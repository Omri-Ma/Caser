import { useCallback, useEffect, useMemo, useState } from 'react'
import { FormError, FormField } from './Form'
import { createWorkLog, deleteWorkLog, listWorkLogs, updateWorkLog } from '../api/work_logs'
import { formatDate } from '../utils/format'
import './WorkHoursPanel.css'

const emptyDraft = { date: new Date().toISOString().slice(0, 10), hours: '', description: '' }

// Lawyer-only panel (never rendered for a client — CaseDetailPage decides
// that, WorkLogs aren't client-visible at all per CLAUDE.md). Any lawyer
// assigned to the case can edit/delete any entry on it, not just their own,
// same broad authority as DocumentsPanel.
export default function WorkHoursPanel({ caseId, caseClosed }) {
  const [entries, setEntries] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [formOpen, setFormOpen] = useState(false)
  const [draft, setDraft] = useState(emptyDraft)
  const [formError, setFormError] = useState(null)
  const [saving, setSaving] = useState(false)

  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState(emptyDraft)
  const [rowError, setRowError] = useState(null)
  const [actioningId, setActioningId] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    listWorkLogs(caseId)
      .then((page) => setEntries(page.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [caseId])

  useEffect(() => {
    load()
  }, [load])

  const totalHours = useMemo(() => (entries ?? []).reduce((sum, entry) => sum + Number(entry.hours), 0), [entries])

  function openForm() {
    setDraft(emptyDraft)
    setFormError(null)
    setFormOpen(true)
  }

  async function handleCreate(event) {
    event.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await createWorkLog(caseId, draft)
      setFormOpen(false)
      load()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSaving(false)
    }
  }

  function startEdit(entry) {
    setEditingId(entry.id)
    setEditDraft({ date: entry.date, hours: String(entry.hours), description: entry.description || '' })
    setRowError(null)
  }

  async function handleSaveEdit(event, entryId) {
    event.preventDefault()
    setActioningId(entryId)
    setRowError(null)
    try {
      await updateWorkLog(caseId, entryId, editDraft)
      setEditingId(null)
      load()
    } catch (err) {
      setRowError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  async function handleDelete(entry) {
    if (!window.confirm('למחוק את רישום השעות הזה?')) return
    setActioningId(entry.id)
    setRowError(null)
    try {
      await deleteWorkLog(caseId, entry.id)
      load()
    } catch (err) {
      setRowError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  return (
    <div className="card detail-card detail-hours-card">
      <div className="documents-toolbar">
        <div className="detail-card-title">שעות עבודה</div>
        {!caseClosed && !formOpen && (
          <button type="button" className="secondary-button work-hours-add-button" onClick={openForm}>
            + רישום שעות
          </button>
        )}
      </div>
      {caseClosed && <div className="documents-closed-note">התיק סגור — לא ניתן לרשום, לערוך או למחוק שעות.</div>}

      {formOpen && (
        <form className="work-hours-form" onSubmit={handleCreate}>
          <FormField label="תאריך">
            <input
              type="date"
              value={draft.date}
              onChange={(event) => setDraft((d) => ({ ...d, date: event.target.value }))}
              required
            />
          </FormField>
          <FormField label="שעות">
            <input
              type="number"
              step="0.25"
              min="0.25"
              max="24"
              value={draft.hours}
              onChange={(event) => setDraft((d) => ({ ...d, hours: event.target.value }))}
              required
            />
          </FormField>
          <FormField label="תיאור">
            <input
              type="text"
              value={draft.description}
              onChange={(event) => setDraft((d) => ({ ...d, description: event.target.value }))}
              placeholder="אופציונלי"
            />
          </FormField>
          {formError && <FormError message={formError} />}
          <div className="work-hours-form-actions">
            <button type="submit" className="secondary-button" disabled={saving}>
              {saving ? 'שומר…' : 'שמירה'}
            </button>
            <button type="button" className="work-hours-form-cancel" onClick={() => setFormOpen(false)}>
              ביטול
            </button>
          </div>
        </form>
      )}

      {rowError && <FormError message={rowError} />}

      {loading && <div className="detail-state">טוען שעות עבודה…</div>}
      {!loading && error && <div className="detail-state detail-state-error">{error}</div>}
      {!loading && !error && entries && entries.length === 0 && (
        <div className="detail-state">אין רישומי שעות בתיק זה עדיין.</div>
      )}
      {!loading && !error && entries && entries.length > 0 && (
        <>
          <div className="work-hours-total">סה״כ {totalHours.toFixed(2)} שעות</div>
          <ul className="documents-list">
            {entries.map((entry) =>
              editingId === entry.id ? (
                <li key={entry.id} className="documents-row work-hours-edit-row">
                  <form className="work-hours-form work-hours-inline-form" onSubmit={(event) => handleSaveEdit(event, entry.id)}>
                    <input
                      type="date"
                      value={editDraft.date}
                      onChange={(event) => setEditDraft((d) => ({ ...d, date: event.target.value }))}
                      required
                    />
                    <input
                      type="number"
                      step="0.25"
                      min="0.25"
                      max="24"
                      value={editDraft.hours}
                      onChange={(event) => setEditDraft((d) => ({ ...d, hours: event.target.value }))}
                      required
                    />
                    <input
                      type="text"
                      value={editDraft.description}
                      onChange={(event) => setEditDraft((d) => ({ ...d, description: event.target.value }))}
                      placeholder="אופציונלי"
                    />
                    <div className="work-hours-form-actions">
                      <button type="submit" className="secondary-button" disabled={actioningId === entry.id}>
                        שמירה
                      </button>
                      <button type="button" className="work-hours-form-cancel" onClick={() => setEditingId(null)}>
                        ביטול
                      </button>
                    </div>
                  </form>
                </li>
              ) : (
                <li key={entry.id} className="documents-row">
                  <div className="documents-row-main">
                    <div className="documents-row-name">
                      {entry.hours} שעות · {formatDate(entry.date)}
                    </div>
                    <div className="documents-row-meta">
                      {entry.lawyer_name}
                      {entry.description ? ` · ${entry.description}` : ''}
                    </div>
                  </div>
                  {!caseClosed && (
                    <div className="documents-row-actions">
                      <button type="button" className="documents-action" onClick={() => startEdit(entry)} disabled={actioningId === entry.id}>
                        עריכה
                      </button>
                      <button
                        type="button"
                        className="documents-action documents-action-danger"
                        onClick={() => handleDelete(entry)}
                        disabled={actioningId === entry.id}
                      >
                        מחיקה
                      </button>
                    </div>
                  )}
                </li>
              ),
            )}
          </ul>
        </>
      )}
    </div>
  )
}
