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
  // Unfiltered snapshot of this membership's assigned cases — only used to
  // drive the status-tab counts and to tell "no cases assigned at all"
  // apart from "no cases matching the current search/filter". The actual
  // displayed list below is always fetched with search/status applied
  // server-side, never filtered client-side.
  const [allCases, setAllCases] = useState(null)
  const [cases, setCases] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('all')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    listMyCases()
      .then((page) => setAllCases(page.items))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput.trim()), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    setLoading(true)
    setError(null)
    listMyCases({ search: search || undefined, status: statusFilter === 'all' ? undefined : statusFilter })
      .then((page) => setCases(page.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [search, statusFilter])

  const statusCounts = useMemo(() => {
    const counts = { open: 0, in_progress: 0, on_hold: 0, closed: 0 }
    for (const c of allCases ?? []) {
      if (counts[c.status] !== undefined) counts[c.status] += 1
    }
    return counts
  }, [allCases])

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

  const noCasesAtAll = allCases !== null && allCases.length === 0
  const isFiltering = Boolean(search) || statusFilter !== 'all'

  return (
    <AppShell activeKey="cases">
      <h1 className="page-title">התיקים שלי</h1>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && allCases === null && <div className="cases-state">טוען תיקים…</div>}

      {!error && noCasesAtAll && (
        <div className="cases-empty card">
          <div className="cases-empty-title">אין לך תיקים משויכים כרגע</div>
          <div className="cases-empty-sub">כשתשויך לתיק על ידי מנהל המשרד, הוא יופיע כאן.</div>
        </div>
      )}

      {!error && !noCasesAtAll && allCases !== null && (
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
            <div className="cases-toolbar">
              <div className="cases-tabs">
                <button
                  type="button"
                  className={`cases-tab${statusFilter === 'all' ? ' active' : ''}`}
                  onClick={() => setStatusFilter('all')}
                >
                  כל התיקים ({allCases.length})
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
              <input
                type="text"
                className="cases-search-input"
                placeholder="חיפוש לפי שם תיק…"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </div>
            <DataTable
              columns={columns}
              rows={cases}
              loading={loading}
              emptyMessage={isFiltering ? 'לא נמצאו תיקים התואמים את החיפוש או הסינון.' : 'אין תיקים בסטטוס זה.'}
              onRowClick={(row) => navigate(`/cases/${row.id}`)}
            />
          </div>
        </>
      )}
    </AppShell>
  )
}
