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
