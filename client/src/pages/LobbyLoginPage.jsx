import { useState } from 'react'
import { Link } from 'react-router-dom'
import { lobbyLogin } from '../api/auth'
import { FormField, FormError } from '../components/Form'
import { redirectToTenant } from '../utils/host'

// lawyer/client login from the lobby (www.<BASE_DOMAIN>:5173) — the one
// entry point for someone who doesn't know (or hasn't yet typed) their
// firm's subdomain (CLAUDE.md's Multi-tenancy architecture). Unlike the
// per-tenant LoginPage, this doesn't know a subdomain up front: the backend
// resolves every firm this identity is a lawyer/client at and this screen
// reacts to however many come back — one redirects straight there, more
// than one shows a picker, zero is a clear inline error.
export default function LobbyLoginPage() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [tenants, setTenants] = useState(null)

  function updateField(field) {
    return (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  function goToTenant(tenant) {
    // role travels as a query param — the tenant subdomain is a different
    // origin and can't read anything stored here (see api/auth.js's
    // lobbyLogin and App.jsx's role-param bootstrap).
    redirectToTenant(tenant.subdomain, `/cases?role=${tenant.role}`)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const session = await lobbyLogin(form)
      if (session.tenants.length === 1) {
        goToTenant(session.tenants[0])
      } else {
        setTenants(session.tenants)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (tenants) {
    return (
      <div className="page-card">
        <h1>בחירת משרד</h1>
        <p className="auth-switch">מחובר/ת ליותר ממשרד אחד — לאיזה מהם להיכנס?</p>
        <ul className="tenant-picker">
          {tenants.map((tenant) => (
            <li key={tenant.tenant_id}>
              <button type="button" className="primary-button" onClick={() => goToTenant(tenant)}>
                {tenant.firm_name}
              </button>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  return (
    <div className="page-card">
      <h1>התחברות</h1>
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
        <Link to="/forgot-password">שכחת סיסמה?</Link>
      </p>
    </div>
  )
}
