import { useCallback, useEffect, useState } from 'react'
import PlatformAppShell from '../components/PlatformAppShell'
import DataTable from '../components/DataTable'
import { FormError } from '../components/Form'
import { listTenants, reactivateTenant, suspendTenant } from '../api/platform'
import './PlatformDashboardPage.css'

const PLAN_LABELS = { free: 'Free', pro: 'Pro', enterprise: 'Enterprise' }

// super_admin's cross-tenant firm list — split out of PlatformDashboardPage
// so the data/graphs overview and the firm list (with its own search bar
// and suspend/reactivate actions) are two separate screens, kept separate
// in turn from the users view (PlatformUsersPage).
export default function PlatformFirmsPage() {
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actioningId, setActioningId] = useState(null)
  const [actionError, setActionError] = useState(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const loadTenants = useCallback(() => {
    setLoading(true)
    setError(null)
    listTenants({ page, search: search || undefined })
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page, search])

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
      <h1 className="page-title platform-page-title">משרדים</h1>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && (
        <div className="card cases-table-card">
          <div className="cases-toolbar">
            <input
              type="text"
              className="cases-search-input"
              placeholder="חיפוש לפי שם משרד או תת-דומיין…"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>

          <FormError message={actionError} />
          <DataTable
            columns={columns}
            rows={result?.items}
            loading={loading}
            emptyMessage={search ? 'לא נמצאו משרדים התואמים את החיפוש.' : 'אין משרדים רשומים במערכת עדיין.'}
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
