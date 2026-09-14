import { useEffect, useState } from 'react'
import { listMyInvites, acceptInvite, declineInvite } from '../api/invites'
import { redirectToTenant } from '../utils/host'
import './InvitesInbox.css'

const ROLE_LABELS = {
  lawyer: 'עורך/ת דין',
  client: 'לקוח/ה',
}

// Persistent pending-invites indicator, reachable from anywhere in the
// authenticated app (CLAUDE.md: previously only surfaced once, at lobby
// login time — this makes it available at any point after, e.g. an invite
// that arrives after the person already logged in elsewhere). Same
// accept/decline actions LobbyLoginPage already offers, just always
// reachable instead of a one-time landing-page list.
export default function InvitesInbox() {
  const [invites, setInvites] = useState([])
  const [open, setOpen] = useState(false)
  const [error, setError] = useState(null)
  const [respondingId, setRespondingId] = useState(null)

  function load() {
    listMyInvites()
      .then(setInvites)
      .catch(() => {})
  }

  useEffect(() => {
    load()
  }, [])

  async function handleAccept(invite) {
    setRespondingId(invite.invite_id)
    setError(null)
    try {
      const joinedTenant = await acceptInvite(invite.invite_id)
      setInvites((prev) => prev.filter((i) => i.invite_id !== invite.invite_id))
      // Land straight on the newly-joined firm — same behavior as accepting
      // from the lobby, since there's nothing more useful to do with it here.
      redirectToTenant(joinedTenant.subdomain, `/cases?role=${joinedTenant.role}`)
    } catch (err) {
      setError(err.message)
      setRespondingId(null)
    }
  }

  async function handleDecline(invite) {
    setRespondingId(invite.invite_id)
    setError(null)
    try {
      await declineInvite(invite.invite_id)
      setInvites((prev) => prev.filter((i) => i.invite_id !== invite.invite_id))
    } catch (err) {
      setError(err.message)
    } finally {
      setRespondingId(null)
    }
  }

  return (
    <div className="invites-inbox">
      <button
        type="button"
        className="invites-inbox-toggle"
        onClick={() => setOpen((o) => !o)}
        title="הזמנות ממתינות"
      >
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M12 3a6 6 0 00-6 6v3.5L4 16h16l-2-3.5V9a6 6 0 00-6-6z" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M9.5 19a2.5 2.5 0 005 0" strokeLinecap="round" />
        </svg>
        {invites.length > 0 && <span className="invites-inbox-badge">{invites.length}</span>}
      </button>

      {open && (
        <div className="invites-inbox-panel">
          <div className="invites-inbox-title">הזמנות ממתינות</div>
          {error && <div className="invites-inbox-error">{error}</div>}
          {invites.length === 0 ? (
            <div className="invites-inbox-empty">אין הזמנות ממתינות.</div>
          ) : (
            <ul className="invites-inbox-list">
              {invites.map((invite) => (
                <li key={invite.invite_id} className="invites-inbox-row">
                  <div>
                    <div className="invites-inbox-firm">{invite.firm_name}</div>
                    <div className="invites-inbox-role">{ROLE_LABELS[invite.role] || invite.role}</div>
                  </div>
                  <div className="invites-inbox-actions">
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
          )}
        </div>
      )}
    </div>
  )
}
