// This app is reachable at two very different kinds of address: any tenant
// subdomain (office1.lvh.me — the normal office_manager CMS) or the one
// fixed platform address (platform.lvh.me — the super_admin login and
// dashboard). Same bundle, same routes file, branching purely on hostname —
// see App.jsx. Mirrors how admin_api's own platform-login route decides
// this server-side (shared/tenant.py's PLATFORM_HOST).
export function isPlatformHost() {
  return window.location.hostname.split('.')[0] === 'platform'
}

// The lobby (www.<BASE_DOMAIN>) is the reserved, non-tenant address signup
// and multi-firm login use — there's no subdomain to resolve yet at either
// of those (CLAUDE.md's Multi-tenancy architecture). Same branching pattern
// as isPlatformHost() above, just a third case in App.jsx's routes.
export function isLobbyHost() {
  return window.location.hostname.split('.')[0] === 'www'
}

const BASE_DOMAIN = import.meta.env.VITE_BASE_DOMAIN

// A hard redirect, not client-side navigation: the lobby and a tenant
// subdomain are different origins, so React Router has no way to route
// there — used by both SignupPage (the tenant didn't exist until this
// request just created it) and the lobby login (the target tenant's session
// cookie already works there without a second login, since it's scoped to
// the base domain, not to www specifically).
export function redirectToTenant(subdomain, path = '/') {
  const port = window.location.port ? `:${window.location.port}` : ''
  window.location.assign(`${window.location.protocol}//${subdomain}.${BASE_DOMAIN}${port}${path}`)
}

// Plain <a> target (not a react-router Link) for a tenant subdomain's
// LoginPage to point at the lobby's signup — different origin, same reason
// redirectToTenant() above uses a hard navigation instead of client routing.
export function lobbySignupUrl() {
  const port = window.location.port ? `:${window.location.port}` : ''
  return `${window.location.protocol}//www.${BASE_DOMAIN}${port}/signup`
}
