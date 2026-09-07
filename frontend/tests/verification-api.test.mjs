import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

// Replace only Vite's build-time environment value to exercise the real client in Node.
const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace('import.meta.env.VITE_API_BASE_URL', '"http://verigate.test"')
const { verificationRunsApi, testSuitesApi, sessionStore, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const storage = new Map()
globalThis.sessionStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) }
const suiteId = '20fd236a-4e3a-4f1a-881b-2ab8da843d9f'
const runId = '9cdc62c2-0316-4d03-b9c6-1e62da1f78d2'
const resultId = '808676af-e425-4ed3-a5a0-c049633ee17f'

test('verification calls use existing paths, JSON bodies, and session bearer token', async () => {
  sessionStore.set('test-token')
  const calls = []
  const response = { id: runId, status: 'pending', results: [] }
  globalThis.fetch = async (url, options) => { calls.push({ url, ...options }); return { ok: true, json: async () => response } }
  assert.equal(await verificationRunsApi.create(suiteId, { name: 'Regression' }), response)
  await verificationRunsApi.list(suiteId)
  await verificationRunsApi.read(runId)
  await verificationRunsApi.updateResult(resultId, { status: 'failed', actual_result: '500', notes: 'Login failed' })
  await testSuitesApi.read(suiteId)
  assert.deepEqual(calls.map(({ url, method = 'GET' }) => [method, url]), [
    ['POST', `http://verigate.test/api/v1/test-suites/${suiteId}/verification-runs`],
    ['GET', `http://verigate.test/api/v1/test-suites/${suiteId}/verification-runs`],
    ['GET', `http://verigate.test/api/v1/verification-runs/${runId}`],
    ['PATCH', `http://verigate.test/api/v1/verification-results/${resultId}`],
    ['GET', `http://verigate.test/api/v1/test-suites/${suiteId}`],
  ])
  for (const call of calls) assert.equal(call.headers.get('Authorization'), 'Bearer test-token')
  assert.deepEqual(JSON.parse(calls[0].body), { name: 'Regression' })
  assert.deepEqual(JSON.parse(calls[3].body), { status: 'failed', actual_result: '500', notes: 'Login failed' })
  assert.equal(calls[3].headers.get('Content-Type'), 'application/json')
})

test('API errors preserve backend messages and unauthorized classification', async () => {
  for (const [status, detail] of [[400, 'Test suite has no active test cases'], [401, 'Not authenticated'], [404, 'Verification run not found']]) {
    globalThis.fetch = async () => ({ ok: false, status, json: async () => ({ detail }) })
    await assert.rejects(verificationRunsApi.read(runId), (error) => error instanceof ApiError && error.status === status && error.message === detail && error.code === (status === 401 ? 'unauthorized' : 'request_failed'))
  }
})

test('network failures use the existing unavailable error', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await assert.rejects(verificationRunsApi.list(suiteId), (error) => error instanceof ApiError && error.code === 'unavailable')
})
