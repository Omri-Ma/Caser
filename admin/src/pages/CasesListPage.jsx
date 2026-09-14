import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import DataTable from '../components/DataTable'
import NewCaseModal from '../components/NewCaseModal'
import { listCases } from '../api/cases'
import { CASE_STATUSES, caseStatusLabel, caseStatusStyle } from '../utils/caseStatus'
import { PRACTICE_AREAS, practiceAreaLabel } from '../utils/practiceArea'
import { formatDate } from '../utils/format'
import './CasesListPage.css'

const STATUS_TABS = [{ key: 'all', label: 'כל התיקים' }, ...CASE_STATUSES.map((s) => ({ key: s, label: caseStatusLabel(s) }))]

export default function CasesListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('all')
  const [practiceAreaFilter, setPracticeAreaFilter] = useState('all')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newCaseOpen, setNewCaseOpen] = useState(false)

  // Debounce the search box so every keystroke doesn't fire a request —
  // the actual filtering still happens server-side once `search` settles.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    setLoading(true)
    setError(null)
    listCases({
      page,
      status: statusFilter === 'all' ? undefined : statusFilter,
      search: search || undefined,
      practiceArea: practiceAreaFilter === 'all' ? undefined : practiceAreaFilter,
    })
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page, statusFilter, practiceAreaFilter, search])

  function selectStatus(status) {
    setStatusFilter(status)
    setPage(1)
  }

  function selectPracticeArea(area) {
    setPracticeAreaFilter(area)
    setPage(1)
  }

  function handleCreated(newCase) {
    setNewCaseOpen(false)
    navigate(`/cases/${newCase.id}`)
  }

  const totalPages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1

  const columns = [
    {
      key: 'title',
      label: 'תיק',
      render: (row) => (
        <div className="case-title-cell">
          <div className="case-id-badge" aria-hidden="true">
            #{row.id}
          </div>
          <div className="case-title-text">{row.title}</div>
        </div>
      ),
    },
    {
      key: 'created_at',
      label: 'נפתח בתאריך',
      render: (row) => <span className="case-muted">{formatDate(row.created_at)}</span>,
    },
    {
      key: 'tags',
      label: 'תחומים',
      render: (row) => (
        <div className="case-tags-cell">
          {(row.practice_areas ?? []).length === 0 ? (
            <span className="case-muted">—</span>
          ) : (
            row.practice_areas.map((area) => (
              <span key={area} className="chip case-tag-chip">
                {practiceAreaLabel(area)}
              </span>
            ))
          )}
        </div>
      ),
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
      <div className="cases-header">
        <h1 className="page-title">תיקים</h1>
        <button type="button" className="primary-button cases-new-button" onClick={() => setNewCaseOpen(true)}>
          + תיק חדש
        </button>
      </div>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && (
        <div className="card cases-table-card">
          <div className="cases-toolbar">
            <div className="cases-tabs">
              {STATUS_TABS.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={`cases-tab${statusFilter === tab.key ? ' active' : ''}`}
                  onClick={() => selectStatus(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <select
              className="cases-practice-area-select"
              value={practiceAreaFilter}
              onChange={(event) => selectPracticeArea(event.target.value)}
            >
              <option value="all">כל התחומים</option>
              {PRACTICE_AREAS.map((area) => (
                <option key={area} value={area}>
                  {practiceAreaLabel(area)}
                </option>
              ))}
            </select>
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
            rows={result?.items}
            loading={loading}
            emptyMessage={
              search || statusFilter !== 'all' || practiceAreaFilter !== 'all'
                ? 'לא נמצאו תיקים התואמים את החיפוש או הסינון.'
                : 'עדיין אין תיקים במשרד. צרו תיק חדש כדי להתחיל.'
            }
            onRowClick={(row) => navigate(`/cases/${row.id}`)}
          />

          {!loading && result && result.total > 0 && (
            <div className="cases-pagination">
              <button type="button" className="secondary-button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                הקודם
              </button>
              <span className="cases-pagination-info">
                עמוד {result.page} מתוך {totalPages} · {result.total} תיקים
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

      <NewCaseModal open={newCaseOpen} onClose={() => setNewCaseOpen(false)} onCreated={handleCreated} />
    </AppShell>
  )
}
