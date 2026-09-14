import { apiFetch } from './client'

export function signup({ firmName, subdomain, adminName, adminEmail, adminPassword }) {
  return apiFetch('/auth/signup', {
    method: 'POST',
    body: {
      firm_name: firmName,
      subdomain,
      admin_name: adminName,
      admin_email: adminEmail,
      admin_password: adminPassword,
    },
    redirectOn401: false,
  })
}

export function login({ email, password }) {
  return apiFetch('/auth/login', { method: 'POST', body: { email, password }, redirectOn401: false })
}

// office_manager login from the lobby (www.<BASE_DOMAIN>) — see LobbyLoginPage.
export function lobbyLogin({ email, password }) {
  return apiFetch('/auth/lobby-login', { method: 'POST', body: { email, password }, redirectOn401: false })
}

// super_admin login at the fixed platform address — see PlatformLoginPage.
export function platformLogin({ email, password }) {
  return apiFetch('/auth/platform-login', { method: 'POST', body: { email, password }, redirectOn401: false })
}

export function me() {
  return apiFetch('/auth/me')
}

// Every active office_manager Membership the current session holds, across
// every active tenant — same lookup /auth/lobby-login uses, just for an
// already-authenticated identity. Used by AppShell to resolve where to send
// someone who lands on a subdomain they have no membership at (CLAUDE.md's
// "Landing somewhere you have no access" redirect rule).
export function myTenants() {
  return apiFetch('/auth/my-tenants')
}

// Self-service profile edit (bio/photo_url/years_of_experience) — global to
// the person, feeds the public homepage's team section (CLAUDE.md).
export function updateProfile({ bio, photoUrl, yearsOfExperience }) {
  return apiFetch('/auth/profile', {
    method: 'PATCH',
    body: { bio: bio || null, photo_url: photoUrl || null, years_of_experience: yearsOfExperience },
  })
}

// Self-service read/write of the office_manager's own
// Memberships.show_on_public_page — reachable from their own profile page
// (there's no Admins page/list to find themselves on anymore, since a
// firm has exactly one office_manager, fixed at founding; CLAUDE.md's
// Memberships note).
export function getMyPublicVisibility() {
  return apiFetch('/auth/my-public-visibility')
}

export function updateMyPublicVisibility(showOnPublicPage) {
  return apiFetch('/auth/my-public-visibility', {
    method: 'PATCH',
    body: { show_on_public_page: showOnPublicPage },
  })
}

export function logout() {
  return apiFetch('/auth/logout', { method: 'POST' })
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
