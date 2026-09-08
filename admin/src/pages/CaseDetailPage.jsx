import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import AssignMemberModal from '../components/AssignMemberModal'
import { FormError } from '../components/Form'
import { getCase, listCaseAssignments, unassignFromCase, updateCaseStatus, updateCaseTitle } from '../api/cases'
import { CASE_STATUSES, caseStatusLabel, caseStatusStyle } from '../utils/caseStatus'
import { formatDate } from '../utils/format'
import './CaseDetailPage.css'

export default function CaseDetailPage() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [assignments, setAssignments] = useState(null)
  const [assignmentsLoading, setAssignmentsLoading] = useState(true)
  const [assignmentsError, setAssignmentsError] = useState(null)
  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [removingId, setRemovingId] = useState(null)
  const [assignmentsActionError, setAssignmentsActionError] = useState(null)

  const [titleEditing, setTitleEditing] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const [titleSaving, setTitleSaving] = useState(false)
  const [titleError, setTitleError] = useState(null)

  const [statusSaving, setStatusSaving] = useState(false)
  const [statusError, setStatusError] = useState(null)

  const loadCase = useCallback(() => {
    setLoading(true)
    setError(null)
    getCase(caseId)
      .then(setCaseData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [caseId])

  const loadAssignments = useCallback(() => {
    setAssignmentsLoading(true)
    setAssignmentsError(null)
    listCaseAssignments(caseId)
      .then((page) => setAssignments(page.items))
      .catch((err) => setAssignmentsError(err.message))
      .finally(() => setAssignmentsLoading(false))
  }, [caseId])

  useEffect(() => {
    loadCase()
    loadAssignments()
  }, [loadCase, loadAssignments])

  function startTitleEdit() {
    setTitleDraft(caseData.title)
    setTitleError(null)
    setTitleEditing(true)
  }

  async function saveTitle(event) {
    event.preventDefault()
    const trimmed = titleDraft.trim()
    if (!trimmed) return
    setTitleSaving(true)
    setTitleError(null)
    try {
      const updated = await updateCaseTitle(caseId, trimmed)
      setCaseData(updated)
      setTitleEditing(false)
    } catch (err) {
      setTitleError(err.message)
    } finally {
      setTitleSaving(false)
    }
  }

  async function handleStatusChange(event) {
    const newStatus = event.target.value
    setStatusSaving(true)
    setStatusError(null)
    try {
      const updated = await updateCaseStatus(caseId, newStatus)
      setCaseData(updated)
    } catch (err) {
      setStatusError(err.message)
    } finally {
      setStatusSaving(false)
    }
  }

  function handleAssigned(assignment) {
    setAssignments((prev) => [...(prev ?? []), assignment])
    setAssignModalOpen(false)
  }

  async function handleUnassign(assignment) {
    if (!window.confirm(`להסיר את ${assignment.identity_name} מהתיק? הגישה למסמכים ולשעות שנרשמו תיאבד מיידית.`)) {
      return
    }
    setRemovingId(assignment.id)
    setAssignmentsActionError(null)
    try {
      await unassignFromCase(caseId, assignment.id)
      setAssignments((prev) => prev.filter((a) => a.id !== assignment.id))
    } catch (err) {
      setAssignmentsActionError(err.message)
    } finally {
      setRemovingId(null)
    }
  }

  const lawyers = (assignments ?? []).filter((a) => a.role === 'lawyer')
  const clients = (assignments ?? []).filter((a) => a.role === 'client')
  const assignedMembershipIds = (assignments ?? []).map((a) => a.membership_id)

  return (
    <AppShell activeKey="cases">
      <div className="detail-breadcrumb">
        <button type="button" className="breadcrumb-back" onClick={() => navigate('/cases')}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path d="M16 4l-6 6 6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          חזרה לתיקים
        </button>
      </div>

      {loading && <div className="detail-state">טוען פרטי תיק…</div>}
      {!loading && error && <div className="detail-state detail-state-error">{error}</div>}

      {!loading && !error && caseData && (
        <>
          <div className="detail-header">
            {!titleEditing && (
              <>
                <h1 className="detail-title">{caseData.title}</h1>
                <button type="button" className="detail-edit-title" onClick={startTitleEdit} aria-label="עריכת שם התיק">
                  ✎
                </button>
              </>
            )}
            {titleEditing && (
              <form className="detail-title-form" onSubmit={saveTitle}>
                <input
                  className="detail-title-input"
                  value={titleDraft}
                  onChange={(event) => setTitleDraft(event.target.value)}
                  autoFocus
                  required
                />
                <button type="submit" className="secondary-button" disabled={titleSaving}>
                  {titleSaving ? 'שומר…' : 'שמירה'}
                </button>
                <button type="button" className="detail-title-cancel" onClick={() => setTitleEditing(false)}>
                  ביטול
                </button>
              </form>
            )}

            <span className="chip" style={caseStatusStyle(caseData.status)}>
              {caseStatusLabel(caseData.status)}
            </span>
            <span className="chip detail-id-chip">מס׳ תיק #{caseData.id}</span>

            <select
              className="detail-status-select"
              value={caseData.status}
              onChange={handleStatusChange}
              disabled={statusSaving}
            >
              {CASE_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {caseStatusLabel(status)}
                </option>
              ))}
            </select>

            <div className="detail-header-spacer" />
            <div className="detail-opened">נפתח בתאריך {formatDate(caseData.created_at)}</div>
          </div>
          {titleError && <FormError message={titleError} />}
          {statusError && <FormError message={statusError} />}

          <div className="card detail-card">
            <div className="detail-assign-header">
              <div className="detail-card-title">שיוכים לתיק</div>
              <button type="button" className="secondary-button detail-assign-button" onClick={() => setAssignModalOpen(true)}>
                + שיוך
              </button>
            </div>

            {assignmentsLoading && <div className="detail-state">טוען שיוכים…</div>}
            {!assignmentsLoading && assignmentsError && (
              <div className="detail-state detail-state-error">{assignmentsError}</div>
            )}
            {assignmentsActionError && <FormError message={assignmentsActionError} />}

            {!assignmentsLoading && !assignmentsError && (
              <div className="detail-assign-columns">
                <AssignmentGroup
                  title="עורכי דין"
                  items={lawyers}
                  emptyMessage="אין עורכי דין משויכים לתיק זה."
                  onRemove={handleUnassign}
                  removingId={removingId}
                />
                <AssignmentGroup
                  title="לקוחות"
                  items={clients}
                  emptyMessage="אין לקוחות משויכים לתיק זה."
                  onRemove={handleUnassign}
                  removingId={removingId}
                />
              </div>
            )}
          </div>

          <AssignMemberModal
            open={assignModalOpen}
            caseId={caseId}
            excludeMembershipIds={assignedMembershipIds}
            onClose={() => setAssignModalOpen(false)}
            onAssigned={handleAssigned}
          />
        </>
      )}
    </AppShell>
  )
}

function AssignmentGroup({ title, items, emptyMessage, onRemove, removingId }) {
  return (
    <div className="assign-group">
      <div className="assign-group-title">
        {title} <span className="assign-group-count">({items.length})</span>
      </div>
      {items.length === 0 && <div className="assign-group-empty">{emptyMessage}</div>}
      {items.length > 0 && (
        <ul className="assign-group-list">
          {items.map((item) => (
            <li key={item.id} className="assign-group-row">
              <div>
                <div className="assign-group-name">{item.identity_name}</div>
                <div className="assign-group-email">{item.identity_email}</div>
              </div>
              <button
                type="button"
                className="assign-group-remove"
                onClick={() => onRemove(item)}
                disabled={removingId === item.id}
              >
                {removingId === item.id ? 'מסיר…' : 'הסרה'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
