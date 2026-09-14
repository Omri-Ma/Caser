import { apiFetch } from './client'

// Unauthenticated — no session cookie is expected, so a 401 here would be
// unexpected server behavior, not "please log in": don't redirect on it.
export function getPublicProfile() {
  return apiFetch('/public/profile', { redirectOn401: false })
}

// Lobby firm directory — also unauthenticated, no session cookie expected.
export function getPublicDirectory(page = 1, search = '') {
  const params = new URLSearchParams({ page: String(page) })
  if (search) params.set('search', search)
  return apiFetch(`/public/directory?${params}`, { redirectOn401: false })
}
