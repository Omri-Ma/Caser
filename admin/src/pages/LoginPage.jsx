import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { FormField, FormError } from '../components/Form'

export default function LoginPage() {
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
      await login(form)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-card">
      <h1>התחברות למערכת הניהול</h1>
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
      <p className="auth-switch">
        עדיין אין לך משרד? <Link to="/signup">הקמת משרד חדש</Link>
      </p>
    </div>
  )
}
