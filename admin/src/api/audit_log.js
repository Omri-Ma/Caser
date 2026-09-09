import { apiFetch } from './client'

const PAGE_SIZE = 50

export function listAuditLog({ page = 1, action } = {}) {
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) })
  if (action) params.set('action', action)
  return apiFetch(`/audit-log?${params}`)
}
