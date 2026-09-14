import { useEffect, useState } from 'react'
import PlatformAppShell from '../components/PlatformAppShell'
import DataTable from '../components/DataTable'
import { listPlatformUsers } from '../api/platform'
import { formatDateTime } from '../utils/format'
import './PlatformUsersPage.css'

const ROLE_LABELS = { office_manager: 'מנהל/ת משרד', lawyer: 'עורך/ת דין', client: 'לקוח/ה' }

// super_admin's cross-tenant users view (CLAUDE.md's super_admin note) —
// every Identity platform-wide, their last_login_at, and which firms/roles
// they hold. Still firm-level/account-level data, not case/document content:
// knowing *that* someone is a lawyer at two firms is not the same as seeing
// anything about their casework.
export default function PlatformUsersPage() {
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
    listPlatformUsers({ page, search: search || undefined })
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page, search])

  const totalPages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1

  const columns = [
    {
      key: 'name',
      label: 'שם',
      render: (row) => (
        <div>
          <div className="member-name">{row.name}</div>
          <div className="member-email">{row.email}</div>
        </div>
      ),
    },
    {
      key: 'memberships',
      label: 'משרדים ותפקידים',
      render: (row) => (
        <div className="platform-user-memberships">
          {row.memberships.length === 0 ? (
            <span className="case-muted">—</span>
          ) : (
            row.memberships.map((m) => (
              <span key={m.tenant_id} className="chip member-role-chip">
                {m.tenant_name} · {ROLE_LABELS[m.role] || m.role}
              </span>
            ))
          )}
        </div>
      ),
    },
    {
      key: 'last_login_at',
      label: 'התחברות אחרונה',
      render: (row) => (
        <span className="case-muted">{row.last_login_at ? formatDateTime(row.last_login_at) : 'מעולם לא התחבר/ה'}</span>
      ),
    },
  ]

  return (
    <PlatformAppShell>
      <h1 className="page-title platform-page-title">אנשי צוות ולקוחות</h1>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && (
        <div className="card cases-table-card">
          <div className="cases-toolbar">
            <input
              type="text"
              className="cases-search-input"
              placeholder="חיפוש לפי שם או אימייל…"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>

          <DataTable
            columns={columns}
            rows={result?.items}
            loading={loading}
            emptyMessage={search ? 'לא נמצאו משתמשים התואמים את החיפוש.' : 'אין עדיין משתמשים במערכת.'}
          />

          {!loading && result && result.total > 0 && (
            <div className="cases-pagination">
              <button type="button" className="secondary-button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                הקודם
              </button>
              <span className="cases-pagination-info">
                עמוד {result.page} מתוך {totalPages} · {result.total} משתמשים
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
