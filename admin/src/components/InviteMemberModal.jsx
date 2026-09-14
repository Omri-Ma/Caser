import { useState } from 'react'
import Modal from './Modal'
import { FormField, FormError } from './Form'
import { inviteMember } from '../api/invites'

// Invite a lawyer or client to this firm, by email — role is fixed by
// which button opened this modal (two distinct actions: "invite lawyer" /
// "invite client"), not a picker inside a single generic form, per the
// user's ask for clearer, less ambiguous actions than one combined
// "add contact" modal used to be. This is a real request now, not an
// instant add (CLAUDE.md's MembershipInvites note) — the invited person
// (or, if they have no account yet, whoever registers with that email)
// accepts or declines it themselves.
const ROLE_LABELS = {
  lawyer: 'עורך/ת דין',
  client: 'לקוח/ה',
}

export default function InviteMemberModal({ open, role, onClose, onInvited }) {
  const [email, setEmail] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleClose() {
    setEmail('')
    setError(null)
    onClose()
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await inviteMember(email.trim(), role)
      setEmail('')
      onInvited()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const roleLabel = ROLE_LABELS[role] || role

  return (
    <Modal open={open} title={`הזמנת ${roleLabel}`} onClose={handleClose}>
      <form onSubmit={handleSubmit}>
        <FormError message={error} />
        <FormField label="אימייל">
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="אם אין עדיין חשבון, תישלח הזמנה להרשמה"
            required
            autoFocus
          />
        </FormField>
        <button type="submit" className="primary-button" disabled={submitting || !email.trim()}>
          {submitting ? 'שולח הזמנה…' : 'שליחת הזמנה'}
        </button>
      </form>
    </Modal>
  )
}
