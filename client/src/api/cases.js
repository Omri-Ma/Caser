import { apiFetch } from './client'

// 200 is the API's max page size (see server/client_api/core/pagination.py).
// A single lawyer/client's assigned-case count realistically never exceeds
// that in this project, so one call covers the whole list — no need for
// real pagination UI on top of it yet.
const MAX_PAGE_SIZE = 200

export function listMyCases() {
  return apiFetch(`/cases?page=1&page_size=${MAX_PAGE_SIZE}`)
}

export function getMyCase(caseId) {
  return apiFetch(`/cases/${caseId}`)
}
