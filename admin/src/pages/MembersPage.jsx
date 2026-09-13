import { useCallback, useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import DataTable from '../components/DataTable'
import AddMemberModal from '../components/AddMemberModal'
import { FormError } from '../components/Form'
import { deactivateMember, listMembers } from '../api/members'
import { me } from '../api/auth'
import './MembersPage.css'

const ROLE_TABS = [
  { key: 'all', label: 'הכול' },
  { key: 'lawyer', label: 'עורכי דין' },
  { key: 'client', label: 'לקוחות' },
  { key: 'office_manager', label: 'מנהלי משרד' },
]

const ROLE_LABELS = {
  lawyer: 'עורך/ת דין',
  client: 'לקוח/ה',
  office_manager: 'מנהל/ת משרד',
}

export default function MembersPage() {
  const [roleFilter, setRoleFilter] = useState('all')
  const [showInactive, setShowInactive] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [rowError, setRowError] = useState(null)
  const [actioningId, setActioningId] = useState(null)
  const [addOpen, setAddOpen] = useState(false)
  const [myEmail, setMyEmail] = useState(null)

  useEffect(() => {
    me().then((identity) => setMyEmail(identity.email)).catch(() => {})
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    listMembers({ role: roleFilter === 'all' ? undefined : roleFilter, includeInactive: showInactive })
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [roleFilter, showInactive])

  useEffect(() => {
    load()
  }, [load])

  function handleAdded() {
    setAddOpen(false)
    load()
  }

  async function handleDeactivate(member) {
    if (!window.confirm(`להסיר את ${member.identity_name} מהמשרד? הגישה למשרד תיחסם מיידית, אך ההיסטוריה שלו/שלה (מסמכים, שעות) תישמר.`)) {
      return
    }
    setActioningId(member.id)
    setRowError(null)
    try {
      await deactivateMember(member.id)
      load()
    } catch (err) {
      setRowError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  const columns = [
    {
      key: 'name',
      label: 'שם',
      render: (row) => (
        <div>
          <div className="member-name">{row.identity_name}</div>
          <div className="member-email">{row.identity_email}</div>
        </div>
      ),
    },
    {
      key: 'role',
      label: 'תפקיד',
      render: (row) => <span className="chip member-role-chip">{ROLE_LABELS[row.role] || row.role}</span>,
    },
    {
      key: 'active',
      label: 'סטטוס',
      render: (row) => (
        <span className={`chip ${row.active ? 'member-status-active' : 'member-status-inactive'}`}>
          {row.active ? 'פעיל/ה' : 'הוסר/ה'}
        </span>
      ),
    },
    {
      key: 'actions',
      label: '',
      render: (row) => {
        const isSelf = row.identity_email === myEmail
        return row.active ? (
          <div className="member-actions">
            <button
              type="button"
              className="member-action member-action-danger"
              onClick={() => handleDeactivate(row)}
              disabled={actioningId === row.id || isSelf}
              title={isSelf ? 'לא ניתן להסיר את עצמך' : undefined}
            >
              הסרה
            </button>
          </div>
        ) : (
          <span className="member-inactive-hint">להחזרה: הוספה מחדש לפי אימייל</span>
        )
      },
    },
  ]

  return (
    <AppShell activeKey="members">
      <div className="cases-header">
        <h1 className="page-title">אנשי צוות</h1>
        <button type="button" className="primary-button cases-new-button" onClick={() => setAddOpen(true)}>
          + הוספת איש צוות
        </button>
      </div>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && (
        <div className="card cases-table-card">
          <div className="cases-tabs">
            {ROLE_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`cases-tab${roleFilter === tab.key ? ' active' : ''}`}
                onClick={() => setRoleFilter(tab.key)}
              >
                {tab.label}
              </button>
            ))}
            <button
              type="button"
              className={`members-inactive-toggle${showInactive ? ' active' : ''}`}
              onClick={() => setShowInactive((v) => !v)}
            >
              {showInactive ? 'מציג גם הוסרו' : 'הצג גם מי שהוסר'}
            </button>
          </div>

          {rowError && <FormError message={rowError} />}

          <DataTable
            columns={columns}
            rows={result?.items}
            loading={loading}
            emptyMessage="אין אנשי צוות להצגה."
          />
        </div>
      )}

      <AddMemberModal open={addOpen} onClose={() => setAddOpen(false)} onAdded={handleAdded} />
    </AppShell>
  )
}
