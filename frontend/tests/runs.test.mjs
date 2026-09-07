import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { filterRuns, loadRuns, runsEmptyState, summarizeRuns } from '../src/runs.js'
import { runProgress } from '../src/verification.js'

const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace('import.meta.env.VITE_API_BASE_URL', '"http://verigate.test"')
const { projectsApi, testSuitesApi, verificationRunsApi, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const api = { listProjects: projectsApi.list, listSuites: testSuitesApi.list, listRuns: verificationRunsApi.list }
globalThis.sessionStorage = { getItem: () => 'runs-test-token' }
const projects = [{ id: 'p1', name: 'Web' }, { id: 'p2', name: 'API' }]
const suites = [{ id: 's1', name: 'Login', project_id: 'p1' }, { id: 's2', name: 'Checkout', project_id: 'p1' }, { id: 's3', name: 'Health', project_id: 'p2' }]
const runs = [
  { id: 'r1', name: 'Login smoke', status: 'in_progress', test_suite_id: 's1', created_at: '2026-09-01T10:00:00Z', started_at: '2026-09-01T10:01:00Z', completed_at: null, total_cases: 3, pending_count: 2, failed_count: 1, passed_count: 0, blocked_count: 0, skipped_count: 0 },
  { id: 'r2', name: 'Purchase flow', status: 'pending', test_suite_id: 's2', created_at: '2026-09-02T10:00:00Z', total_cases: 2, pending_count: 2 },
  { id: 'r3', name: 'API smoke', status: 'completed', test_suite_id: 's3', created_at: '2026-09-03T10:00:00Z', total_cases: 1, pending_count: 0 },
]
const fakeApi = {
  listProjects: async () => projects,
  listSuites: async (projectId) => suites.filter((suite) => suite.project_id === projectId),
  listRuns: async (suiteId) => runs.filter((run) => run.test_suite_id === suiteId),
}

test('aggregation uses existing authenticated list endpoints exactly once, preserving run and project/suite context', async () => {
  const responses = new Map([
    ['/api/v1/projects', projects],
    ...projects.map((project) => [`/api/v1/projects/${project.id}/test-suites`, suites.filter((suite) => suite.project_id === project.id)]),
    ...suites.map((suite) => [`/api/v1/test-suites/${suite.id}/verification-runs`, runs.filter((run) => run.test_suite_id === suite.id)]),
  ])
  const calls = []
  globalThis.fetch = async (url, options) => {
    const path = new URL(url).pathname
    calls.push(path)
    assert.equal(options.method || 'GET', 'GET')
    assert.equal(options.headers.get('Authorization'), 'Bearer runs-test-token')
    assert.ok(responses.has(path), `Unexpected API endpoint: ${path}`)
    return { ok: true, json: async () => responses.get(path) }
  }
  const stages = []
  const data = await loadRuns(api, (stage) => stages.push(stage))
  assert.deepEqual(stages, ['projects', 'suites', 'runs'])
  assert.deepEqual(calls.sort(), [...responses.keys()].sort())
  assert.equal(data.runs.length, 3)
  assert.deepEqual(data.runs[0], { ...runs[0], project_id: 'p1', project_name: 'Web', suite_name: 'Login' })
  assert.equal(data.runs[2].project_name, 'API')
  assert.deepEqual(data.failures, [])
})

test('partial failures preserve successful branches and identify missing project/suite data', async () => {
  const data = await loadRuns({ ...fakeApi,
    listSuites: async (id) => { if (id === 'p2') throw new ApiError('Server unavailable', 0, 'unavailable'); return fakeApi.listSuites(id) },
    listRuns: async (id) => { if (id === 's1') throw new ApiError('Suite not found', 404); return fakeApi.listRuns(id) },
  })
  assert.deepEqual(data.runs.map((run) => run.id), ['r2'])
  assert.equal(data.failures.length, 2)
  assert.ok(data.failures.some((failure) => failure.projectId === 'p2' && failure.label.includes('API')))
  assert.ok(data.failures.some((failure) => failure.suiteId === 's1' && failure.message === 'Suite not found'))
  assert.equal(runsEmptyState(data, 'p2'), 'incomplete')
})

test('unauthorized responses from any aggregation stage propagate to the session handler', async () => {
  const expired = new ApiError('Not authenticated', 401, 'unauthorized')
  for (const stage of ['listProjects', 'listSuites', 'listRuns']) {
    await assert.rejects(loadRuns({ ...fakeApi, [stage]: async () => { throw expired } }), (error) => error === expired)
  }
})

test('initial API failure propagates and a later reload can succeed', async () => {
  await assert.rejects(loadRuns({ ...fakeApi, listProjects: async () => { throw new ApiError('Unavailable', 0, 'unavailable') } }), { code: 'unavailable' })
  assert.equal((await loadRuns(fakeApi)).runs.length, 3)
})

test('empty states distinguish no projects, no suites, no runs, and filtered results', async () => {
  let requests = 0
  const noProjects = await loadRuns({ ...fakeApi, listProjects: async () => [], listSuites: async () => { requests++; return [] } })
  assert.equal(requests, 0)
  assert.equal(runsEmptyState(noProjects), 'projects')
  const noSuites = await loadRuns({ ...fakeApi, listSuites: async () => [] })
  assert.equal(runsEmptyState(noSuites), 'suites')
  const noRuns = await loadRuns({ ...fakeApi, listRuns: async () => [] })
  assert.equal(runsEmptyState(noRuns), 'runs')
  const data = await loadRuns(fakeApi)
  assert.equal(runsEmptyState(data), 'filtered')
  assert.deepEqual(filterRuns(data.runs, { search: 'nonexistent' }), [])
  assert.equal(runsEmptyState({ ...data, suites: data.suites.filter((suite) => suite.project_id !== 'p2'), runs: [] }, 'p2'), 'suites')
})

test('project, exact status, name/suite search, and date ordering filter loaded data without mutation', async () => {
  const data = await loadRuns(fakeApi)
  assert.deepEqual(filterRuns(data.runs).map((run) => run.id), ['r3', 'r2', 'r1'])
  assert.deepEqual(filterRuns(data.runs, { sort: 'oldest' }).map((run) => run.id), ['r1', 'r2', 'r3'])
  assert.deepEqual(filterRuns(data.runs, { projectId: 'p1' }).map((run) => run.id), ['r2', 'r1'])
  assert.deepEqual(filterRuns(data.runs, { projectId: 'p1', status: 'in_progress' }).map((run) => run.id), ['r1'])
  assert.deepEqual(filterRuns(data.runs, { search: '  CHECKOUT ' }).map((run) => run.id), ['r2'])
  assert.deepEqual(filterRuns(data.runs, { search: 'smoke', status: 'completed' }).map((run) => run.id), ['r3'])
  assert.deepEqual(data.runs.map((run) => run.id), ['r1', 'r2', 'r3'])
  assert.deepEqual(summarizeRuns(data.runs), { total: 3, pending: 1, in_progress: 1, completed: 1 })
})

test('progress is derived only from valid backend counts', () => {
  assert.deepEqual(runProgress(runs[0]), { executed: 1, total: 3 })
  assert.deepEqual(runProgress(runs[1]), { executed: 0, total: 2 })
  assert.deepEqual(runProgress(runs[2]), { executed: 1, total: 1 })
  assert.deepEqual(runProgress({ total_cases: 0, pending_count: 0 }), { executed: 0, total: 0 })
  for (const run of [{}, { total_cases: 3 }, { total_cases: 3, pending_count: 4 }, { total_cases: -1, pending_count: 0 }, { total_cases: 3, pending_count: '2' }]) assert.equal(runProgress(run), null)
})
