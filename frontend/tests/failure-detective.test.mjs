import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace('import.meta.env.VITE_API_BASE_URL', '"http://verigate.test"')
const { verificationRunsApi, sessionStore, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const storage = new Map()
globalThis.sessionStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) }
const runId = '9cdc62c2-0316-4d03-b9c6-1e62da1f78d2'
const resultId = '808676af-e425-4ed3-a5a0-c049633ee17f'

test('verificationRunsApi.analyze posts to run analysis endpoint with auth and returns structured diagnosis', async () => {
  sessionStore.set('detective-token')
  const calls = []
  const mockResponse = {
    verification_run_id: runId,
    status: 'failed',
    failed_count: 1,
    analyses: [
      {
        result_id: resultId,
        test_case_id: 'tc-123',
        test_case_title: 'Verify Login',
        category: 'Authentication Failure',
        root_cause: 'Invalid credentials returned 401',
        explanation: 'The credentials submitted were rejected.',
        suggested_fix: 'Check the test user credentials.',
        confidence: 'High',
        analysis_source: 'heuristic',
        evidence_used: ['failure_message', 'status_code: 401']
      }
    ]
  }

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => mockResponse }
  }

  const result = await verificationRunsApi.analyze(runId, { force_reanalyze: true })

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/verification-runs/${runId}/analyze`)
  assert.equal(calls[0].method, 'POST')
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer detective-token')
  assert.equal(calls[0].headers.get('Content-Type'), 'application/json')
  assert.deepEqual(JSON.parse(calls[0].body), { force_reanalyze: true })
  assert.deepEqual(result, mockResponse)
})

test('verificationRunsApi.analyzeResult posts to result analysis endpoint and returns single diagnosis', async () => {
  sessionStore.set('detective-token')
  const calls = []
  const mockResultDiagnosis = {
    result_id: resultId,
    test_case_id: 'tc-123',
    test_case_title: 'Verify Page Title',
    category: 'Assertion Failure',
    root_cause: "Page title mismatch: expected 'Example Domain', got 'Wrong Title'",
    explanation: 'The browser navigated to the page but title assertion failed.',
    suggested_fix: "Update test case expected value to 'Example Domain'.",
    confidence: 'High',
    analysis_source: 'llm',
    evidence_used: ['expected: Example Domain', 'actual: Wrong Title']
  }

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => mockResultDiagnosis }
  }

  const result = await verificationRunsApi.analyzeResult(resultId)

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/verification-results/${resultId}/analyze`)
  assert.equal(calls[0].method, 'POST')
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer detective-token')
  assert.deepEqual(result, mockResultDiagnosis)
})

test('AI detective API errors propagate structured ApiError details', async () => {
  sessionStore.set('detective-token')
  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    json: async () => ({ detail: 'Verification run not found' })
  })

  await assert.rejects(
    verificationRunsApi.analyze(runId),
    (error) => error instanceof ApiError && error.status === 404 && error.message === 'Verification run not found'
  )
})
