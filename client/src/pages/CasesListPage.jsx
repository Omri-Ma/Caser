import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import DataTable from '../components/DataTable'
import { listMyCases } from '../api/cases'
import { CASE_STATUSES, caseStatusLabel, caseStatusStyle } from '../utils/caseStatus'
import { avatarInitials, avatarTone, formatDate } from '../utils/format'
import './CasesListPage.css'

export default function CasesListPage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('all')

  useEffect(() => {
    listMyCases()
      .then((page) => setCases(page.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const statusCounts = useMemo(() => {
    const counts = { open: 0, in_progress: 0, on_hold: 0, closed: 0 }
    for (const c of cases ?? []) {
      if (counts[c.status] !== undefined) counts[c.status] += 1
    }
    return counts
  }, [cases])

  const filteredCases = useMemo(() => {
    if (!cases) return []
    if (statusFilter === 'all') return cases
    return cases.filter((c) => c.status === statusFilter)
  }, [cases, statusFilter])

  const columns = [
    {
      key: 'title',
      label: 'תיק',
      render: (row, index) => (
        <div className="case-title-cell">
          <div className="case-avatar" style={avatarTone(index)}>
            {avatarInitials(row.title)}
          </div>
          <div>
            <div className="case-title-text">{row.title}</div>
            <div className="case-title-sub">מס׳ תיק #{row.id}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'created_at',
      label: 'נפתח בתאריך',
      render: (row) => <span className="case-muted">{formatDate(row.created_at)}</span>,
    },
    {
      key: 'status',
      label: 'סטטוס',
      render: (row) => (
        <span className="chip" style={caseStatusStyle(row.status)}>
          {caseStatusLabel(row.status)}
        </span>
      ),
    },
  ]

  return (
    <AppShell activeKey="cases">
      <h1 className="page-title">התיקים שלי</h1>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && loading && <div className="cases-state">טוען תיקים…</div>}

      {!error && !loading && cases && cases.length === 0 && (
        <div className="cases-empty card">
          <div className="cases-empty-title">אין לך תיקים משויכים כרגע</div>
          <div className="cases-empty-sub">כשתשויך לתיק על ידי מנהל המשרד, הוא יופיע כאן.</div>
        </div>
      )}

      {!error && !loading && cases && cases.length > 0 && (
        <>
          <div className="stat-row">
            {CASE_STATUSES.map((status) => (
              <div className="card stat-card" key={status}>
                <div className="stat-label">{caseStatusLabel(status)}</div>
                <div className="stat-value">{statusCounts[status]}</div>
              </div>
            ))}
          </div>

          <div className="card cases-table-card">
            <div className="cases-tabs">
              <button
                type="button"
                className={`cases-tab${statusFilter === 'all' ? ' active' : ''}`}
                onClick={() => setStatusFilter('all')}
              >
                כל התיקים ({cases.length})
              </button>
              {CASE_STATUSES.map((status) => (
                <button
                  key={status}
                  type="button"
                  className={`cases-tab${statusFilter === status ? ' active' : ''}`}
                  onClick={() => setStatusFilter(status)}
                >
                  {caseStatusLabel(status)} ({statusCounts[status]})
                </button>
              ))}
            </div>
            <DataTable
              columns={columns}
              rows={filteredCases}
              emptyMessage="אין תיקים בסטטוס זה."
              onRowClick={(row) => navigate(`/cases/${row.id}`)}
            />
          </div>
        </>
      )}
    </AppShell>
  )
}
