import { useEffect, useState } from 'react'

function isoToDisplay(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '')
  if (!match) return ''
  const [, y, m, d] = match
  return `${d}/${m}/${y}`
}

function displayToIso(display) {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(display)
  if (!match) return null
  const [, d, m, y] = match
  const day = Number(d)
  const month = Number(m)
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  return `${y}-${m}-${d}`
}

// Native <input type="date"> renders in whatever format the browser's own
// UI locale uses (Chromium ignores the page/element's lang and dir for
// this — confirmed live, not just from docs), so it can't be forced to
// DD/MM/YYYY the way the rest of this RTL app is. This is a plain masked
// text input instead: always DD/MM/YYYY on screen, converted to/from the
// ISO string (yyyy-mm-dd) the rest of the app and the API already use
// everywhere else — callers see no difference from a native date input.
// Duplicated from client/'s own DateInput rather than shared (CLAUDE.md:
// admin/ and client/ are deliberately separate frontend projects with no
// shared design system between them).
export default function DateInput({ value, onChange, required }) {
  const [text, setText] = useState(isoToDisplay(value))

  useEffect(() => {
    setText(isoToDisplay(value))
  }, [value])

  function handleChange(event) {
    const raw = event.target.value
    setText(raw)
    const iso = displayToIso(raw)
    if (iso) onChange(iso)
  }

  return (
    <input
      type="text"
      inputMode="numeric"
      placeholder="DD/MM/YYYY"
      dir="ltr"
      value={text}
      onChange={handleChange}
      required={required}
    />
  )
}
