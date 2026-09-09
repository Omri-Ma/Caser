import { apiFetch } from './client'

// 200 is the API's max page size (see server/client_api/core/pagination.py).
// A single lawyer/client's assigned-case count realistically never exceeds
// that in this project, so one call covers the whole list — no need for
// real pagination UI on top of it yet.
const MAX_PAGE_SIZE = 200

export function listMyCases({ search, status } = {}) {
  const params = new URLSearchParams({ page: '1', page_size: String(MAX_PAGE_SIZE) })
  if (search) params.set('search', search)
  if (status) params.set('status', status)
  return apiFetch(`/cases?${params}`)
}

export function getMyCase(caseId) {
  return apiFetch(`/cases/${caseId}`)
}
