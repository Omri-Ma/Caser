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

// lawyer/client login from the lobby (www.<BASE_DOMAIN>) — see
// LobbyLoginPage. Doesn't call setStoredRole itself: which tenant's role
// applies isn't known until the picker (if any) resolves to one, and the
// redirect crosses origins anyway (see utils/host.js's redirectToTenant),
// so the role travels via a query param instead — read back on the landing
// page's next mount.
export function lobbyLogin({ email, password }) {
  return apiFetch('/auth/lobby-login', { method: 'POST', body: { email, password }, redirectOn401: false })
}

export function me() {
  return apiFetch('/auth/me')
}

export async function logout() {
  await apiFetch('/auth/logout', { method: 'POST' })
  clearStoredRole()
}

// Self-service "change my password" while logged in — every role, never an
// office_manager lever over another person's account (CLAUDE.md's
// office_manager authority boundary).
export function changePassword({ currentPassword, newPassword }) {
  return apiFetch('/auth/change-password', {
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword },
  })
}

// Real forgot-password flow (CLAUDE.md's PasswordResetTokens) — reachable
// only from the lobby (www.<BASE_DOMAIN>), since a forgotten password is an
// Identities-level problem with no tenant known yet.
export function forgotPassword(email) {
  return apiFetch('/auth/forgot-password', { method: 'POST', body: { email }, redirectOn401: false })
}

export function resetPassword({ token, newPassword }) {
  return apiFetch('/auth/reset-password', {
    method: 'POST',
    body: { token, new_password: newPassword },
    redirectOn401: false,
  })
}

// Dev-only stand-in for real email delivery (CLAUDE.md's Future additions) —
// lets the ForgotPasswordPage point at a visibly reachable place to find the
// reset link instead of an inbox that doesn't exist in this exercise.
export function getDevOutbox(email) {
  return apiFetch(`/auth/dev-outbox?email=${encodeURIComponent(email)}`, { redirectOn401: false })
}
