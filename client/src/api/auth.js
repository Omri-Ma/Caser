import { apiFetch } from './client'
import { clearStoredIsManager, clearStoredRole, setStoredIsManager, setStoredRole } from './session'

// A cheap "do I actually have access at this subdomain" check — 204 if so,
// 403 (E.NO_ACCESS_TO_FIRM) otherwise. Used by AppShell to send a
// lawyer/client with no access here to the general homepage instead of
// rendering a shell whose every real data call would 403 individually.
export function checkMyMembership() {
  return apiFetch('/auth/my-membership')
}

// Every other active firm this identity works with, as a lawyer or client —
// powers the multi-firm switcher (CLAUDE.md's Identity vs. membership).
export function myTenants() {
  return apiFetch('/auth/my-tenants')
}

// Self-service "leave this firm" — deactivates the caller's own membership
// at the current tenant subdomain (CLAUDE.md's Memberships note).
export function leaveFirm() {
  return apiFetch('/auth/leave-firm', { method: 'POST' })
}

export function register({ name, email, password }) {
  return apiFetch('/auth/register', { method: 'POST', body: { name, email, password }, redirectOn401: false })
}

export async function login({ email, password }) {
  const session = await apiFetch('/auth/login', { method: 'POST', body: { email, password }, redirectOn401: false })
  setStoredRole(session.role)
  setStoredIsManager(session.is_manager)
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

// Self-service profile edit (bio/photo_url/years_of_experience) — global to
// the person, feeds the public homepage's team section (CLAUDE.md). Lawyer
// only in practice (a client is never shown there), but not role-gated
// here — harmless either way, same as the underlying Identities columns.
export function updateProfile({ bio, photoUrl, yearsOfExperience }) {
  return apiFetch('/auth/profile', {
    method: 'PATCH',
    body: { bio: bio || null, photo_url: photoUrl || null, years_of_experience: yearsOfExperience },
  })
}

export async function logout() {
  await apiFetch('/auth/logout', { method: 'POST' })
  clearStoredRole()
  clearStoredIsManager()
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
