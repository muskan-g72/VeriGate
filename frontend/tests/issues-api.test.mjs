import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { canCreateIssue, issueDraft } from '../src/issues.js'

const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace('import.meta.env.VITE_API_BASE_URL', '"http://verigate.test"')
const { issuesApi, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
globalThis.sessionStorage = { getItem: () => 'issue-test-token' }
const resultId = '808676af-e425-4ed3-a5a0-c049633ee17f'
const issueId = '9cdc62c2-0316-4d03-b9c6-1e62da1f78d2'
const projectId = '20fd236a-4e3a-4f1a-881b-2ab8da843d9f'

test('issue client uses existing paths, bearer token and exact create/update payloads', async () => {
  const calls = []
  const response = { id: issueId, status: 'resolved', resolved_at: '2026-09-07T12:00:00Z' }
  globalThis.fetch = async (url, options) => { calls.push({ url, ...options }); return { ok: true, json: async () => response } }
  const creation = { title: 'Login failed', description: '500 response', severity: 'high' }
  const update = { ...creation, status: 'resolved' }
  assert.equal(await issuesApi.createFromResult(resultId, creation), response)
  await issuesApi.listForProject(projectId)
  await issuesApi.read(issueId)
  assert.equal(await issuesApi.update(issueId, update), response)
  assert.deepEqual(calls.map(({ url, method = 'GET' }) => [method, url]), [
    ['POST', `http://verigate.test/api/v1/verification-results/${resultId}/issues`],
    ['GET', `http://verigate.test/api/v1/projects/${projectId}/issues`],
    ['GET', `http://verigate.test/api/v1/issues/${issueId}`],
    ['PATCH', `http://verigate.test/api/v1/issues/${issueId}`],
  ])
  for (const call of calls) assert.equal(call.headers.get('Authorization'), 'Bearer issue-test-token')
  assert.deepEqual(JSON.parse(calls[0].body), creation)
  assert.deepEqual(JSON.parse(calls[3].body), update)
  assert.equal(calls[3].headers.get('Content-Type'), 'application/json')
})

test('issue errors preserve backend eligibility and session errors', async () => {
  for (const [status, detail] of [[400, 'Issues can only be created from failed or blocked results'], [401, 'Not authenticated'], [404, 'Issue not found']]) {
    globalThis.fetch = async () => ({ ok: false, status, json: async () => ({ detail }) })
    await assert.rejects(issuesApi.createFromResult(resultId, { title: 'Finding' }), (error) => error instanceof ApiError && error.status === status && error.message === detail)
  }
})

test('only failed and blocked results are eligible; draft uses saved test context', () => {
  for (const status of ['passed', 'pending', 'skipped']) assert.equal(canCreateIssue(status), false)
  for (const status of ['failed', 'blocked']) assert.equal(canCreateIssue(status), true)
  const draft = issueDraft({ status: 'failed', actual_result: '500', notes: 'API failed' }, { title: 'Login', steps: 'Submit credentials', expected_result: 'Dashboard loads' })
  assert.deepEqual(draft, { title: 'Login - failed', severity: 'medium', description: 'Steps:\nSubmit credentials\n\nExpected result:\nDashboard loads\n\nActual result:\n500\n\nNotes:\nAPI failed' })
})

test('issue requests report backend unavailability consistently', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await assert.rejects(issuesApi.listForProject(projectId), (error) => error instanceof ApiError && error.code === 'unavailable' && error.status === 0)
})

test('issue drafts respect title limits and handle missing test definitions', () => {
  assert.deepEqual(issueDraft({ status: 'blocked' }), { title: 'Verification - blocked', description: '', severity: 'medium' })
  assert.equal(issueDraft({ status: 'failed' }, { title: 'x'.repeat(180) }).title.length, 180)
})
