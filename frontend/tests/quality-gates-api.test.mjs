import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace(/import\.meta\.env\.VITE_API_(URL|BASE_URL)/, '"http://verigate.test"')
const { qualityGatesApi, verificationRunsApi, sessionStore } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const storage = new Map()
globalThis.sessionStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) }

test('quality gate API uses project and run endpoints', async () => {
  const calls = []
  globalThis.fetch = async (url, options) => { calls.push({ url, ...options }); return { ok: true, json: async () => null } }
  const projectId = '11111111-1111-1111-1111-111111111111'
  const runId = '22222222-2222-2222-2222-222222222222'
  await qualityGatesApi.get(projectId)
  await qualityGatesApi.update(projectId, { enabled: true, min_executed_tests: 1 })
  await verificationRunsApi.qualityGate(runId)
  assert.deepEqual(calls.map(({ url, method = 'GET' }) => [method, url]), [
    ['GET', `http://verigate.test/api/v1/projects/${projectId}/quality-gate`],
    ['PUT', `http://verigate.test/api/v1/projects/${projectId}/quality-gate`],
    ['GET', `http://verigate.test/api/v1/verification-runs/${runId}/quality-gate`],
  ])
})
