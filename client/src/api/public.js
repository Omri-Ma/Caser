import { apiFetch } from './client'

// Unauthenticated — no session cookie is expected, so a 401 here would be
// unexpected server behavior, not "please log in": don't redirect on it.
export function getPublicProfile() {
  return apiFetch('/public/profile', { redirectOn401: false })
}
