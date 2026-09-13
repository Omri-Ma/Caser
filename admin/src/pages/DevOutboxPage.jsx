import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getDevOutbox } from '../api/auth'

// Dev-only stand-in for real email delivery (CLAUDE.md's Future additions —
// there's no SMTP provider set up in this exercise). A visibly reachable
// page rather than digging through server logs: lists the reset links
// ForgotPasswordPage's requests actually generated, for the given email.
export default function DevOutboxPage() {
  const [searchParams] = useSearchParams()
  const email = searchParams.get('email') || ''
  const [entries, setEntries] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getDevOutbox(email)
      .then(setEntries)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [email])

  return (
    <div className="page-card">
      <h1>תיבת דואר לפיתוח</h1>
      <p className="auth-switch">
        סביבת פיתוח בלבד — כאן מופיעים קישורי איפוס הסיסמה במקום שליחת מייל אמיתית.
        {email && <> מציג תוצאות עבור <bdi>{email}</bdi>.</>}
      </p>

      {loading && <div className="cases-state">טוען…</div>}
      {!loading && error && <div className="cases-state cases-state-error">{error}</div>}
      {!loading && !error && entries && entries.length === 0 && (
        <div className="cases-state">אין קישורי איפוס עדיין{email ? ' עבור כתובת זו' : ''}.</div>
      )}
      {!loading && !error && entries && entries.length > 0 && (
        <ul className="tenant-picker">
          {entries.map((entry, index) => (
            <li key={index}>
              <div className="member-email">{entry.email}</div>
              <a href={entry.link}>{entry.link}</a>
            </li>
          ))}
        </ul>
      )}

      <p className="auth-switch">
        <Link to="/login">חזרה להתחברות</Link>
      </p>
    </div>
  )
}
