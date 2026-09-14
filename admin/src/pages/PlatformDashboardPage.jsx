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
import { getPlatformEarnings, getPlatformStats, getStorageOverview, getTenantGrowth } from '../api/platform'
import { formatFileSize, formatMonthLabel } from '../utils/format'
import './PlatformDashboardPage.css'

const PLAN_LABELS = { free: 'Free', pro: 'Pro', enterprise: 'Enterprise' }
const PLAN_COLORS = { free: 'var(--color-gray)', pro: 'var(--color-info)', enterprise: 'var(--color-primary)' }

// super_admin's data/graphs overview (CLAUDE.md's Roles: firm-level/
// aggregate data only) — platform-wide stats, plan distribution, tenant
// growth and earnings trends, per-tenant storage overview. The cross-tenant
// firm list itself (with suspend/reactivate) lives on its own page
// (PlatformFirmsPage) — split out so this screen stays purely the data/
// graphs view, kept separate from both the firm list and the users view.
export default function PlatformDashboardPage() {
  const [stats, setStats] = useState(null)
  const [statsError, setStatsError] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  const [growth, setGrowth] = useState(null)
  const [earnings, setEarnings] = useState(null)
  const [storage, setStorage] = useState(null)
  const [chartsError, setChartsError] = useState(null)
  const [storageSearch, setStorageSearch] = useState('')

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

  useEffect(() => {
    loadStats()
    loadCharts()
  }, [loadStats, loadCharts])

  const growthChartData = growth?.map((point) => ({ label: formatMonthLabel(point.month), new_tenants: point.new_tenants }))
  const earningsChartData = earnings?.trend.map((point) => ({ label: formatMonthLabel(point.month), earnings: point.earnings_ils }))
  const planPieData = stats?.plan_distribution
    .filter((entry) => entry.tenant_count > 0)
    .map((entry) => ({ name: PLAN_LABELS[entry.plan] || entry.plan, value: entry.tenant_count, plan: entry.plan }))

  // Search filters the storage-by-firm list client-side — storage-overview
  // isn't paginated (bounded by tenant count, per the backend's own note),
  // so this just narrows what's already fetched in full, the same reasoning
  // that lets the list drop its old top-6 cap now that a firm can be found
  // by name/subdomain directly instead.
  const term = storageSearch.trim().toLowerCase()
  const storageEntries = (storage || [])
    .filter((entry) => !term || entry.name.toLowerCase().includes(term) || entry.subdomain.toLowerCase().includes(term))
    .slice()
    .sort((a, b) => {
      const pctOf = (entry) => (entry.plan === 'enterprise' || entry.storage_limit_bytes <= 0 ? 0 : entry.storage_used_bytes / entry.storage_limit_bytes)
      return pctOf(b) - pctOf(a)
    })

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
            <div className="platform-card-title-row">
              <div className="platform-card-title">אחסון לפי משרד</div>
              <input
                type="text"
                className="cases-search-input platform-storage-search"
                placeholder="חיפוש משרד…"
                value={storageSearch}
                onChange={(event) => setStorageSearch(event.target.value)}
              />
            </div>
            {!storage || storage.length === 0 ? (
              <div className="dashboard-chart-empty">אין עדיין משרדים להצגה.</div>
            ) : storageEntries.length === 0 ? (
              <div className="dashboard-chart-empty">לא נמצאו משרדים התואמים את החיפוש.</div>
            ) : (
              <ul className="platform-storage-list">
                {storageEntries.map((entry) => {
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
