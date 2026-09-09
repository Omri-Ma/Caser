const dateFormatter = new Intl.DateTimeFormat('he-IL', { day: '2-digit', month: 'short', year: 'numeric' })
const dateTimeFormatter = new Intl.DateTimeFormat('he-IL', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})
const monthFormatter = new Intl.DateTimeFormat('he-IL', { month: 'short', year: '2-digit' })

export function formatDate(isoString) {
  return dateFormatter.format(new Date(isoString))
}

export function formatDateTime(isoString) {
  return dateTimeFormatter.format(new Date(isoString))
}

// "2026-03" -> a short localized month label ("מרץ 26") for the case-
// activity chart's x-axis.
export function formatMonthLabel(yyyyMm) {
  const [year, month] = yyyyMm.split('-').map(Number)
  return monthFormatter.format(new Date(year, month - 1, 1))
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`
}

// Decorative-only: initials + a rotating tonal color, purely to make lists
// scannable. Not derived from any real per-row data.
const AVATAR_TONES = ['avatar1', 'avatar2', 'avatar3']

export function avatarInitials(title) {
  return title.trim().slice(0, 2)
}

export function avatarTone(index) {
  const tone = AVATAR_TONES[index % AVATAR_TONES.length]
  return { color: `var(--color-${tone})`, background: `var(--color-${tone}-bg)` }
}
