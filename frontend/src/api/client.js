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
