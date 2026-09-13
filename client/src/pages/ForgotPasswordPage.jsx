import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../api/auth'
import { FormField, FormError } from '../components/Form'

// Lobby-only (www.<BASE_DOMAIN>) — a forgotten password is an
// Identities-level problem, not a per-firm one, so there's no subdomain to
// be on when requesting a reset (CLAUDE.md's PasswordResetTokens note).
// Always shows the same generic confirmation regardless of whether the
// email matched a real account — the backend response is deliberately
// identical either way, so this screen never branches on it.
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await forgotPassword(email.trim())
      setSubmitted(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="page-card">
        <h1>בדיקת דוא״ל</h1>
        <p className="auth-switch">
          אם קיים חשבון עם כתובת האימייל <bdi>{email.trim()}</bdi>, נשלח אליו קישור לאיפוס הסיסמה.
        </p>
        <p className="auth-switch">
          סביבת פיתוח — אין שליחת מייל אמיתית: הקישור מופיע ב
          <Link to={`/dev-outbox?email=${encodeURIComponent(email.trim())}`}>תיבת הדואר לפיתוח</Link>.
        </p>
        <p className="auth-switch">
          <Link to="/login">חזרה להתחברות</Link>
        </p>
      </div>
    )
  }

  return (
    <div className="page-card">
      <h1>שכחתי סיסמה</h1>
      <form onSubmit={handleSubmit}>
        <FormError message={error} />
        <FormField label="אימייל">
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoFocus />
        </FormField>
        <button type="submit" className="primary-button" disabled={submitting || !email.trim()}>
          {submitting ? 'שולח…' : 'שליחת קישור לאיפוס'}
        </button>
      </form>
      <p className="auth-switch">
        <Link to="/login">חזרה להתחברות</Link>
      </p>
    </div>
  )
}
