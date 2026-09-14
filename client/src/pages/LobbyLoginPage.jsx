import { useState } from 'react'
import { Link } from 'react-router-dom'
import { lobbyLogin } from '../api/auth'
import { acceptInvite, declineInvite } from '../api/invites'
import { FormField, FormError } from '../components/Form'
import { redirectToTenant } from '../utils/host'
import './LobbyLoginPage.css'

const ROLE_LABELS = {
  lawyer: 'עורך/ת דין',
  client: 'לקוח/ה',
}

// lawyer/client login from the lobby (www.<BASE_DOMAIN>:5173) — the only
// login entry point for a tenant subdomain now (there's no per-tenant
// /login anymore), and specifically the one that works before you know
// (or have typed) a firm's subdomain at all (CLAUDE.md's Multi-tenancy
// architecture). Doesn't know a subdomain up front: the backend resolves
// every firm this identity is a lawyer/client at and this screen reacts to
// however many come back — one redirects straight there, more than one
// shows a picker, zero is a clear inline error.
//
// Also the one place a pending MembershipInvite surfaces (CLAUDE.md's
// MembershipInvites note: "the invite shows up as a pending action for
// them the next time they log in") — shown above the tenant picker so it
// can't be missed, and never auto-skipped past even when there's only one
// existing tenant, so the user always gets a chance to respond first.
export default function LobbyLoginPage() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [tenants, setTenants] = useState(null)
  const [invites, setInvites] = useState([])
  const [inviteError, setInviteError] = useState(null)
  const [respondingId, setRespondingId] = useState(null)

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
      if (session.pending_invites.length === 0 && session.tenants.length === 1) {
        goToTenant(session.tenants[0])
        return
      }
      setTenants(session.tenants)
      setInvites(session.pending_invites)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleAccept(invite) {
    setRespondingId(invite.invite_id)
    setInviteError(null)
    try {
      const joinedTenant = await acceptInvite(invite.invite_id)
      setInvites((prev) => prev.filter((i) => i.invite_id !== invite.invite_id))
      setTenants((prev) => [...(prev || []), joinedTenant])
    } catch (err) {
      setInviteError(err.message)
    } finally {
      setRespondingId(null)
    }
  }

  async function handleDecline(invite) {
    setRespondingId(invite.invite_id)
    setInviteError(null)
    try {
      await declineInvite(invite.invite_id)
      setInvites((prev) => prev.filter((i) => i.invite_id !== invite.invite_id))
    } catch (err) {
      setInviteError(err.message)
    } finally {
      setRespondingId(null)
    }
  }

  if (tenants !== null) {
    return (
      <div className="page-card">
        <h1>ברוכ/ה הבא/ה</h1>

        {invites.length > 0 && (
          <>
            <p className="auth-switch">הוזמנת להצטרף למשרדים הבאים:</p>
            <FormError message={inviteError} />
            <ul className="tenant-picker invite-picker">
              {invites.map((invite) => (
                <li key={invite.invite_id} className="invite-picker-row">
                  <div>
                    <div className="member-name">{invite.firm_name}</div>
                    <div className="member-email">{ROLE_LABELS[invite.role] || invite.role}</div>
                  </div>
                  <div className="invite-picker-actions">
                    <button
                      type="button"
                      className="primary-button"
                      disabled={respondingId === invite.invite_id}
                      onClick={() => handleAccept(invite)}
                    >
                      קבלה
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={respondingId === invite.invite_id}
                      onClick={() => handleDecline(invite)}
                    >
                      דחייה
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}

        {tenants.length > 0 && (
          <>
            <p className="auth-switch">{tenants.length === 1 ? 'כניסה למשרד:' : 'מחובר/ת ליותר ממשרד אחד — לאיזה מהם להיכנס?'}</p>
            <ul className="tenant-picker">
              {tenants.map((tenant) => (
                <li key={tenant.tenant_id}>
                  <button type="button" className="primary-button" onClick={() => goToTenant(tenant)}>
                    {tenant.firm_name}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        {tenants.length === 0 && invites.length === 0 && (
          <p className="auth-switch">כל ההזמנות טופלו, ואין כרגע משרד להיכנס אליו.</p>
        )}
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
