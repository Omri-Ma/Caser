// The membership role for the current tenant login. /auth/me (session
// restore on page load) only returns identity fields, not role — role is
// only ever handed to the frontend once, in the /auth/login response — so
// we stash it here for UI-only decisions (e.g. which document folder tabs
// to show). This is display convenience, never a security boundary: real
// role enforcement happens server-side on every request regardless.
const ROLE_KEY = 'caser_role'

export function setStoredRole(role) {
  sessionStorage.setItem(ROLE_KEY, role)
}

export function getStoredRole() {
  return sessionStorage.getItem(ROLE_KEY)
}

export function clearStoredRole() {
  sessionStorage.removeItem(ROLE_KEY)
}
