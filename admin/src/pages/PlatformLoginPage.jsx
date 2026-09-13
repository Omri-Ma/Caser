import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { platformLogin } from '../api/auth'
import { FormField, FormError } from '../components/Form'

// super_admin's own login screen at the fixed platform address — never a
// signup link here (CLAUDE.md: "no self-service platform-staff signup",
// the first super_admin is a fixed seed.sql row), and it posts to
// /auth/platform-login, not /auth/login (see LobbyLoginPage for the
// office_manager equivalent — the lobby, not a per-tenant page, since
// there is no per-tenant /login anymore).
export default function PlatformLoginPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function updateField(field) {
    return (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await platformLogin(form)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-card">
      <h1>כניסת מנהל פלטפורמה</h1>
      <p className="auth-switch">גישה למנהלי CaseHub בלבד — לא עבור משרדי עורכי דין.</p>
      <form onSubmit={handleSubmit}>
        <FormError message={error} />
        <FormField label="אימייל">
          <input type="email" value={form.email} onChange={updateField('email')} required />
        </FormField>
        <FormField label="סיסמה">
          <input type="password" value={form.password} onChange={updateField('password')} required />
        </FormField>
        <button type="submit" className="primary-button" disabled={submitting}>
          {submitting ? 'מתחבר…' : 'התחברות'}
        </button>
      </form>
    </div>
  )
}
