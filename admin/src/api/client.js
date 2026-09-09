// Auth-aware fetch wrapper for admin_api. Base URL reuses the browser's own
// hostname (the app is always served from a real tenant subdomain, e.g.
// office1.lvh.me, or the fixed platform.lvh.me for super_admin) and only
// takes protocol/port from env — see client/src/api/client.js for the same
// reasoning on that side.
const API_PROTOCOL = import.meta.env.VITE_API_PROTOCOL || 'http'
const API_PORT = import.meta.env.VITE_API_PORT

function apiBaseUrl() {
  return `${API_PROTOCOL}://${window.location.hostname}:${API_PORT}`
}

export class ApiError extends Error {
  constructor(message, { status, field } = {}) {
    super(message)
    this.status = status
    this.field = field
  }
}

// redirectOn401 is false for login/signup calls themselves — a 401 there is
// "wrong password", a normal inline form error, not an expired session.
export async function apiFetch(path, { method = 'GET', body, redirectOn401 = true } = {}) {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method,
    credentials: 'include',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })

  let data = null
  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (response.status === 401 && redirectOn401) {
    window.location.assign('/login')
    throw new ApiError(data?.error || 'ההתחברות פגה', { status: 401, field: data?.field })
  }

  if (!response.ok) {
    throw new ApiError(data?.error || 'משהו השתבש, נסו שוב', { status: response.status, field: data?.field })
  }

  return data
}

// Downloads return a raw file, not JSON — fetch the blob directly and read
// the real filename off Content-Disposition (set server-side from
// Documents.original_filename) rather than guessing it from the URL.
export async function apiDownload(path) {
  const response = await fetch(`${apiBaseUrl()}${path}`, { method: 'GET', credentials: 'include' })

  if (response.status === 401) {
    window.location.assign('/login')
    throw new ApiError('ההתחברות פגה', { status: 401 })
  }

  if (!response.ok) {
    let data = null
    try {
      data = await response.json()
    } catch {
      data = null
    }
    throw new ApiError(data?.error || 'משהו השתבש, נסו שוב', { status: response.status, field: data?.field })
  }

  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match ? decodeURIComponent(match[1]) : 'download'
  return { blob, filename }
}
