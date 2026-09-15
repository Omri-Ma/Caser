import { useState } from 'react'
import { Link } from 'react-router-dom'
import { lobbyLogin } from '../api/auth'
import { FormField, FormError } from '../components/Form'
import { redirectToTenant, clientLoginUrl } from '../utils/host'

// office_manager login from the lobby (www.<BASE_DOMAIN>:5174) — the only
// login entry point for a tenant subdomain now (there's no per-tenant
// /login anymore), and specifically the one that works before you know
// (or have typed) a firm's subdomain at all (CLAUDE.md's Multi-tenancy
// architecture). Doesn't know a subdomain up front: the backend resolves
// every firm this identity manages and this screen reacts to however many
// come back — one redirects straight there, more than one shows a picker,
// zero is a clear inline error.
export default function LobbyLoginPage() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [tenants, setTenants] = useState(null)

  function updateField(field) {
    return (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const session = await lobbyLogin(form)
      if (session.tenants.length === 1) {
        redirectToTenant(session.tenants[0].subdomain)
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
              <button
                type="button"
                className="primary-button"
                onClick={() => redirectToTenant(tenant.subdomain)}
              >
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
        <Link to="/forgot-password">שכחת סיסמה?</Link>
      </p>
      <p className="auth-switch">
        עדיין אין לך משרד? <Link to="/signup">הקמת משרד חדש</Link>
      </p>
      <p className="auth-switch">
        עורכ/ת דין או לקוח/ה? <a href={clientLoginUrl()}>מעבר לכניסה של הלקוחות</a>
      </p>
    </div>
  )
}
