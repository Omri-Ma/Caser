import { apiFetch } from './client'

// A firm's lawyer or client roster is realistically well under the API's
// 200 max page size — one call covers the whole list for the assignment
// picker, same shortcut used for a case's assignment list.
const MAX_PAGE_SIZE = 200

export function listMembers({ role } = {}) {
  const params = new URLSearchParams({ page: '1', page_size: String(MAX_PAGE_SIZE) })
  if (role) params.set('role', role)
  return apiFetch(`/members?${params}`)
}
