import { apiDownload, apiFetch } from './client'

export function getDashboardStats() {
  return apiFetch('/dashboard/stats')
}

export function exportDashboardData(resource) {
  return apiDownload(`/dashboard/export?resource=${resource}`)
}
