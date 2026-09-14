import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import PlatformAppShell from '../components/PlatformAppShell'
import DataTable from '../components/DataTable'
import { FormError } from '../components/Form'
import {
  getPlatformEarnings,
  getPlatformStats,
  getStorageOverview,
  getTenantGrowth,
  listTenants,
  reactivateTenant,
  suspendTenant,
} from '../api/platform'
import { formatFileSize, formatMonthLabel } from '../utils/format'
import './PlatformDashboardPage.css'

const PLAN_LABELS = { free: 'Free', pro: 'Pro', enterprise: 'Enterprise' }
const PLAN_COLORS = { free: 'var(--color-gray)', pro: 'var(--color-info)', enterprise: 'var(--color-primary)' }

// super_admin's dashboard (CLAUDE.md's Roles: firm-level/aggregate data
// only) — platform-wide stats, plan distribution, tenant growth and
// earnings trends, per-tenant storage overview, plus the cross-tenant firm
// list with suspend/reactivate. Everything here comes from admin_api's
// /platform/* routes, the one place a query legitimately spans every tenant.
export default function PlatformDashboardPage() {
  const [stats, setStats] = useState(null)
  const [statsError, setStatsError] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const [growth, setGrowth] = useState(null)
  const [earnings, setEarnings] = useState(null)
  const [storage, setStorage] = useState(null)
  const [chartsError, setChartsError] = useState(null)

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

  const loadCharts = useCallback(() => {
    setChartsError(null)
    Promise.all([getTenantGrowth(), getPlatformEarnings(), getStorageOverview()])
      .then(([growthData, earningsData, storageData]) => {
        setGrowth(growthData)
        setEarnings(earningsData)
        setStorage(storageData)
      })
      .catch((err) => setChartsError(err.message))
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
    loadCharts()
  }, [loadStats, loadCharts])

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
      loadCharts()
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

  const growthChartData = growth?.map((point) => ({ label: formatMonthLabel(point.month), new_tenants: point.new_tenants }))
  const earningsChartData = earnings?.trend.map((point) => ({ label: formatMonthLabel(point.month), earnings: point.earnings_ils }))
  const planPieData = stats?.plan_distribution
    .filter((entry) => entry.tenant_count > 0)
    .map((entry) => ({ name: PLAN_LABELS[entry.plan] || entry.plan, value: entry.tenant_count, plan: entry.plan }))

  return (
    <PlatformAppShell>
      <h1 className="page-title platform-page-title">לוח בקרה</h1>

      {statsError && <div className="cases-state cases-state-error">{statsError}</div>}
      {!statsError && (
        <div className="platform-stats-grid">
          <StatCard label="משרדים" value={stats?.total_tenants} loading={statsLoading} />
          <StatCard label="משרדים פעילים" value={stats?.active_tenants} loading={statsLoading} />
          <StatCard label="עורכי דין (סה״כ)" value={stats?.total_lawyers} loading={statsLoading} />
          <StatCard label="לקוחות (סה״כ)" value={stats?.total_clients} loading={statsLoading} />
          <StatCard label="תיקים (סה״כ)" value={stats?.total_cases} loading={statsLoading} />
          <StatCard
            label="אחסון בשימוש (סה״כ)"
            value={statsLoading ? undefined : formatFileSize(stats?.total_storage_bytes ?? 0)}
            loading={statsLoading}
          />
        </div>
      )}

      {chartsError && <div className="cases-state cases-state-error">{chartsError}</div>}
      {!chartsError && (
        <div className="platform-charts-grid">
          <div className="card platform-card">
            <div className="platform-card-title">התפלגות תוכניות</div>
            {!planPieData || planPieData.length === 0 ? (
              <div className="dashboard-chart-empty">אין עדיין משרדים להצגה.</div>
            ) : (
              <div className="platform-chart">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={planPieData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75}>
                      {planPieData.map((entry) => (
                        <Cell key={entry.plan} fill={PLAN_COLORS[entry.plan] || 'var(--color-gray)'} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: 10, border: '1px solid var(--color-border)', fontSize: 13 }}
                      formatter={(value, name) => [value, name]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="card platform-card">
            <div className="platform-card-title">משרדים חדשים לפי חודש</div>
            {!growthChartData || growthChartData.every((p) => p.new_tenants === 0) ? (
              <div className="dashboard-chart-empty">אין עדיין משרדים חדשים להצגה במגמה.</div>
            ) : (
              <div className="platform-chart">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={growthChartData} margin={{ top: 8, left: 0, right: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                    <XAxis dataKey="label" stroke="var(--color-text-muted)" fontSize={12} tickLine={false} />
                    <YAxis allowDecimals={false} stroke="var(--color-text-muted)" fontSize={12} tickLine={false} width={28} />
                    <Tooltip
                      contentStyle={{ borderRadius: 10, border: '1px solid var(--color-border)', fontSize: 13 }}
                      formatter={(value) => [value, 'משרדים חדשים']}
                    />
                    <Bar dataKey="new_tenants" fill="var(--color-primary)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="card platform-card">
            <div className="platform-card-title">הכנסות פלטפורמה</div>
            <div className="platform-earnings-figure">
              {earnings ? `${earnings.current_month_earnings_ils.toLocaleString()} ₪` : '…'}
            </div>
            {!earningsChartData || earningsChartData.every((p) => p.earnings === 0) ? (
              <div className="dashboard-chart-empty">אין עדיין נתוני מנוי להצגה במגמה.</div>
            ) : (
              <div className="platform-chart">
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={earningsChartData} margin={{ top: 8, left: 0, right: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                    <XAxis dataKey="label" stroke="var(--color-text-muted)" fontSize={12} tickLine={false} />
                    <YAxis stroke="var(--color-text-muted)" fontSize={12} tickLine={false} width={40} />
                    <Tooltip
                      contentStyle={{ borderRadius: 10, border: '1px solid var(--color-border)', fontSize: 13 }}
                      formatter={(value) => [`${value.toLocaleString()} ₪`, 'הכנסות']}
                    />
                    <Line type="monotone" dataKey="earnings" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="card platform-card">
            <div className="platform-card-title">אחסון לפי משרד</div>
            {!storage || storage.length === 0 ? (
              <div className="dashboard-chart-empty">אין עדיין משרדים להצגה.</div>
            ) : (
              <ul className="platform-storage-list">
                {storage
                  .slice()
                  .sort((a, b) => b.storage_used_bytes / b.storage_limit_bytes - a.storage_used_bytes / a.storage_limit_bytes)
                  .slice(0, 6)
                  .map((entry) => {
                    const pct = entry.storage_limit_bytes > 0 ? (entry.storage_used_bytes / entry.storage_limit_bytes) * 100 : 0
                    const over = pct >= 90
                    return (
                      <li key={entry.tenant_id} className="platform-storage-row">
                        <div className="platform-storage-row-header">
                          <span className="platform-storage-name">{entry.name}</span>
                          <span dir="ltr" className={`platform-storage-pct${over ? ' over' : ''}`}>
                            {formatFileSize(entry.storage_used_bytes)} / {formatFileSize(entry.storage_limit_bytes)}
                          </span>
                        </div>
                        <div className="usage-bar-track">
                          <div className={`usage-bar-fill${over ? ' over' : ''}`} style={{ width: `${Math.min(100, pct)}%` }} />
                        </div>
                      </li>
                    )
                  })}
              </ul>
            )}
          </div>
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
