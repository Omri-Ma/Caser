import { apiDownload, apiFetch, apiUpload } from './client'

// Bounded by one case's realistic work-log count, same shortcut documents.js
// already takes for a single case's list.
const PAGE_SIZE = 200

export function listWorkLogs(caseId) {
  return apiFetch(`/cases/${caseId}/work-logs?page=1&page_size=${PAGE_SIZE}`)
}

export function createWorkLog(caseId, { date, hours, description }) {
  return apiFetch(`/cases/${caseId}/work-logs`, { method: 'POST', body: { date, hours, description: description || null } })
}

export function updateWorkLog(caseId, workLogId, { date, hours, description }) {
  return apiFetch(`/cases/${caseId}/work-logs/${workLogId}`, {
    method: 'PATCH',
    body: { date, hours, description: description || null },
  })
}

export function deleteWorkLog(caseId, workLogId) {
  return apiFetch(`/cases/${caseId}/work-logs/${workLogId}`, { method: 'DELETE' })
}

export function downloadWorkLogImportTemplate() {
  return apiDownload('/work-logs/import/template')
}

export function importWorkLogs(file) {
  const formData = new FormData()
  formData.append('file', file)
  return apiUpload('/work-logs/import', formData)
}
