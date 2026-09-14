import { apiFetch } from './client'

const PAGE_SIZE = 50
// A case's assignment list is bounded by how many people can realistically
// work one case — well under the API's 200 max page size, so one call
// covers it, same shortcut client/'s cases.js already takes for a single
// lawyer/client's assigned-case list.
const ASSIGNMENTS_PAGE_SIZE = 200

export function listCases({ page = 1, status, search, practiceArea } = {}) {
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) })
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  if (practiceArea) params.set('practice_area', practiceArea)
  return apiFetch(`/cases?${params}`)
}

export function setCaseTags(caseId, practiceAreas) {
  return apiFetch(`/cases/${caseId}/tags`, { method: 'PUT', body: { practice_areas: practiceAreas } })
}

export function getCase(caseId) {
  return apiFetch(`/cases/${caseId}`)
}

export function createCase(title) {
  return apiFetch('/cases', { method: 'POST', body: { title } })
}

export function updateCaseTitle(caseId, title) {
  return apiFetch(`/cases/${caseId}`, { method: 'PATCH', body: { title } })
}

export function updateCaseStatus(caseId, status) {
  return apiFetch(`/cases/${caseId}/status`, { method: 'PATCH', body: { status } })
}

export function listCaseAssignments(caseId) {
  return apiFetch(`/cases/${caseId}/assignments?page=1&page_size=${ASSIGNMENTS_PAGE_SIZE}`)
}

export function assignToCase(caseId, membershipId) {
  return apiFetch(`/cases/${caseId}/assignments`, { method: 'POST', body: { membership_id: membershipId } })
}

export function unassignFromCase(caseId, assignmentId) {
  return apiFetch(`/cases/${caseId}/assignments/${assignmentId}`, { method: 'DELETE' })
}

export function deleteCase(caseId) {
  return apiFetch(`/cases/${caseId}`, { method: 'DELETE' })
}
