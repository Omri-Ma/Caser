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

// super_admin login at the fixed platform address — see PlatformLoginPage.
export function platformLogin({ email, password }) {
  return apiFetch('/auth/platform-login', { method: 'POST', body: { email, password }, redirectOn401: false })
}

export function me() {
  return apiFetch('/auth/me')
}

export function logout() {
  return apiFetch('/auth/logout', { method: 'POST' })
}
