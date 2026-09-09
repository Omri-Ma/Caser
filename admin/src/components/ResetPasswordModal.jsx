import { useState } from 'react'
import Modal from './Modal'
import { FormField, FormError } from './Form'
import { resetMemberPassword } from '../api/members'

// office_manager sets a new password for a member by hand — the interim
// stand-in for real password recovery (CLAUDE.md's Future additions). They
// must use it next login; this never touches the office manager's own
// password.
export default function ResetPasswordModal({ open, member, onClose, onDone }) {
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  function handleClose() {
    setNewPassword('')
    setError(null)
    setDone(false)
    onClose()
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await resetMemberPassword(member.id, newPassword)
      setDone(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (!member) return null

  return (
    <Modal open={open} title={`איפוס סיסמה עבור ${member.identity_name}`} onClose={handleClose}>
      {done ? (
        <>
          <div className="reset-password-success">
            הסיסמה עודכנה בהצלחה. יש למסור אותה ל<bdi>{member.identity_name}</bdi> — יידרש/תידרש להשתמש בה בכניסה הבאה.
          </div>
          <button type="button" className="secondary-button" onClick={() => { handleClose(); onDone() }}>
            סגירה
          </button>
        </>
      ) : (
        <form onSubmit={handleSubmit}>
          <FormError message={error} />
          <FormField label="סיסמה חדשה">
            <input
              type="text"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              minLength={8}
              required
              autoFocus
            />
          </FormField>
          <button type="submit" className="primary-button" disabled={submitting || newPassword.length < 8}>
            {submitting ? 'מאפס…' : 'איפוס סיסמה'}
          </button>
        </form>
      )}
    </Modal>
  )
}
