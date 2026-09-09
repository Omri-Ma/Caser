import { apiFetch } from './client'

// A firm's lawyer or client roster is realistically well under the API's
// 200 max page size — one call covers the whole list for the assignment
// picker, same shortcut used for a case's assignment list.
const MAX_PAGE_SIZE = 200

export function listMembers({ role, includeInactive = false } = {}) {
  const params = new URLSearchParams({ page: '1', page_size: String(MAX_PAGE_SIZE) })
  if (role) params.set('role', role)
  if (includeInactive) params.set('include_inactive', 'true')
  return apiFetch(`/members?${params}`)
}

export function addMember(email, role) {
  return apiFetch('/members', { method: 'POST', body: { email, role } })
}

export function deactivateMember(membershipId) {
  return apiFetch(`/members/${membershipId}/deactivate`, { method: 'POST' })
}

export function resetMemberPassword(membershipId, newPassword) {
  return apiFetch(`/members/${membershipId}/reset-password`, {
    method: 'POST',
    body: { new_password: newPassword },
  })
}
