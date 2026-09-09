import { apiFetch } from './client'

const PAGE_SIZE = 50

export function listTenants({ page = 1 } = {}) {
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) })
  return apiFetch(`/platform/tenants?${params}`)
}

export function getPlatformStats() {
  return apiFetch('/platform/stats')
}

export function suspendTenant(tenantId) {
  return apiFetch(`/platform/tenants/${tenantId}/suspend`, { method: 'POST' })
}

export function reactivateTenant(tenantId) {
  return apiFetch(`/platform/tenants/${tenantId}/reactivate`, { method: 'POST' })
}
