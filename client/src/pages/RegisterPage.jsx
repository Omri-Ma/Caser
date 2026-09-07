import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../api/auth'
import { FormField, FormError } from '../components/Form'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
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
        <FormField label="סיסמה (8 תווים לפחות)">
          <input type="password" value={form.password} onChange={updateField('password')} required minLength={8} />
        </FormField>
        <button type="submit" className="primary-button" disabled={submitting}>
          {submitting ? 'נרשם…' : 'הרשמה'}
        </button>
      </form>
      <p className="auth-switch">
        כבר יש לך חשבון? <Link to="/login">התחברות</Link>
      </p>
    </div>
  )
}
