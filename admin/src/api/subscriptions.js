import { apiFetch } from './client'

export function getSubscription() {
  return apiFetch('/subscription')
}

export function switchPlan(plan) {
  return apiFetch('/subscription/plan', { method: 'POST', body: { plan } })
}
