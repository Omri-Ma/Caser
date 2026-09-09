import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import DocumentsPanel from '../components/DocumentsPanel'
import NarrativesPanel from '../components/NarrativesPanel'
import WorkHoursPanel from '../components/WorkHoursPanel'
import { getMyCase } from '../api/cases'
import { getStoredRole } from '../api/session'
import { caseStatusLabel, caseStatusStyle } from '../utils/caseStatus'
import { formatDate } from '../utils/format'
import './CaseDetailPage.css'

// Client can only ever see the client-visible folder (CLAUDE.md's Documents
// rules); lawyer/office_manager can see both. Falls back to the more
// restrictive view if role isn't known for some reason (e.g. direct
// navigation without a stored session role) — this is a display choice
// only, not a security boundary, that's enforced server-side.
function canSeeInternalFolder() {
  return getStoredRole() === 'lawyer'
}

// WorkLogs are never client-visible at all (CLAUDE.md) — the panel isn't
// just hidden by CSS, it's not rendered/mounted for a client, so it never
// issues a request the server would 403 anyway.
function canSeeWorkHours() {
  return getStoredRole() === 'lawyer'
}

// Narratives are always firm-internal too (CLAUDE.md) — same reasoning and
// same not-rendered-at-all treatment as WorkHoursPanel.
function canSeeNarratives() {
  return getStoredRole() === 'lawyer'
}

export default function CaseDetailPage() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [documentsRefreshSignal, setDocumentsRefreshSignal] = useState(0)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getMyCase(caseId)
      .then(setCaseData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [caseId])

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
            <h1 className="detail-title">{caseData.title}</h1>
            <span className="chip" style={caseStatusStyle(caseData.status)}>
              {caseStatusLabel(caseData.status)}
            </span>
            <span className="chip detail-id-chip">מס׳ תיק #{caseData.id}</span>
            <div className="detail-header-spacer" />
            <div className="detail-opened">נפתח בתאריך {formatDate(caseData.created_at)}</div>
          </div>

          <div className="detail-columns">
            <DocumentsPanel
              caseId={caseId}
              role={getStoredRole()}
              showInternalTab={canSeeInternalFolder()}
              caseClosed={caseData.status === 'closed'}
              refreshSignal={documentsRefreshSignal}
            />
            {canSeeWorkHours() && <WorkHoursPanel caseId={caseId} caseClosed={caseData.status === 'closed'} />}
          </div>

          {canSeeNarratives() && (
            <div className="detail-columns">
              <NarrativesPanel caseId={caseId} onDocumentAdded={() => setDocumentsRefreshSignal((n) => n + 1)} />
            </div>
          )}
        </>
      )}
    </AppShell>
  )
}
