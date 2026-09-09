import { useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import DataTable from '../components/DataTable'
import { listAuditLog } from '../api/audit_log'
import { formatDateTime } from '../utils/format'

const ACTION_LABELS = {
  document_uploaded: 'העלאת מסמך',
  document_archived: 'העברת מסמך לארכיון',
  document_restored: 'שחזור מסמך מהארכיון',
  document_permanently_deleted: 'מחיקת מסמך לצמיתות',
  work_log_edited: 'עריכת רישום שעות',
  work_log_deleted: 'מחיקת רישום שעות',
  work_log_excel_imported: 'ייבוא שעות מאקסל',
  member_deactivated: 'הסרת איש צוות',
  member_password_reset: 'איפוס סיסמה לאיש צוות',
  narrative_pdf_exported: 'ייצוא PDF של נרטיב',
}

const ACTION_TABS = [{ key: 'all', label: 'הכול' }, ...Object.entries(ACTION_LABELS).map(([key, label]) => ({ key, label }))]

function actionLabel(action) {
  return ACTION_LABELS[action] || action
}

// Read-only browsing of this tenant's AuditLog (CLAUDE.md's Phase 3 item 4)
// — office_manager only, no write path here. Entries are produced by the
// actions that already write them elsewhere (documents, work logs, members,
// narratives); this screen just lists who did what, to what, and when.
export default function AuditLogPage() {
  const [page, setPage] = useState(1)
  const [actionFilter, setActionFilter] = useState('all')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    listAuditLog({ page, action: actionFilter === 'all' ? undefined : actionFilter })
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page, actionFilter])

  function selectAction(action) {
    setActionFilter(action)
    setPage(1)
  }

  const totalPages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1

  const columns = [
    {
      key: 'timestamp',
      label: 'מתי',
      render: (row) => <span className="case-muted">{formatDateTime(row.timestamp)}</span>,
    },
    {
      key: 'actor',
      label: 'מי',
      render: (row) => (
        <div>
          <div className="member-name">{row.actor_name}</div>
          <div className="member-email">{row.actor_email}</div>
        </div>
      ),
    },
    {
      key: 'action',
      label: 'פעולה',
      render: (row) => <span className="chip member-role-chip">{actionLabel(row.action)}</span>,
    },
    {
      key: 'target',
      label: 'יעד',
      render: (row) => <span className="case-muted">{row.target}</span>,
    },
  ]

  return (
    <AppShell activeKey="audit-log">
      <h1 className="page-title">יומן פעולות</h1>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && (
        <div className="card cases-table-card">
          <div className="cases-tabs">
            {ACTION_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`cases-tab${actionFilter === tab.key ? ' active' : ''}`}
                onClick={() => selectAction(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <DataTable
            columns={columns}
            rows={result?.items}
            loading={loading}
            emptyMessage={actionFilter === 'all' ? 'אין עדיין פעולות רשומות ביומן.' : 'אין פעולות מסוג זה ביומן.'}
          />

          {!loading && result && result.total > 0 && (
            <div className="cases-pagination">
              <button type="button" className="secondary-button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                הקודם
              </button>
              <span className="cases-pagination-info">
                עמוד {result.page} מתוך {totalPages} · {result.total} פעולות
              </span>
              <button
                type="button"
                className="secondary-button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                הבא
              </button>
            </div>
          )}
        </div>
      )}
    </AppShell>
  )
}
