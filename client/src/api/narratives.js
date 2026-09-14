import { apiFetch } from './client'

// Bounded by one case's realistic narrative-history length, same shortcut
// work_logs.js/documents.js already take for a single case's list.
const PAGE_SIZE = 200

// Read-only from client/'s side — generation and PDF export are
// office_manager-only now (admin_api), see CLAUDE.md's Narratives note.
export function listNarratives(caseId) {
  return apiFetch(`/cases/${caseId}/narratives?page=1&page_size=${PAGE_SIZE}`)
}
