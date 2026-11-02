import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import { filterTraceabilityItems, formatCoverageStatus, latestVerifiedAt, paginationOffset } from '../src/requirements.js'

const source = (await readFile(new URL('../src/api/client.js', import.meta.url), 'utf8')).replace(/import\.meta\.env\.VITE_API_(URL|BASE_URL)/, '"http://verigate.test"')
const { requirementsApi, sessionStore } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
globalThis.sessionStorage = new Map()
globalThis.sessionStorage.getItem = globalThis.sessionStorage.get.bind(globalThis.sessionStorage)
globalThis.sessionStorage.setItem = globalThis.sessionStorage.set.bind(globalThis.sessionStorage)
globalThis.sessionStorage.removeItem = globalThis.sessionStorage.delete.bind(globalThis.sessionStorage)

test('requirements API uses documented CRUD, traceability, linking, and export paths', async () => {
  sessionStore.set('token'); const calls = []; globalThis.fetch = async (url, options = {}) => { calls.push({ url, ...options }); return { ok: true, json: async () => ({ items: [], total: 0 }), blob: async () => new Blob(['rtm']), headers: new Headers({ 'Content-Disposition': 'attachment; filename="matrix.csv"' }) } }
  await requirementsApi.create('project', { requirement_key: 'REQ-1', title: 'Title' }); await requirementsApi.update('requirement', { status: 'deprecated' }); await requirementsApi.traceability('project', { priority: 'critical', category: 'security', status: 'approved', limit: 50, offset: 100 }); await requirementsApi.linkTestCase('requirement', 'case'); await requirementsApi.unlinkIssue('requirement', 'issue'); const exportResult = await requirementsApi.exportTraceability('project')
  assert.deepEqual(calls.map(({ url, method = 'GET' }) => [method, url]), [['POST', 'http://verigate.test/api/v1/projects/project/requirements'], ['PATCH', 'http://verigate.test/api/v1/requirements/requirement'], ['GET', 'http://verigate.test/api/v1/projects/project/requirements/traceability?status=approved&priority=critical&category=security&limit=50&offset=100'], ['POST', 'http://verigate.test/api/v1/requirements/requirement/test-cases/case'], ['DELETE', 'http://verigate.test/api/v1/requirements/requirement/issues/issue'], ['GET', 'http://verigate.test/api/v1/projects/project/requirements/traceability.csv']])
  assert.equal(calls[0].headers.get('Authorization'), 'Bearer token'); assert.equal(exportResult.filename, 'matrix.csv')
})

test('traceability helpers are null-safe and filter only loaded items', () => {
  const items = [{ requirement_key: 'REQ-1', title: 'Login', coverage_status: 'passing', unresolved_issue_count: 0 }, { requirement_key: 'REQ-2', title: 'Payment', coverage_status: 'failing', unresolved_issue_count: 2 }]
  assert.equal(formatCoverageStatus('not_passing'), 'Not passing'); assert.equal(formatCoverageStatus(null), 'Untested'); assert.deepEqual(filterTraceabilityItems(items, { search: 'payment', unresolved: true }).map((item) => item.requirement_key), ['REQ-2']); assert.equal(latestVerifiedAt([{ latest_run_completed_at: null }]), null); assert.equal(latestVerifiedAt([{ latest_run_completed_at: '2026-01-01T00:00:00Z' }, { latest_run_completed_at: '2026-02-01T00:00:00Z' }]), '2026-02-01T00:00:00.000Z'); assert.equal(paginationOffset(3, 50), 100)
})
