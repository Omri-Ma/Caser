import { apiFetch } from './client'

// Bounded by one case's realistic narrative-history length, same shortcut
// work_logs.js/documents.js already take for a single case's list.
const PAGE_SIZE = 200

// list: any assigned lawyer, read-only. generate/export: manager-authority
// lawyers only (Memberships.is_manager, CLAUDE.md's Memberships note) —
// server-enforced via require_manager_lawyer; the frontend only decides
// whether to *render* the generate/export controls (NarrativesPanel's
// isManager prop), same UX-convenience-only pattern as every other
// frontend role check in this app.
export function listNarratives(caseId) {
  return apiFetch(`/cases/${caseId}/narratives?page=1&page_size=${PAGE_SIZE}`)
}

export function generateNarrative(caseId, { periodStart, periodEnd, language }) {
  return apiFetch(`/cases/${caseId}/narratives`, {
    method: 'POST',
    body: { period_start: periodStart, period_end: periodEnd, language },
  })
}

export function exportNarrativePdf(caseId, narrativeId, filename) {
  return apiFetch(`/cases/${caseId}/narratives/${narrativeId}/export-pdf`, {
    method: 'POST',
    body: { filename },
  })
}
