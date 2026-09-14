import { apiFetch } from './client'

// A firm's lawyer or client roster is realistically well under the API's
// 200 max page size — one call covers the whole list for the assignment
// picker, same shortcut used for a case's assignment list.
const MAX_PAGE_SIZE = 200

export function listMembers({ role, active = true } = {}) {
  const params = new URLSearchParams({ page: '1', page_size: String(MAX_PAGE_SIZE), active: String(active) })
  if (role) params.set('role', role)
  return apiFetch(`/members?${params}`)
}

export function deactivateMember(membershipId) {
  return apiFetch(`/members/${membershipId}/deactivate`, { method: 'POST' })
}

export function updatePublicVisibility(membershipId, showOnPublicPage) {
  return apiFetch(`/members/${membershipId}/public-visibility`, {
    method: 'PATCH',
    body: { show_on_public_page: showOnPublicPage },
  })
}

// Promote a lawyer to office_manager, or demote an office_manager back to
// lawyer — never involves a client (CLAUDE.md's Memberships note).
export function updateMemberRole(membershipId, role) {
  return apiFetch(`/members/${membershipId}/role`, { method: 'PATCH', body: { role } })
}

// Lawyer-only billing rate, feeds Narratives.total_fee (CLAUDE.md's
// Memberships note).
export function updateHourlyRate(membershipId, hourlyRate) {
  return apiFetch(`/members/${membershipId}/hourly-rate`, { method: 'PATCH', body: { hourly_rate: hourlyRate } })
}
