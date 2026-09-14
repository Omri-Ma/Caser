import { useCallback, useEffect, useState } from 'react'
import { listNarratives } from '../api/narratives'
import { formatDate } from '../utils/format'
import './NarrativesPanel.css'

const CURRENCY_TEXT = { he: 'ש"ח', en: 'ILS' }

function feeLabel(narrative) {
  const currency = CURRENCY_TEXT[narrative.language] ?? CURRENCY_TEXT.he
  return `${Number(narrative.total_fee).toFixed(2)} ${currency}`
}

// Lawyer-only, read-only view (CLAUDE.md's Narratives note: generation and
// PDF export are office_manager-only now, handled in admin/'s CaseDetailPage
// instead) — an assigned lawyer can still see what will be billed for their
// own logged hours, just not create or export a narrative. Narratives are
// always firm-internal (never rendered/mounted for a client either way).
export default function NarrativesPanel({ caseId }) {
  const [narratives, setNarratives] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showHistory, setShowHistory] = useState(false)

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

  const current = narratives && narratives.length > 0 ? narratives[0] : null
  const history = narratives && narratives.length > 1 ? narratives.slice(1) : []

  return (
    <div className="card detail-card detail-narratives-card">
      <div className="documents-toolbar">
        <div className="detail-card-title">נרטיב תיק</div>
      </div>

      {loading && <div className="detail-state">טוען נרטיב…</div>}
      {!loading && error && <div className="detail-state detail-state-error">{error}</div>}
      {!loading && !error && !current && <div className="detail-state">טרם נוצר נרטיב לתיק זה.</div>}

      {!loading && !error && current && (
        <>
          <div className="narrative-current">
            <div className="narrative-meta">
              נוצר בתאריך {formatDate(current.created_at)} · תקופה {formatDate(current.period_start)}–
              {formatDate(current.period_end)} · {Number(current.total_hours).toFixed(2)} שעות · {feeLabel(current)}
            </div>
            <div className="narrative-text">{current.generated_text}</div>
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
