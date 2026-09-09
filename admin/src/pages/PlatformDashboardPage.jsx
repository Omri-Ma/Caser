import { useCallback, useEffect, useState } from 'react'
import PlatformAppShell from '../components/PlatformAppShell'
import DataTable from '../components/DataTable'
import { FormError } from '../components/Form'
import { getPlatformStats, listTenants, reactivateTenant, suspendTenant } from '../api/platform'
import './PlatformDashboardPage.css'

const PLAN_LABELS = { free: 'Free', pro: 'Pro', enterprise: 'Enterprise' }

// super_admin's one and only screen (CLAUDE.md's Roles: firm-level/
// aggregate data only) — platform-wide stats overview plus the
// cross-tenant firm list with suspend/reactivate. Both come from
// admin_api's /platform/* routes, which are the one place a query
// legitimately spans every tenant.
export default function PlatformDashboardPage() {
  const [stats, setStats] = useState(null)
  const [statsError, setStatsError] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const [page, setPage] = useState(1)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actioningId, setActioningId] = useState(null)
  const [actionError, setActionError] = useState(null)

  const loadStats = useCallback(() => {
    setStatsLoading(true)
    setStatsError(null)
    getPlatformStats()
      .then(setStats)
      .catch((err) => setStatsError(err.message))
      .finally(() => setStatsLoading(false))
  }, [])

  const loadTenants = useCallback(() => {
    setLoading(true)
    setError(null)
    listTenants({ page })
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  useEffect(() => {
    loadTenants()
  }, [loadTenants])

  async function handleToggle(tenant) {
    const suspending = tenant.active
    const message = suspending
      ? `להשעות את ${tenant.name}? כל אנשי הצוות והלקוחות במשרד ייחסמו מיידית מגישה למערכת.`
      : `להפעיל מחדש את ${tenant.name}?`
    if (!window.confirm(message)) return

    setActioningId(tenant.id)
    setActionError(null)
    try {
      if (suspending) {
        await suspendTenant(tenant.id)
      } else {
        await reactivateTenant(tenant.id)
      }
      loadTenants()
      loadStats()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  const totalPages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1

  const columns = [
    {
      key: 'name',
      label: 'משרד',
      render: (row) => (
        <div>
          <div className="member-name">{row.name}</div>
          <div className="member-email">{row.subdomain}.lvh.me</div>
        </div>
      ),
    },
    {
      key: 'plan',
      label: 'תוכנית',
      render: (row) => <span className="chip member-role-chip">{PLAN_LABELS[row.plan] || row.plan}</span>,
    },
    {
      key: 'lawyer_count',
      label: 'עורכי דין',
      render: (row) => <span dir="ltr">{row.lawyer_count}</span>,
    },
    {
      key: 'case_count',
      label: 'תיקים',
      render: (row) => <span dir="ltr">{row.case_count}</span>,
    },
    {
      key: 'active',
      label: 'סטטוס',
      render: (row) => (
        <span className={`chip ${row.active ? 'member-status-active' : 'tenant-status-suspended'}`}>
          {row.active ? 'פעיל' : 'מושעה'}
        </span>
      ),
    },
    {
      key: 'actions',
      label: '',
      render: (row) => (
        <button
          type="button"
          className={row.active ? 'member-action member-action-danger' : 'member-action'}
          onClick={() => handleToggle(row)}
          disabled={actioningId === row.id}
        >
          {row.active ? 'השעיה' : 'הפעלה מחדש'}
        </button>
      ),
    },
  ]

  return (
    <PlatformAppShell>
      <h1 className="page-title platform-page-title">לוח בקרה</h1>

      {statsError && <div className="cases-state cases-state-error">{statsError}</div>}
      {!statsError && (
        <div className="platform-stats-grid">
          <StatCard label="משרדים" value={stats?.total_tenants} loading={statsLoading} />
          <StatCard label="משרדים פעילים" value={stats?.active_tenants} loading={statsLoading} />
          <StatCard label="עורכי דין (סה״כ)" value={stats?.total_lawyers} loading={statsLoading} />
          <StatCard label="תיקים (סה״כ)" value={stats?.total_cases} loading={statsLoading} />
        </div>
      )}

      <h2 className="platform-tenants-title">משרדים</h2>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && (
        <div className="card cases-table-card">
          <FormError message={actionError} />
          <DataTable
            columns={columns}
            rows={result?.items}
            loading={loading}
            emptyMessage="אין משרדים רשומים במערכת עדיין."
          />

          {!loading && result && result.total > 0 && (
            <div className="cases-pagination">
              <button type="button" className="secondary-button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                הקודם
              </button>
              <span className="cases-pagination-info">
                עמוד {result.page} מתוך {totalPages} · {result.total} משרדים
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

function StatCard({ label, value, loading }) {
  return (
    <div className="card platform-stat-card">
      <div className="platform-stat-value">{loading ? '…' : value}</div>
      <div className="platform-stat-label">{label}</div>
    </div>
  )
}
