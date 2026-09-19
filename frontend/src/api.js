// Small fetch wrapper: attaches the JWT and normalizes errors.

export function getToken() {
  return localStorage.getItem('token')
}

export function setSession(token, username, role) {
  localStorage.setItem('token', token)
  localStorage.setItem('username', username)
  localStorage.setItem('role', role || 'user')
}

export function clearSession() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('role')
}

export function getRole() {
  return localStorage.getItem('role')
}

export function isAdmin() {
  return getRole() === 'admin'
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.json)
  }

  const response = await fetch(path, { ...options, headers })

  if (response.status === 401 && !path.startsWith('/api/auth/')) {
    clearSession()
    window.location.href = '/login'
    throw new Error('Session expired, please log in again.')
  }

  if (!response.ok) {
    let detail = `Request failed (HTTP ${response.status})`
    try {
      const body = await response.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : detail
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new Error(detail)
  }

  if (response.status === 204) return null
  return response.json()
}

export const api = {
  register: (username, password) =>
    request('/api/auth/register', { method: 'POST', json: { username, password } }),

  login: (username, password) =>
    request('/api/auth/login', { method: 'POST', json: { username, password } }),

  uploadReport: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/analyses', { method: 'POST', body: form })
  },

  listAnalyses: () => request('/api/analyses'),

  getAnalysis: (id) => request(`/api/analyses/${id}`),

  deleteAnalysis: (id) => request(`/api/analyses/${id}`, { method: 'DELETE' }),

  compareAnalyses: (baseId, newId) =>
    request(`/api/analyses/compare?base_id=${baseId}&new_id=${newId}`),

  // API-key pool visible to any signed-in user (labels only, no secrets).
  listApiKeys: () => request('/api/api-keys'),

  explainPath: (analysisId, pathIndex, apiKeyId) =>
    request(`/api/analyses/${analysisId}/paths/${pathIndex}/explain`, {
      method: 'POST',
      json: { api_key_id: apiKeyId ?? null },
    }),

  // ----- admin -----
  admin: {
    listUsers: () => request('/api/admin/users'),
    createUser: (username, password, role) =>
      request('/api/admin/users', { method: 'POST', json: { username, password, role } }),
    updateUser: (id, patch) =>
      request(`/api/admin/users/${id}`, { method: 'PATCH', json: patch }),
    deleteUser: (id) => request(`/api/admin/users/${id}`, { method: 'DELETE' }),

    listAnalyses: () => request('/api/admin/analyses'),
    deleteAnalysis: (id) => request(`/api/admin/analyses/${id}`, { method: 'DELETE' }),

    listApiKeys: () => request('/api/admin/api-keys'),
    createApiKey: (label, secret) =>
      request('/api/admin/api-keys', { method: 'POST', json: { label, secret } }),
    updateApiKey: (id, patch) =>
      request(`/api/admin/api-keys/${id}`, { method: 'PATCH', json: patch }),
    deleteApiKey: (id) => request(`/api/admin/api-keys/${id}`, { method: 'DELETE' }),

    stats: () => request('/api/admin/stats'),
  },
}
