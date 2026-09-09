import { apiFetch } from './client'

export function getTenant() {
  return apiFetch('/tenant')
}

export function updateTenant({ name, logoUrl, primaryColor }) {
  return apiFetch('/tenant', { method: 'PATCH', body: { name, logo_url: logoUrl || null, primary_color: primaryColor || null } })
}
