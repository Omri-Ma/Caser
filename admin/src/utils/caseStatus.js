// Shared between CasesListPage and CaseDetailPage — status label/color
// mapping lives in one place so both screens render a case's status
// identically.
export const CASE_STATUSES = ['open', 'in_progress', 'on_hold', 'closed']

const LABELS = {
  open: 'פתוח',
  in_progress: 'בטיפול',
  on_hold: 'מוקפא',
  closed: 'סגור',
}

const COLOR_VARS = {
  open: ['--color-success', '--color-success-bg'],
  in_progress: ['--color-info', '--color-info-bg'],
  on_hold: ['--color-warn', '--color-warn-bg'],
  closed: ['--color-gray', '--color-gray-bg'],
}

export function caseStatusLabel(status) {
  return LABELS[status] ?? status
}

export function caseStatusStyle(status) {
  const [fg, bg] = COLOR_VARS[status] ?? COLOR_VARS.closed
  return { color: `var(${fg})`, background: `var(${bg})` }
}
