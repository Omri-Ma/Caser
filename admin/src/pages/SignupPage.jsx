import { useState } from 'react'
import { Link } from 'react-router-dom'
import { signup } from '../api/auth'
import { FormField, FormError } from '../components/Form'
import PasswordConfirmFields, { passwordsValid } from '../components/PasswordConfirmFields'
import { redirectToTenant } from '../utils/host'

export default function SignupPage() {
  const [form, setForm] = useState({
    firmName: '',
    subdomain: '',
    adminName: '',
    adminEmail: '',
    adminPassword: '',
  })
  const [confirmPassword, setConfirmPassword] = useState('')
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
      await signup(form)
      redirectToTenant(form.subdomain)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-card">
      <h1>הקמת משרד חדש</h1>
      <form onSubmit={handleSubmit}>
        <FormError message={error} />
        <FormField label="שם המשרד">
          <input value={form.firmName} onChange={updateField('firmName')} required />
        </FormField>
        <FormField label="תת-דומיין (למשל: acme)">
          <input value={form.subdomain} onChange={updateField('subdomain')} required pattern="[a-z0-9\-]+" />
        </FormField>
        <FormField label="שם מלא (מנהל המשרד)">
          <input value={form.adminName} onChange={updateField('adminName')} required />
        </FormField>
        <FormField label="אימייל">
          <input type="email" value={form.adminEmail} onChange={updateField('adminEmail')} required />
        </FormField>
        <PasswordConfirmFields
          password={form.adminPassword}
          onPasswordChange={updateField('adminPassword')}
          confirmPassword={confirmPassword}
          onConfirmPasswordChange={(event) => setConfirmPassword(event.target.value)}
          passwordLabel="סיסמה (8 תווים לפחות)"
        />
        <button type="submit" className="primary-button" disabled={submitting || !passwordsValid(form.adminPassword, confirmPassword)}>
          {submitting ? 'מקים משרד…' : 'הקמת משרד'}
        </button>
      </form>
      <p className="auth-switch">
        כבר יש לך חשבון במשרד הזה? <Link to="/login">התחברות</Link>
      </p>
    </div>
  )
}
