import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { register } from '../api/auth'
import { FormField, FormError } from '../components/Form'
import PasswordConfirmFields, { passwordsValid } from '../components/PasswordConfirmFields'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  // Prefilled (not locked) from an invite link's ?email= — CLAUDE.md's
  // MembershipInvites note: registering with that exact email is itself
  // the acceptance, resolved server-side purely by email match, so nothing
  // breaks if this gets edited before submitting.
  const [form, setForm] = useState({ name: '', email: searchParams.get('email') || '', password: '' })
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
      await register(form)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-card">
      <h1>הרשמה</h1>
      <form onSubmit={handleSubmit}>
        <FormError message={error} />
        <FormField label="שם מלא">
          <input value={form.name} onChange={updateField('name')} required />
        </FormField>
        <FormField label="אימייל">
          <input type="email" value={form.email} onChange={updateField('email')} required />
        </FormField>
        <PasswordConfirmFields
          password={form.password}
          onPasswordChange={updateField('password')}
          confirmPassword={confirmPassword}
          onConfirmPasswordChange={(event) => setConfirmPassword(event.target.value)}
          passwordLabel="סיסמה (8 תווים לפחות)"
        />
        <button type="submit" className="primary-button" disabled={submitting || !passwordsValid(form.password, confirmPassword)}>
          {submitting ? 'נרשם…' : 'הרשמה'}
        </button>
      </form>
      <p className="auth-switch">
        כבר יש לך חשבון? <Link to="/login">התחברות</Link>
      </p>
    </div>
  )
}
