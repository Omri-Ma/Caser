import { apiFetch } from './client'

export function register({ name, email, password }) {
  return apiFetch('/auth/register', { method: 'POST', body: { name, email, password }, redirectOn401: false })
}

export function login({ email, password }) {
  return apiFetch('/auth/login', { method: 'POST', body: { email, password }, redirectOn401: false })
}

export function me() {
  return apiFetch('/auth/me')
}

export function logout() {
  return apiFetch('/auth/logout', { method: 'POST' })
}
