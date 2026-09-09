const dateFormatter = new Intl.DateTimeFormat('he-IL', { day: '2-digit', month: 'short', year: 'numeric' })

export function formatDate(isoString) {
  return dateFormatter.format(new Date(isoString))
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Decorative-only: initials + a rotating tonal color, purely to make the
// case list scannable. Not derived from any real per-case data.
const AVATAR_TONES = ['avatar1', 'avatar2', 'avatar3']

export function avatarInitials(title) {
  return title.trim().slice(0, 2)
}

export function avatarTone(index) {
  const tone = AVATAR_TONES[index % AVATAR_TONES.length]
  return { color: `var(--color-${tone})`, background: `var(--color-${tone}-bg)` }
}
