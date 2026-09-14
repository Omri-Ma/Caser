import { apiFetch } from './client'

const MAX_PAGE_SIZE = 200

export function listInvites({ role, status = 'pending' } = {}) {
  const params = new URLSearchParams({ page: '1', page_size: String(MAX_PAGE_SIZE), status })
  if (role) params.set('role', role)
  return apiFetch(`/invites?${params}`)
}

export function inviteMember(email, role) {
  return apiFetch('/invites', { method: 'POST', body: { email, role } })
}

// Cancel a still-pending invite before anyone has answered it.
export function revokeInvite(inviteId) {
  return apiFetch(`/invites/${inviteId}/revoke`, { method: 'POST' })
}
