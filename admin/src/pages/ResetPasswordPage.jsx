import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { resetPassword } from '../api/auth'
import { FormField, FormError } from '../components/Form'

// Lobby-only (www.<BASE_DOMAIN>) — the page a reset link (from the dev
// outbox, standing in for a real email) actually points at. token comes
// from the query string; redeeming it bumps token_version server-side,
// invalidating any session that was open under the old password.
export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await resetPassword({ token, newPassword })
      setDone(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (!token) {
    return (
      <div className="page-card">
        <h1>איפוס סיסמה</h1>
        <div className="form-error-banner">קישור האיפוס חסר או שגוי. יש לבקש קישור חדש.</div>
        <p className="auth-switch">
          <Link to="/forgot-password">בקשת קישור חדש</Link>
        </p>
      </div>
    )
  }

  if (done) {
    return (
      <div className="page-card">
        <h1>הסיסמה עודכנה</h1>
        <p className="auth-switch">ניתן להתחבר עכשיו עם הסיסמה החדשה. כל שאר ההתחברויות הפעילות נותקו.</p>
        <p className="auth-switch">
          <Link to="/login">מעבר להתחברות</Link>
        </p>
      </div>
    )
  }

  return (
    <div className="page-card">
      <h1>איפוס סיסמה</h1>
      <form onSubmit={handleSubmit}>
        <FormError message={error} />
        <FormField label="סיסמה חדשה">
          <input
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            minLength={8}
            required
            autoFocus
          />
        </FormField>
        <button type="submit" className="primary-button" disabled={submitting || newPassword.length < 8}>
          {submitting ? 'מעדכן…' : 'עדכון סיסמה'}
        </button>
      </form>
    </div>
  )
}
