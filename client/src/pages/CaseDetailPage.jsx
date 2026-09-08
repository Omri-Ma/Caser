import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
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

export default function CaseDetailPage() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
            <DocumentsSection showInternal={canSeeInternalFolder()} />
            <WorkHoursSection />
          </div>
        </>
      )}
    </AppShell>
  )
}

function DocumentsSection({ showInternal }) {
  const [tab, setTab] = useState('client')

  return (
    <div className="card detail-card">
      <div className="detail-tabs">
        <button
          type="button"
          className={`detail-tab${tab === 'client' ? ' active' : ''}`}
          onClick={() => setTab('client')}
        >
          מסמכי לקוח
        </button>
        {showInternal && (
          <button
            type="button"
            className={`detail-tab${tab === 'internal' ? ' active' : ''}`}
            onClick={() => setTab('internal')}
          >
            מסמכים פנימיים
          </button>
        )}
      </div>
      <div className="detail-placeholder">
        <div className="detail-placeholder-title">ניהול מסמכים בקרוב</div>
        <div className="detail-placeholder-sub">
          העלאה, צפייה והורדה של מסמכי התיק תהיה זמינה כאן בשלב הבא של הפיתוח.
        </div>
      </div>
    </div>
  )
}

function WorkHoursSection() {
  return (
    <div className="card detail-card detail-hours-card">
      <div className="detail-card-title">שעות עבודה</div>
      <div className="detail-placeholder">
        <div className="detail-placeholder-title">מעקב שעות בקרוב</div>
        <div className="detail-placeholder-sub">סיכום שעות העבודה שנרשמו בתיק יופיע כאן בשלב הבא של הפיתוח.</div>
      </div>
    </div>
  )
}
