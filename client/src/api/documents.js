import { apiDownload, apiFetch, apiUpload } from './client'

// Bounded by one case's realistic document count, same shortcut cases.js
// already takes for a single case's assignment list — one call covers it.
const PAGE_SIZE = 200

export function listDocuments(caseId, { folderType, archived = false } = {}) {
  const params = new URLSearchParams({ page: '1', page_size: String(PAGE_SIZE), archived: String(archived) })
  if (folderType) params.set('folder_type', folderType)
  return apiFetch(`/cases/${caseId}/documents?${params}`)
}

export function uploadDocument(caseId, { file, folderType, confirmReplace = false }) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('folder_type', folderType)
  formData.append('confirm_replace', String(confirmReplace))
  return apiUpload(`/cases/${caseId}/documents`, formData)
}

export function downloadDocument(caseId, documentId) {
  return apiDownload(`/cases/${caseId}/documents/${documentId}/download`)
}

export function archiveDocument(caseId, documentId) {
  return apiFetch(`/cases/${caseId}/documents/${documentId}/archive`, { method: 'POST' })
}

export function restoreDocument(caseId, documentId) {
  return apiFetch(`/cases/${caseId}/documents/${documentId}/restore`, { method: 'POST' })
}

export function reclassifyDocument(caseId, documentId, folderType) {
  return apiFetch(`/cases/${caseId}/documents/${documentId}`, { method: 'PATCH', body: { folder_type: folderType } })
}
