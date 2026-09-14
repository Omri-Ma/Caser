import { apiFetch } from './client'

export function listMyInvites() {
  return apiFetch('/invites')
}

export function acceptInvite(inviteId) {
  return apiFetch(`/invites/${inviteId}/accept`, { method: 'POST' })
}

export function declineInvite(inviteId) {
  return apiFetch(`/invites/${inviteId}/decline`, { method: 'POST' })
}
