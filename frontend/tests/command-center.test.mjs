import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace('import.meta.env.VITE_API_BASE_URL', '"http://verigate.test"')
const { dashboardApi, sessionStore, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const storage = new Map()
globalThis.sessionStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) }
const sampleProjectId = '3fa85f64-5717-4562-b3fc-2c963f66afa6'

test('dashboardApi.summary sends GET to /api/v1/dashboard/summary with bearer token', async () => {
  sessionStore.set('command-token')
  const calls = []
  const mockSummary = {
    total_projects: 3,
    total_test_suites: 5,
    total_test_cases: 24,
    total_runs: 10,
    completed_runs: 8,
    running_runs: 2,
    passed_runs: 7,
    failed_runs: 1,
    total_results: 50,
    passed_results: 45,
    failed_results: 3,
    blocked_results: 2,
    skipped_results: 0,
    pending_results: 0,
    pass_rate: 90.0,
    failure_rate: 6.0,
    average_duration: 1.45,
    open_issues: 2,
    resolved_issues: 4,
    health_score: 88,
    health_score_status: 'healthy',
    health_score_explanation: 'Verification health is strong.',
    recent_runs: [],
    recent_failures: [],
    trend: []
  }

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => mockSummary }
  }

  const result = await dashboardApi.summary()

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, 'http://verigate.test/api/v1/dashboard/summary')
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer command-token')
  assert.deepEqual(result, mockSummary)
})

test('dashboardApi.summary with projectId appends query parameter', async () => {
  sessionStore.set('command-token')
  const calls = []
  const mockProjectSummary = {
    project_id: sampleProjectId,
    total_projects: 1,
    total_runs: 4,
    health_score: 75,
    health_score_status: 'degraded'
  }

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => mockProjectSummary }
  }

  const result = await dashboardApi.summary(sampleProjectId)

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/dashboard/summary?project_id=${sampleProjectId}`)
  assert.deepEqual(result, mockProjectSummary)
})

test('dashboardApi.summary propagates ApiError on 401 unauthorized or 404 project not found', async () => {
  sessionStore.set('command-token')
  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    json: async () => ({ detail: 'Project not found' })
  })

  await assert.rejects(
    dashboardApi.summary(sampleProjectId),
    (err) => err instanceof ApiError && err.status === 404 && err.message === 'Project not found'
  )
})
