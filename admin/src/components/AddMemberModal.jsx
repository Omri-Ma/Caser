import { useState } from 'react'
import Modal from './Modal'
import { FormField, FormError } from './Form'
import { addMember } from '../api/members'

// Attach an existing global account to this firm by email — no new password
// is created here (CLAUDE.md: the person logs in with their existing
// account). If this email has a previously-deactivated membership at this
// firm, the backend reactivates that row instead of inserting a new one —
// transparent to this form either way.
const ROLE_OPTIONS = [
  { value: 'lawyer', label: 'עורך/ת דין' },
  { value: 'client', label: 'לקוח/ה' },
  { value: 'office_manager', label: 'מנהל/ת משרד' },
]

export default function AddMemberModal({ open, onClose, onAdded }) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('lawyer')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleClose() {
    setEmail('')
    setRole('lawyer')
    setError(null)
    onClose()
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await addMember(email.trim(), role)
      setEmail('')
      setRole('lawyer')
      onAdded()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal open={open} title="הוספת איש צוות" onClose={handleClose}>
      <form onSubmit={handleSubmit}>
        <FormError message={error} />
        <FormField label="אימייל">
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="האדם חייב להיות רשום כבר במערכת"
            required
            autoFocus
          />
        </FormField>
        <FormField label="תפקיד">
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            {ROLE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </FormField>
        <button type="submit" className="primary-button" disabled={submitting || !email.trim()}>
          {submitting ? 'מוסיף…' : 'הוספה'}
        </button>
      </form>
    </Modal>
  )
}
