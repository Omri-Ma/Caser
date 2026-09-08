import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { signup } from '../api/auth'
import { FormField, FormError } from '../components/Form'

export default function SignupPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    firmName: '',
    subdomain: '',
    adminName: '',
    adminEmail: '',
    adminPassword: '',
  })
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
      navigate('/')
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
        <FormField label="סיסמה (8 תווים לפחות)">
          <input
            type="password"
            value={form.adminPassword}
            onChange={updateField('adminPassword')}
            required
            minLength={8}
          />
        </FormField>
        <button type="submit" className="primary-button" disabled={submitting}>
          {submitting ? 'מקים משרד…' : 'הקמת משרד'}
        </button>
      </form>
      <p className="auth-switch">
        כבר יש לך חשבון במשרד הזה? <Link to="/login">התחברות</Link>
      </p>
    </div>
  )
}
