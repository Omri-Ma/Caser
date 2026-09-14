import { useEffect, useState } from 'react'
import PlatformAppShell from '../components/PlatformAppShell'
import DataTable from '../components/DataTable'
import { listPlatformAuditLog } from '../api/platform'
import { formatDateTime } from '../utils/format'

const ACTION_LABELS = {
  tenant_suspended: 'השעיית משרד',
  tenant_reactivated: 'הפעלת משרד מחדש',
}

function actionLabel(action) {
  return ACTION_LABELS[action] || action
}

// super_admin's own action trail (CLAUDE.md's PlatformAuditLogs note) — a
// separate, parallel log from the tenant-scoped AuditLogPage every
// office_manager sees. Only ever grows from suspend/reactivate actions,
// the one action powerful enough to lock an entire firm out unilaterally.
export default function PlatformAuditLogPage() {
  const [page, setPage] = useState(1)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    listPlatformAuditLog({ page })
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page])

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
      key: 'target_tenant_name',
      label: 'משרד',
      render: (row) => <span className="case-muted">{row.target_tenant_name}</span>,
    },
  ]

  return (
    <PlatformAppShell>
      <h1 className="page-title platform-page-title">יומן פעולות פלטפורמה</h1>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && (
        <div className="card cases-table-card">
          <DataTable
            columns={columns}
            rows={result?.items}
            loading={loading}
            emptyMessage="אין עדיין פעולות רשומות ביומן הפלטפורמה."
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
    </PlatformAppShell>
  )
}
