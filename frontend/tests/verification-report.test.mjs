import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace('import.meta.env.VITE_API_BASE_URL', '"http://verigate.test"')
const { reportsApi, sessionStore, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const storage = new Map()
globalThis.sessionStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) }
const runId = '9cdc62c2-0316-4d03-b9c6-1e62da1f78d2'

test('reportsApi.verificationReport fetches JSON report data with authorization', async () => {
  sessionStore.set('report-token-abc')
  const calls = []
  const mockReportJson = {
    report_title: 'Proof of Verification Report',
    verification_run: { id: runId, name: 'Release 2.4 Sanity Run', status: 'passed' },
    project: { id: 'proj-1', name: 'Core Engine' },
    summary: { total_tests: 5, passed: 5, failed: 0, pass_rate: 100.0 },
    timeline: [],
    test_results: []
  }

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => mockReportJson }
  }

  const result = await reportsApi.verificationReport(runId, 'json')

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/verification-runs/${runId}/report?format=json`)
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer report-token-abc')
  assert.deepEqual(result, mockReportJson)
})

test('reportsApi.verificationReport supports alternative formats', async () => {
  sessionStore.set('report-token-abc')
  const calls = []
  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => ({ html: '<html><body>Report</body></html>' }) }
  }

  await reportsApi.verificationReport(runId, 'html')

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/verification-runs/${runId}/report?format=html`)
})

test('reportsApi.downloadVerificationReport downloads PDF blob and extracts filename header', async () => {
  sessionStore.set('report-token-abc')
  const calls = []
  const mockPdfContent = new Uint8Array([0x25, 0x50, 0x44, 0x46]) // %PDF
  const mockBlob = new Blob([mockPdfContent], { type: 'application/pdf' })

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return {
      ok: true,
      headers: new Headers({
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="verigate-proof-of-verification-Release-Run.pdf"'
      }),
      blob: async () => mockBlob
    }
  }

  const { blob, filename } = await reportsApi.downloadVerificationReport(runId)

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/verification-runs/${runId}/report?format=pdf`)
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer report-token-abc')
  assert.equal(filename, 'verigate-proof-of-verification-Release-Run.pdf')
  assert.equal(blob.type, 'application/pdf')
})

test('reportsApi.downloadVerificationReport falls back to default filename when header is missing', async () => {
  sessionStore.set('report-token-abc')
  const mockBlob = new Blob(['pdf-data'], { type: 'application/pdf' })

  globalThis.fetch = async () => ({
    ok: true,
    headers: new Headers({ 'Content-Type': 'application/pdf' }),
    blob: async () => mockBlob
  })

  const { filename } = await reportsApi.downloadVerificationReport(runId)
  assert.equal(filename, 'verigate-proof-of-verification.pdf')
})

test('reportsApi.downloadVerificationReport throws ApiError on failure', async () => {
  sessionStore.set('report-token-abc')
  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    json: async () => ({ detail: 'Verification run not found.' })
  })

  await assert.rejects(
    () => reportsApi.downloadVerificationReport('missing-id'),
    (err) => {
      assert(err instanceof ApiError)
      assert.equal(err.status, 404)
      assert.equal(err.message, 'Verification run not found.')
      return true
    }
  )
})
