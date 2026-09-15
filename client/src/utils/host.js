// The lobby (www.<BASE_DOMAIN>) is the reserved, non-tenant address
// multi-firm login uses — there's no subdomain to resolve yet there
// (CLAUDE.md's Multi-tenancy architecture). Mirrors admin/'s own
// isLobbyHost() — same convention, kept per-app since client/ and admin/
// don't share frontend code (CLAUDE.md's Code quality).
export function isLobbyHost() {
  return window.location.hostname.split('.')[0] === 'www'
}

const BASE_DOMAIN = import.meta.env.VITE_BASE_DOMAIN

// A hard redirect, not client-side navigation: the lobby and a tenant
// subdomain are different origins, so React Router has no way to route
// there — the target tenant's session cookie already works without a
// second login, since it's scoped to the base domain, not to www specifically.
export function redirectToTenant(subdomain, path = '/') {
  const port = window.location.port ? `:${window.location.port}` : ''
  window.location.assign(`${window.location.protocol}//${subdomain}.${BASE_DOMAIN}${port}${path}`)
}

// Where the lobby's general homepage (marketing + firm directory) lives —
// a logged-in client can navigate back to it from inside the authenticated
// app (CLAUDE.md: "Reachable from client/ ... not just anonymous
// visitors"), even though the current page is on a different origin.
export function lobbyHomeUrl() {
  const port = window.location.port ? `:${window.location.port}` : ''
  return `${window.location.protocol}//www.${BASE_DOMAIN}${port}/`
}

// Where the lobby's login page lives — a tenant subdomain has no /login of
// its own anymore (lawyer/client only ever log in via the lobby), so this
// is where AppShell sends a logged-out/expired-session visitor.
export function lobbyLoginUrl() {
  const port = window.location.port ? `:${window.location.port}` : ''
  return `${window.location.protocol}//www.${BASE_DOMAIN}${port}/login`
}

// The right login target for a failed/expired session, wherever this code
// happens to be running. The lobby keeps its own /login (to avoid
// redirecting to itself); every tenant subdomain goes there instead, since
// it no longer has a local /login.
export function loginRedirectUrl() {
  if (isLobbyHost()) return '/login'
  return lobbyLoginUrl()
}

const ADMIN_APP_PORT = import.meta.env.VITE_ADMIN_APP_PORT

// Where admin/'s lobby signup page lives, for someone reading client/'s
// (own) lobby who actually wants to found a firm rather than log into one
// — a cross-app link, not a cross-tenant one, so it needs admin/'s own port
// (5174 locally) rather than the current page's, same reasoning as
// redirectToTenant's cross-subdomain hard redirect (CLAUDE.md's Multi-
// tenancy architecture: locally distinguished by port, a subdomain suffix
// in production).
export function adminSignupUrl() {
  const port = ADMIN_APP_PORT ? `:${ADMIN_APP_PORT}` : ''
  return `${window.location.protocol}//www.${BASE_DOMAIN}${port}/signup`
}
