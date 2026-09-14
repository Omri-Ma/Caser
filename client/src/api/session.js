// The membership role for the current tenant login. /auth/me (session
// restore on page load) only returns identity fields, not role — role is
// only ever handed to the frontend once, in the /auth/login response — so
// we stash it here for UI-only decisions (e.g. which document folder tabs
// to show). This is display convenience, never a security boundary: real
// role enforcement happens server-side on every request regardless.
const ROLE_KEY = 'caser_role'
// Memberships.is_manager for the current tenant login (CLAUDE.md's
// Memberships note) — same "stash it once, read it for UI-only decisions"
// pattern as ROLE_KEY, since it's likewise handed to the frontend only in
// the login/lobby-login response, not on every /auth/me session restore.
const IS_MANAGER_KEY = 'caser_is_manager'

export function setStoredRole(role) {
  sessionStorage.setItem(ROLE_KEY, role)
}

export function getStoredRole() {
  return sessionStorage.getItem(ROLE_KEY)
}

export function clearStoredRole() {
  sessionStorage.removeItem(ROLE_KEY)
}

export function setStoredIsManager(isManager) {
  sessionStorage.setItem(IS_MANAGER_KEY, isManager ? '1' : '')
}

export function getStoredIsManager() {
  return sessionStorage.getItem(IS_MANAGER_KEY) === '1'
}

export function clearStoredIsManager() {
  sessionStorage.removeItem(IS_MANAGER_KEY)
}
