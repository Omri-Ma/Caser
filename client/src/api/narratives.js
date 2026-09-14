import { apiFetch } from './client'

// Bounded by one case's realistic narrative-history length, same shortcut
// work_logs.js/documents.js already take for a single case's list.
const PAGE_SIZE = 200

export function listNarratives(caseId) {
  return apiFetch(`/cases/${caseId}/narratives?page=1&page_size=${PAGE_SIZE}`)
}

export function generateNarrative(caseId, { periodStart, periodEnd, language }) {
  return apiFetch(`/cases/${caseId}/narratives`, {
    method: 'POST',
    body: { period_start: periodStart, period_end: periodEnd, language },
  })
}

export function exportNarrativePdf(caseId, narrativeId) {
  return apiFetch(`/cases/${caseId}/narratives/${narrativeId}/export-pdf`, { method: 'POST' })
}
