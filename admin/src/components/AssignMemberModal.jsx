import { useEffect, useState } from 'react'
import Modal from './Modal'
import { FormError } from './Form'
import { listMembers } from '../api/members'
import { assignToCase } from '../api/cases'
import './AssignMemberModal.css'

// Assign flow for a case: pick an existing lawyer or client membership at
// this firm — never free text (CLAUDE.md requires assignment by picking
// from real memberships, resolved server-side through get_tenant_scoped).
export default function AssignMemberModal({ open, caseId, excludeMembershipIds, onClose, onAssigned }) {
  const [roleTab, setRoleTab] = useState('lawyer')
  const [members, setMembers] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [submitError, setSubmitError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    setMembers(null)
    setLoading(true)
    setError(null)
    setSelectedId(null)
    setSubmitError(null)
    listMembers({ role: roleTab })
      .then((page) => setMembers(page.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [open, roleTab])

  function handleClose() {
    onClose()
  }

  const availableMembers = (members ?? []).filter((m) => !excludeMembershipIds.includes(m.id))

  async function handleAssign() {
    if (!selectedId) return
    setSubmitError(null)
    setSubmitting(true)
    try {
      const assignment = await assignToCase(caseId, selectedId)
      onAssigned(assignment)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal open={open} title="שיוך לתיק" onClose={handleClose}>
      <div className="assign-tabs">
        <button
          type="button"
          className={`assign-tab${roleTab === 'lawyer' ? ' active' : ''}`}
          onClick={() => setRoleTab('lawyer')}
        >
          עורכי דין
        </button>
        <button
          type="button"
          className={`assign-tab${roleTab === 'client' ? ' active' : ''}`}
          onClick={() => setRoleTab('client')}
        >
          לקוחות
        </button>
      </div>

      {loading && <div className="assign-state">טוען…</div>}
      {!loading && error && <div className="assign-state assign-state-error">{error}</div>}
      {!loading && !error && availableMembers.length === 0 && (
        <div className="assign-state">
          {roleTab === 'lawyer' ? 'אין עורכי דין זמינים לשיוך.' : 'אין לקוחות זמינים לשיוך.'}
        </div>
      )}

      {!loading && !error && availableMembers.length > 0 && (
        <div className="assign-picker-list">
          {availableMembers.map((member) => (
            <button
              type="button"
              key={member.id}
              className={`assign-picker-row${selectedId === member.id ? ' selected' : ''}`}
              onClick={() => setSelectedId(member.id)}
            >
              <div>
                <div className="assign-picker-name">{member.identity_name}</div>
                <div className="assign-picker-email">{member.identity_email}</div>
              </div>
              <span className="assign-picker-radio" aria-hidden="true" />
            </button>
          ))}
        </div>
      )}

      <FormError message={submitError} />
      <button
        type="button"
        className="primary-button"
        disabled={!selectedId || submitting}
        onClick={handleAssign}
        style={{ marginTop: 14 }}
      >
        {submitting ? 'משייך…' : 'שיוך'}
      </button>
    </Modal>
  )
}
