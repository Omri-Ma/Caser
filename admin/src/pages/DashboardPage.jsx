import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import AppShell from '../components/AppShell'
import { FormError } from '../components/Form'
import { exportDashboardData, getDashboardStats } from '../api/dashboard'
import { formatFileSize, formatMonthLabel } from '../utils/format'
import './DashboardPage.css'

const PLAN_LABELS = { free: 'Free', pro: 'Pro', enterprise: 'Enterprise' }

function triggerBrowserDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// office_manager's own per-tenant dashboard — real numbers from
// /dashboard/stats (admin_api), scoped to the current tenant only. Not to
// be confused with super_admin's cross-tenant /platform dashboard
// (PlatformDashboardPage), a deliberately separate screen and code path.
export default function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [exporting, setExporting] = useState(null)
  const [exportError, setExportError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getDashboardStats()
      .then(setStats)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleExport(resource) {
    setExporting(resource)
    setExportError(null)
    try {
      const { blob, filename } = await exportDashboardData(resource)
      triggerBrowserDownload(blob, filename)
    } catch (err) {
      setExportError(err.message)
    } finally {
      setExporting(null)
    }
  }

  const isEmpty = stats && stats.total_case_count === 0 && stats.lawyer_count === 0 && stats.client_count === 0
  const chartData = stats?.monthly_case_activity.map((point) => ({
    label: formatMonthLabel(point.month),
    new_cases: point.new_cases,
  }))
  const hoursChartData = stats?.monthly_billable_hours.map((point) => ({
    label: formatMonthLabel(point.month),
    total_hours: point.total_hours,
  }))
  const hasBillableHours = stats?.monthly_billable_hours.some((point) => point.total_hours > 0)

  return (
    <AppShell activeKey="dashboard">
      <h1 className="page-title">לוח בקרה</h1>

      {loading && <div className="cases-state">טוען נתוני משרד…</div>}
      {!loading && error && <div className="cases-state cases-state-error">{error}</div>}

      {!loading && !error && isEmpty && (
        <div className="card dashboard-empty-note">
          המשרד עדיין לא צבר פעילות (אין תיקים, עורכי דין או לקוחות) — הנתונים כאן יתעדכנו עם הפעילות הראשונה.
        </div>
      )}

      {!loading && !error && stats && (
        <>
          <div className="dashboard-stats-grid">
            <StatCard label="תיקים פעילים" value={stats.active_case_count} />
            <StatCard label="תיקים (סה״כ)" value={stats.total_case_count} />
            <StatCard label="עורכי דין" value={stats.lawyer_count} />
            <StatCard label="לקוחות" value={stats.client_count} />
          </div>

          <div className="card dashboard-card">
            <div className="dashboard-card-title">
              אחסון בשימוש · תוכנית {PLAN_LABELS[stats.plan] || stats.plan}
            </div>
            <StorageBar used={stats.storage_used_bytes} limit={stats.storage_limit_bytes} />
          </div>

          <div className="card dashboard-card">
            <div className="dashboard-card-title">תיקים חדשים לפי חודש</div>
            {stats.total_case_count === 0 ? (
              <div className="dashboard-chart-empty">אין עדיין תיקים להצגה במגמה.</div>
            ) : (
              <div className="dashboard-chart">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={chartData} margin={{ top: 8, left: 0, right: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                    <XAxis dataKey="label" stroke="var(--color-text-muted)" fontSize={12} tickLine={false} />
                    <YAxis allowDecimals={false} stroke="var(--color-text-muted)" fontSize={12} tickLine={false} width={28} />
                    <Tooltip
                      contentStyle={{ borderRadius: 10, border: '1px solid var(--color-border)', fontSize: 13 }}
                      formatter={(value) => [value, 'תיקים חדשים']}
                    />
                    <Bar dataKey="new_cases" fill="var(--color-primary)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="card dashboard-card">
            <div className="dashboard-card-title">שעות חיוב לפי חודש</div>
            {!hasBillableHours ? (
              <div className="dashboard-chart-empty">אין עדיין שעות עבודה רשומות להצגה במגמה.</div>
            ) : (
              <div className="dashboard-chart">
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={hoursChartData} margin={{ top: 8, left: 0, right: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                    <XAxis dataKey="label" stroke="var(--color-text-muted)" fontSize={12} tickLine={false} />
                    <YAxis stroke="var(--color-text-muted)" fontSize={12} tickLine={false} width={28} />
                    <Tooltip
                      contentStyle={{ borderRadius: 10, border: '1px solid var(--color-border)', fontSize: 13 }}
                      formatter={(value) => [value, 'שעות חיוב']}
                    />
                    <Line
                      type="monotone"
                      dataKey="total_hours"
                      stroke="var(--color-primary)"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="card dashboard-card">
            <div className="dashboard-card-title">ייצוא נתונים</div>
            <FormError message={exportError} />
            <div className="dashboard-export-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => handleExport('cases')}
                disabled={exporting !== null}
              >
                {exporting === 'cases' ? 'מייצא…' : 'ייצוא תיקים (CSV)'}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => handleExport('members')}
                disabled={exporting !== null}
              >
                {exporting === 'members' ? 'מייצא…' : 'ייצוא אנשי צוות (CSV)'}
              </button>
            </div>
          </div>
        </>
      )}
    </AppShell>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="card dashboard-stat-card">
      <div className="dashboard-stat-value">{value}</div>
      <div className="dashboard-stat-label">{label}</div>
    </div>
  )
}

function StorageBar({ used, limit }) {
  const percent = limit > 0 ? Math.min(100, (used / limit) * 100) : 0
  const over = used > limit
  return (
    <div className="usage-bar">
      <div className="usage-bar-header">
        <span>אחסון</span>
        <span dir="ltr" className={over ? 'usage-bar-over' : ''}>
          {formatFileSize(used)} / {formatFileSize(limit)}
        </span>
      </div>
      <div className="usage-bar-track">
        <div className={`usage-bar-fill${over ? ' over' : ''}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}
