import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace('import.meta.env.VITE_API_BASE_URL', '"http://verigate.test"')
const { githubApi, sessionStore, ApiError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const storage = new Map()
globalThis.sessionStorage = { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) }
const projectId = '43a3d242-4f36-4074-b5df-1e2efd978a3c'

test('githubApi.getProjectConfig fetches project GitHub settings with bearer token', async () => {
  sessionStore.set('gh-auth-token-1')
  const calls = []
  const mockConfig = {
    project_id: projectId,
    github_repo: 'muskan-g72/VeriGate',
    github_default_branch: 'main',
    github_verification_enabled: true,
    is_connected: true,
    webhook_configured: true,
    webhook_url: 'http://verigate.test/api/v1/github/webhook',
  }

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => mockConfig }
  }

  const result = await githubApi.getProjectConfig(projectId)

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/projects/${projectId}/github`)
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer gh-auth-token-1')
  assert.deepEqual(result, mockConfig)
})

test('githubApi.updateProjectConfig sends PATCH request with serialized payload', async () => {
  sessionStore.set('gh-auth-token-2')
  const calls = []
  const payload = {
    github_repo: 'muskan-g72/VeriGate',
    github_default_branch: 'develop',
    github_verification_enabled: true,
    github_webhook_secret: 'new-secret-xyz',
  }

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return {
      ok: true,
      json: async () => ({
        project_id: projectId,
        ...payload,
        is_connected: true,
        webhook_configured: true,
      }),
    }
  }

  const result = await githubApi.updateProjectConfig(projectId, payload)

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/projects/${projectId}/github`)
  assert.equal(calls[0].method, 'PATCH')
  assert.equal(calls[0].headers.get('Content-Type'), 'application/json')
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer gh-auth-token-2')
  assert.equal(calls[0].body, JSON.stringify(payload))
  assert.equal(result.github_default_branch, 'develop')
})

test('githubApi.listProjectPrs fetches PR runs for a specific project', async () => {
  sessionStore.set('gh-auth-token-3')
  const calls = []
  const mockPrRuns = [
    {
      id: 'run-1',
      trigger_source: 'github_pr',
      pr_number: 101,
      pr_title: 'feat: webhook integration',
      status: 'completed',
      passed_count: 8,
      failed_count: 0,
    },
  ]

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => mockPrRuns }
  }

  const result = await githubApi.listProjectPrs(projectId)

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, `http://verigate.test/api/v1/projects/${projectId}/github/prs`)
  assert.equal(result.length, 1)
  assert.equal(result[0].pr_number, 101)
})

test('githubApi.listPrVerifications fetches across all projects or with query param', async () => {
  sessionStore.set('gh-auth-token-4')
  const calls = []

  globalThis.fetch = async (url, options) => {
    calls.push({ url, ...options })
    return { ok: true, json: async () => [] }
  }

  // Without projectId
  await githubApi.listPrVerifications()
  assert.equal(calls[0].url, 'http://verigate.test/api/v1/github/pr-verifications')

  // With projectId
  await githubApi.listPrVerifications('proj-99')
  assert.equal(calls[1].url, 'http://verigate.test/api/v1/github/pr-verifications?project_id=proj-99')
})

test('githubApi handles API error responses cleanly', async () => {
  sessionStore.set('invalid-token')
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Could not validate credentials' }),
  })

  await assert.rejects(
    async () => {
      await githubApi.getProjectConfig(projectId)
    },
    (err) => {
      assert(err instanceof ApiError)
      assert.equal(err.status, 401)
      assert.equal(err.code, 'unauthorized')
      assert.equal(err.message, 'Could not validate credentials')
      return true
    }
  )
})
