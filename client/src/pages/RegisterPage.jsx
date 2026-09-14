import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { register } from '../api/auth'
import { listMyInvites, acceptInvite, declineInvite } from '../api/invites'
import { FormField, FormError } from '../components/Form'
import PasswordConfirmFields, { passwordsValid } from '../components/PasswordConfirmFields'

const ROLE_LABELS = {
  lawyer: 'עורך/ת דין',
  client: 'לקוח/ה',
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  // Prefilled (not locked) from an invite link's ?email= — nothing breaks
  // if this gets edited before submitting, since resolving the invite is a
  // separate, explicit step after registration now (see below).
  const [form, setForm] = useState({ name: '', email: searchParams.get('email') || '', password: '' })
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Populated only after a successful registration — CLAUDE.md's
  // MembershipInvites note (reversed from an earlier draft): registering
  // for an invited email is NOT itself the acceptance. Creating an account
  // and agreeing to join a specific firm are two separate, deliberate acts,
  // so a freshly-registered identity lands on the same explicit
  // accept/decline screen an already-registered invitee sees at lobby
  // login, rather than being silently added anywhere.
  const [invites, setInvites] = useState(null)
  const [inviteError, setInviteError] = useState(null)
  const [respondingId, setRespondingId] = useState(null)

  function updateField(field) {
    return (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register(form)
      const pending = await listMyInvites().catch(() => [])
      if (pending.length === 0) {
        navigate('/')
      } else {
        setInvites(pending)
      }
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
      await acceptInvite(invite.invite_id)
      setInvites((prev) => prev.filter((i) => i.invite_id !== invite.invite_id))
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

  if (invites !== null) {
    return (
      <div className="page-card">
        <h1>ברוכ/ה הבא/ה ל-Caser</h1>
        {invites.length > 0 ? (
          <>
            <p className="auth-switch">החשבון נוצר בהצלחה. הוזמנת להצטרף למשרדים הבאים:</p>
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
        ) : (
          <p className="auth-switch">כל ההזמנות טופלו.</p>
        )}
        <button type="button" className="primary-button" onClick={() => navigate('/')}>
          המשך
        </button>
      </div>
    )
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
