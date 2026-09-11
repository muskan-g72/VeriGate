const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const TOKEN_KEY = 'verigate_session'

export class ApiError extends Error {
  constructor(message, status = 0, code = 'request_failed') {
    super(message); this.name = 'ApiError'; this.status = status; this.code = code
  }
}

export const sessionStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers)
  const token = sessionStore.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
    const payload = await response.json().catch(() => null)
    if (!response.ok) {
      const detail = typeof payload?.detail === 'string' ? payload.detail : 'The request could not be completed.'
      throw new ApiError(detail, response.status, response.status === 401 ? 'unauthorized' : 'request_failed')
    }
    return payload
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('VeriGate API is unavailable. Check the server and try again.', 0, 'unavailable')
  }
}

export const authApi = {
  register: (data) => request('/api/v1/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  login: (email, password) => request('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ username: email, password }) }),
  me: () => request('/api/v1/auth/me'),
  forgotPassword: (email) => request('/api/v1/auth/forgot-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) }),
  resetPassword: (token, password) => request('/api/v1/auth/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token, password }) }),
}

export const projectsApi = {
  list: () => request('/api/v1/projects'),
  read: (projectId) => request(`/api/v1/projects/${projectId}`),
  create: (data) => request('/api/v1/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
  update: (projectId, data) => request(`/api/v1/projects/${projectId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
}

export const testSuitesApi = {
  read: (suiteId) => request(`/api/v1/test-suites/${suiteId}`),
  list: (projectId) => request(`/api/v1/projects/${projectId}/test-suites`),
  create: (projectId, data) => request(`/api/v1/projects/${projectId}/test-suites`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  update: (suiteId, data) => request(`/api/v1/test-suites/${suiteId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  remove: (suiteId) => request(`/api/v1/test-suites/${suiteId}`, { method: 'DELETE' }),
}

export const dashboardApi = {
  summary: () => request('/api/v1/dashboard/summary'),
  projectSummary: (projectId) => request(`/api/v1/projects/${projectId}/summary`),
}

export const projectMembersApi = {
  list: (projectId) => request(`/api/v1/projects/${projectId}/members`),
  create: (projectId, data) => request(`/api/v1/projects/${projectId}/members`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  update: (projectId, userId, data) => request(`/api/v1/projects/${projectId}/members/${userId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  remove: (projectId, userId) => request(`/api/v1/projects/${projectId}/members/${userId}`, { method: 'DELETE' }),
}

export const verificationRunsApi = {
  list: (suiteId) => request(`/api/v1/test-suites/${suiteId}/verification-runs`),
  create: (suiteId, data) => request(`/api/v1/test-suites/${suiteId}/verification-runs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  read: (runId) => request(`/api/v1/verification-runs/${runId}`),
  updateResult: (resultId, data) => request(`/api/v1/verification-results/${resultId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  analyze: (runId, data = {}) => request(`/api/v1/verification-runs/${runId}/analyze`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  analyzeResult: (resultId) => request(`/api/v1/verification-results/${resultId}/analyze`, {
    method: 'POST',
  }),
}

export const testCasesApi = {
  list: (suiteId) => request(`/api/v1/test-suites/${suiteId}/test-cases`),
  create: (suiteId, data) => request(`/api/v1/test-suites/${suiteId}/test-cases`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  update: (caseId, data) => request(`/api/v1/test-cases/${caseId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  remove: (caseId) => request(`/api/v1/test-cases/${caseId}`, { method: 'DELETE' }),
}

export const issuesApi = {
  createFromResult: (resultId, data) => request(`/api/v1/verification-results/${resultId}/issues`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  listForProject: (projectId) => request(`/api/v1/projects/${projectId}/issues`),
  read: (issueId) => request(`/api/v1/issues/${issueId}`),
  update: (issueId, data) => request(`/api/v1/issues/${issueId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
}

export const evidenceApi = {
  list: (resultId) => request(`/api/v1/verification-results/${resultId}/evidence`),
  create: (resultId, data) => request(`/api/v1/verification-results/${resultId}/evidence`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  remove: (evidenceId) => request(`/api/v1/evidence/${evidenceId}`, { method: 'DELETE' }),
  read: (evidenceId) => request(`/api/v1/evidence/${evidenceId}`),
}

export const reportsApi = {
  project: (projectId) => request(`/api/v1/projects/${projectId}/reports`),
  trend: (projectId) => request(`/api/v1/projects/${projectId}/reports/verification-trend`),
  issues: (projectId) => request(`/api/v1/projects/${projectId}/reports/issues`),
}

export const teamsApi = {
  list: () => request('/api/v1/teams'),
  create: (data) => request('/api/v1/teams', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  members: (teamId) => request(`/api/v1/teams/${teamId}/members`),
  update: (teamId, data) => request(`/api/v1/teams/${teamId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  remove: (teamId) => request(`/api/v1/teams/${teamId}`, { method: 'DELETE' }),
  addMember: (teamId, data) => request(`/api/v1/teams/${teamId}/members`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  removeMember: (teamId, userId) => request(`/api/v1/teams/${teamId}/members/${userId}`, { method: 'DELETE' }),
}

export const auditLogsApi = { list: (filters = {}) => request(`/api/v1/audit-logs?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString()}`), read: (logId) => request(`/api/v1/audit-logs/${logId}`) }

export const adminApi = {
  statistics: () => request('/api/v1/admin/statistics'),
  users: () => request('/api/v1/admin/users'),
  teams: () => request('/api/v1/admin/teams'),
  projects: () => request('/api/v1/admin/projects'),
  runs: (filters = {}) => request(`/api/v1/admin/verification-runs?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString()}`),
  issues: (filters = {}) => request(`/api/v1/admin/issues?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString()}`),
  auditLogs: (filters = {}) => request(`/api/v1/admin/audit-logs?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString()}`),
}
