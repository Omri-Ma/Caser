import { useState } from 'react'
import Modal from './Modal'
import { FormField, FormError } from './Form'
import { createCase } from '../api/cases'

// Create-case flow — same modal pattern as every other create flow in this
// app (a single Modal + FormField/FormError, submit button disabled while
// in flight). A case always starts life as "open" (CLAUDE.md), so there's
// no status field here.
export default function NewCaseModal({ open, onClose, onCreated }) {
  const [title, setTitle] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleClose() {
    setTitle('')
    setError(null)
    onClose()
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const created = await createCase(title.trim())
      setTitle('')
      onCreated(created)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal open={open} title="תיק חדש" onClose={handleClose}>
      <form onSubmit={handleSubmit}>
        <FormError message={error} />
        <FormField label="שם התיק">
          <input value={title} onChange={(event) => setTitle(event.target.value)} required autoFocus />
        </FormField>
        <button type="submit" className="primary-button" disabled={submitting || !title.trim()}>
          {submitting ? 'יוצר תיק…' : 'יצירת תיק'}
        </button>
      </form>
    </Modal>
  )
}
