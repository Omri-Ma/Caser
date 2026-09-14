import { useCallback, useEffect, useState } from 'react'
import { FormError, FormField } from './Form'
import DateInput from './DateInput'
import { checkMissingRates, exportNarrativePdf, generateNarrative, listNarratives } from '../api/narratives'
import { updateHourlyRate } from '../api/members'
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

function defaultFilename(caseTitle, narrativeId) {
  const slug = caseTitle.trim().replace(/\s+/g, '-').slice(0, 40)
  return `narrative-${slug}-${narrativeId}`
}

// office_manager-only (CLAUDE.md's Narratives note: reversed from an
// earlier any-lawyer-assigned draft once total_fee started depending on
// each lawyer's real, office_manager-set hourly_rate) — office_manager
// sees every case's narratives automatically, same oversight authority as
// Documents/WorkLogs on the admin CaseDetailPage. Narratives are always
// firm-internal; exporting to PDF files it as a real internal Document,
// sharing it with a client afterwards is just the existing Documents
// reclassify-to-client-folder action.
export default function NarrativesPanel({ caseId, caseTitle, onDocumentAdded }) {
  const [narratives, setNarratives] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  const [formOpen, setFormOpen] = useState(false)
  const [draft, setDraft] = useState({ periodStart: firstOfMonthIso(), periodEnd: todayIso(), language: 'he' })

  const [exportTarget, setExportTarget] = useState(null)
  const [filenameDraft, setFilenameDraft] = useState('')
  const [exporting, setExporting] = useState(false)

  // Which lawyers contributing hours to the chosen period still have no
  // (or a zero) hourly_rate — a legitimate but easy-to-miss state that
  // would otherwise silently understate the narrative's total_fee
  // (CLAUDE.md's Narratives note). Re-checked whenever the period changes.
  const [missingRates, setMissingRates] = useState([])
  const [rateEditingId, setRateEditingId] = useState(null)
  const [rateDraft, setRateDraft] = useState('')
  const [rateSaving, setRateSaving] = useState(false)

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

  const refreshMissingRates = useCallback(
    (periodStart, periodEnd) => {
      if (!periodStart || !periodEnd || periodEnd < periodStart) {
        setMissingRates([])
        return
      }
      checkMissingRates(caseId, periodStart, periodEnd)
        .then(setMissingRates)
        .catch(() => setMissingRates([]))
    },
    [caseId],
  )

  useEffect(() => {
    if (!formOpen) return
    refreshMissingRates(draft.periodStart, draft.periodEnd)
  }, [formOpen, draft.periodStart, draft.periodEnd, refreshMissingRates])

  function openForm() {
    setActionError(null)
    setRateEditingId(null)
    setDraft({ periodStart: firstOfMonthIso(), periodEnd: todayIso(), language: 'he' })
    setFormOpen(true)
  }

  function startRateEdit(lawyer) {
    setRateEditingId(lawyer.membership_id)
    setRateDraft(lawyer.hourly_rate != null ? String(lawyer.hourly_rate) : '')
  }

  async function saveMissingRate(lawyer) {
    const value = rateDraft.trim()
    if (!value || Number(value) <= 0) return
    setRateSaving(true)
    try {
      await updateHourlyRate(lawyer.membership_id, value)
      setRateEditingId(null)
      refreshMissingRates(draft.periodStart, draft.periodEnd)
    } catch (err) {
      setActionError(err.message)
    } finally {
      setRateSaving(false)
    }
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

  function openExport(narrative) {
    setActionError(null)
    setFilenameDraft(defaultFilename(caseTitle, narrative.id))
    setExportTarget(narrative)
  }

  async function handleExport(event) {
    event.preventDefault()
    const filename = filenameDraft.trim()
    if (!filename) return
    setExporting(true)
    setActionError(null)
    try {
      await exportNarrativePdf(caseId, exportTarget.id, filename)
      setExportTarget(null)
      onDocumentAdded?.()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setExporting(false)
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
            <DateInput value={draft.periodStart} onChange={(iso) => setDraft((d) => ({ ...d, periodStart: iso }))} required />
          </FormField>
          <FormField label="עד תאריך">
            <DateInput value={draft.periodEnd} onChange={(iso) => setDraft((d) => ({ ...d, periodEnd: iso }))} required />
          </FormField>
          <FormField label="שפה">
            <select value={draft.language} onChange={(event) => setDraft((d) => ({ ...d, language: event.target.value }))}>
              <option value="he">עברית</option>
              <option value="en">English</option>
            </select>
          </FormField>

          {missingRates.length > 0 && (
            <div className="narrative-rate-warning">
              <div className="narrative-rate-warning-title">
                לעורכי/ות הדין הבאים אין תעריף שעתי מוגדר (או תעריף אפס) בתקופה זו — שעותיהם ייכללו בסה"כ השעות אך לא
                יתומחרו בשכר הטרחה:
              </div>
              <ul className="narrative-rate-warning-list">
                {missingRates.map((lawyer) => (
                  <li key={lawyer.membership_id} className="narrative-rate-warning-row">
                    <span>
                      {lawyer.name}
                      {!lawyer.active && ' (הוסר/ה מהצוות)'}
                    </span>
                    {rateEditingId === lawyer.membership_id ? (
                      <span className="member-rate-edit">
                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          className="member-rate-input"
                          value={rateDraft}
                          onChange={(event) => setRateDraft(event.target.value)}
                          autoFocus
                        />
                        <button type="button" className="member-action" onClick={() => saveMissingRate(lawyer)} disabled={rateSaving}>
                          {rateSaving ? 'שומר…' : 'שמירה'}
                        </button>
                        <button type="button" className="member-action" onClick={() => setRateEditingId(null)}>
                          ביטול
                        </button>
                      </span>
                    ) : (
                      <button type="button" className="member-rate-display" onClick={() => startRateEdit(lawyer)}>
                        הגדרת תעריף
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

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

      {exportTarget && (
        <form className="work-hours-form" onSubmit={handleExport}>
          <FormField label="שם הקובץ המיוצא">
            <input
              type="text"
              value={filenameDraft}
              onChange={(event) => setFilenameDraft(event.target.value)}
              required
            />
          </FormField>
          {actionError && <FormError message={actionError} />}
          <div className="work-hours-form-actions">
            <button type="submit" className="secondary-button" disabled={exporting}>
              {exporting ? 'מייצא…' : 'ייצוא ל-PDF'}
            </button>
            <button type="button" className="detail-title-cancel" onClick={() => setExportTarget(null)}>
              ביטול
            </button>
          </div>
        </form>
      )}

      {!formOpen && !exportTarget && actionError && <FormError message={actionError} />}

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
              onClick={() => openExport(current)}
            >
              ייצוא ל-PDF (מסמך פנימי)
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
                        <button type="button" className="documents-action" onClick={() => openExport(narrative)}>
                          ייצוא ל-PDF
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
