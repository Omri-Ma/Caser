// This app is reachable at two very different kinds of address: any tenant
// subdomain (office1.lvh.me — the normal office_manager CMS) or the one
// fixed platform address (platform.lvh.me — the super_admin login and
// dashboard). Same bundle, same routes file, branching purely on hostname —
// see App.jsx. Mirrors how admin_api's own platform-login route decides
// this server-side (shared/tenant.py's PLATFORM_HOST).
export function isPlatformHost() {
  return window.location.hostname.split('.')[0] === 'platform'
}
