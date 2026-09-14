import { useCallback, useEffect, useState } from 'react'
import { FormError, FormField } from './Form'
import DateInput from './DateInput'
import { exportNarrativePdf, generateNarrative, listNarratives } from '../api/narratives'
import { formatDate } from '../utils/format'
import './NarrativesPanel.css'

const CURRENCY_TEXT = { he: 'ש"ח', en: 'ILS' }

function feeLabel(narrative) {
  const currency = CURRENCY_TEXT[narrative.language] ?? CURRENCY_TEXT.he
  return `${Number(narrative.total_fee).toFixed(2)} ${currency}`
}

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function firstOfMonthIso() {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
}

// Lawyer-only, mirrors WorkHoursPanel — narratives are always firm-internal
// (CLAUDE.md), never rendered/mounted for a client. Exporting a narrative to
// PDF files it as a real internal Document; onDocumentAdded lets the parent
// refresh DocumentsPanel so it shows up there immediately without a second
// full page reload.
export default function NarrativesPanel({ caseId, onDocumentAdded }) {
  const [narratives, setNarratives] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [exportingId, setExportingId] = useState(null)
  const [showHistory, setShowHistory] = useState(false)

  const [formOpen, setFormOpen] = useState(false)
  const [draft, setDraft] = useState({ periodStart: firstOfMonthIso(), periodEnd: todayIso(), language: 'he' })

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    listNarratives(caseId)
      .then((page) => setNarratives(page.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [caseId])

  useEffect(() => {
    load()
  }, [load])

  function openForm() {
    setActionError(null)
    setDraft({ periodStart: firstOfMonthIso(), periodEnd: todayIso(), language: 'he' })
    setFormOpen(true)
  }

  async function handleGenerate(event) {
    event.preventDefault()
    setGenerating(true)
    setActionError(null)
    try {
      await generateNarrative(caseId, draft)
      setFormOpen(false)
      load()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  async function handleExport(narrativeId) {
    setExportingId(narrativeId)
    setActionError(null)
    try {
      await exportNarrativePdf(caseId, narrativeId)
      onDocumentAdded?.()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setExportingId(null)
    }
  }

  const current = narratives && narratives.length > 0 ? narratives[0] : null
  const history = narratives && narratives.length > 1 ? narratives.slice(1) : []

  return (
    <div className="card detail-card detail-narratives-card">
      <div className="documents-toolbar">
        <div className="detail-card-title">נרטיב תיק</div>
        {!formOpen && (
          <button type="button" className="secondary-button work-hours-add-button" onClick={openForm}>
            + יצירת נרטיב חדש
          </button>
        )}
      </div>

      {formOpen && (
        <form className="work-hours-form" onSubmit={handleGenerate}>
          <FormField label="מתאריך">
            <DateInput
              value={draft.periodStart}
              onChange={(iso) => setDraft((d) => ({ ...d, periodStart: iso }))}
              required
            />
          </FormField>
          <FormField label="עד תאריך">
            <DateInput
              value={draft.periodEnd}
              onChange={(iso) => setDraft((d) => ({ ...d, periodEnd: iso }))}
              required
            />
          </FormField>
          <FormField label="שפה">
            <select value={draft.language} onChange={(event) => setDraft((d) => ({ ...d, language: event.target.value }))}>
              <option value="he">עברית</option>
              <option value="en">English</option>
            </select>
          </FormField>
          {actionError && <FormError message={actionError} />}
          <div className="work-hours-form-actions">
            <button type="submit" className="secondary-button" disabled={generating}>
              {generating ? 'מייצר…' : 'יצירה'}
            </button>
            <button type="button" className="detail-title-cancel" onClick={() => setFormOpen(false)}>
              ביטול
            </button>
          </div>
        </form>
      )}

      {!formOpen && actionError && <FormError message={actionError} />}

      {loading && <div className="detail-state">טוען נרטיב…</div>}
      {!loading && error && <div className="detail-state detail-state-error">{error}</div>}
      {!loading && !error && !current && !formOpen && <div className="detail-state">טרם נוצר נרטיב לתיק זה.</div>}

      {!loading && !error && current && (
        <>
          <div className="narrative-current">
            <div className="narrative-meta">
              נוצר בתאריך {formatDate(current.created_at)} · תקופה {formatDate(current.period_start)}–
              {formatDate(current.period_end)} · {Number(current.total_hours).toFixed(2)} שעות · {feeLabel(current)}
            </div>
            <div className="narrative-text">{current.generated_text}</div>
            <button
              type="button"
              className="secondary-button narrative-export-button"
              onClick={() => handleExport(current.id)}
              disabled={exportingId === current.id}
            >
              {exportingId === current.id ? 'מייצא…' : 'ייצוא ל-PDF (מסמך פנימי)'}
            </button>
          </div>

          {history.length > 0 && (
            <div className="narrative-history">
              <button type="button" className="narrative-history-toggle" onClick={() => setShowHistory((v) => !v)}>
                {showHistory ? 'הסתרת היסטוריה' : `היסטוריית נרטיבים (${history.length})`}
              </button>
              {showHistory && (
                <ul className="documents-list">
                  {history.map((narrative) => (
                    <li key={narrative.id} className="documents-row">
                      <div className="documents-row-main">
                        <div className="documents-row-name">
                          {formatDate(narrative.period_start)}–{formatDate(narrative.period_end)} ·{' '}
                          {Number(narrative.total_hours).toFixed(2)} שעות · {feeLabel(narrative)}
                        </div>
                        <div className="documents-row-meta">{formatDate(narrative.created_at)}</div>
                      </div>
                      <div className="documents-row-actions">
                        <button
                          type="button"
                          className="documents-action"
                          onClick={() => handleExport(narrative.id)}
                          disabled={exportingId === narrative.id}
                        >
                          {exportingId === narrative.id ? 'מייצא…' : 'ייצוא ל-PDF'}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
