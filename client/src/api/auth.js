import { apiFetch } from './client'
import { clearStoredRole, setStoredRole } from './session'

export function register({ name, email, password }) {
  return apiFetch('/auth/register', { method: 'POST', body: { name, email, password }, redirectOn401: false })
}

export async function login({ email, password }) {
  const session = await apiFetch('/auth/login', { method: 'POST', body: { email, password }, redirectOn401: false })
  setStoredRole(session.role)
  return session
}

export function me() {
  return apiFetch('/auth/me')
}

export async function logout() {
  await apiFetch('/auth/logout', { method: 'POST' })
  clearStoredRole()
}
