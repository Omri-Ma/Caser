import { useCallback, useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import DataTable from '../components/DataTable'
import InviteMemberModal from '../components/InviteMemberModal'
import { FormError } from '../components/Form'
import { deactivateMember, listMembers, updateMemberRole, updatePublicVisibility } from '../api/members'
import { listInvites, revokeInvite } from '../api/invites'
import { me } from '../api/auth'
import { formatDate } from '../utils/format'
import './MembersPage.css'

const STATUS_TABS = [
  { key: 'active', label: 'פעילים' },
  { key: 'pending', label: 'ממתינים' },
  { key: 'removed', label: 'הוסרו' },
]

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
  const [statusTab, setStatusTab] = useState('active')
  const [roleFilter, setRoleFilter] = useState('all')
  const [result, setResult] = useState(null)
  // Which tab `result` actually belongs to — set together with the data
  // itself (not read off `statusTab` directly), so columns never render
  // against rows from the *previous* tab's shape. `statusTab` changes the
  // instant a tab is clicked, but the fetch (and this) only resolve later;
  // rendering pending's invite-shaped columns against a still-in-flight
  // active tab's member rows (or vice versa) crashes on the mismatched shape
  // (e.g. an invite column reading a member row's missing `created_at`).
  const [resultTab, setResultTab] = useState('active')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [rowError, setRowError] = useState(null)
  const [actioningId, setActioningId] = useState(null)
  const [inviteRole, setInviteRole] = useState(null)
  const [myEmail, setMyEmail] = useState(null)

  useEffect(() => {
    me().then((identity) => setMyEmail(identity.email)).catch(() => {})
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const role = roleFilter === 'all' ? undefined : roleFilter
    const tabAtRequestTime = statusTab
    const request =
      statusTab === 'pending' ? listInvites({ role, status: 'pending' }) : listMembers({ role, active: statusTab === 'active' })
    request
      .then((data) => {
        setResult(data)
        setResultTab(tabAtRequestTime)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [roleFilter, statusTab])

  useEffect(() => {
    load()
  }, [load])

  function handleInvited() {
    setInviteRole(null)
    if (statusTab !== 'pending') setStatusTab('pending')
    else load()
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

  async function handleRevoke(invite) {
    if (!window.confirm(`לבטל את ההזמנה עבור ${invite.email}?`)) return
    setActioningId(invite.id)
    setRowError(null)
    try {
      await revokeInvite(invite.id)
      load()
    } catch (err) {
      setRowError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  async function handleToggleRole(member) {
    const nextRole = member.role === 'office_manager' ? 'lawyer' : 'office_manager'
    const verb = nextRole === 'office_manager' ? 'לקדם' : 'להוריד'
    if (!window.confirm(`${verb} את ${member.identity_name} ל${ROLE_LABELS[nextRole]}?`)) {
      return
    }
    setActioningId(member.id)
    setRowError(null)
    try {
      await updateMemberRole(member.id, nextRole)
      load()
    } catch (err) {
      setRowError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  async function handleTogglePublicVisibility(member) {
    setActioningId(member.id)
    setRowError(null)
    try {
      await updatePublicVisibility(member.id, !member.show_on_public_page)
      load()
    } catch (err) {
      setRowError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  const memberColumns = [
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
      key: 'public_page',
      label: 'עמוד ציבורי',
      render: (row) => {
        // Only office_manager/lawyer memberships are eligible at all (a
        // client is never "the firm" the way staff are, CLAUDE.md), and
        // only meaningful for an active membership — the removed tab never
        // shows this control.
        if (statusTab !== 'active' || (row.role !== 'office_manager' && row.role !== 'lawyer')) return null
        return (
          <label className="member-public-toggle">
            <input
              type="checkbox"
              checked={row.show_on_public_page}
              disabled={actioningId === row.id}
              onChange={() => handleTogglePublicVisibility(row)}
            />
            מוצג/ת
          </label>
        )
      },
    },
    {
      key: 'actions',
      label: '',
      render: (row) => {
        const isSelf = row.identity_email === myEmail
        const canToggleRole = row.role === 'office_manager' || row.role === 'lawyer'
        return statusTab === 'active' ? (
          <div className="member-actions">
            {canToggleRole && (
              <button
                type="button"
                className="member-action"
                onClick={() => handleToggleRole(row)}
                disabled={actioningId === row.id}
              >
                {row.role === 'office_manager' ? 'הורדה לעו״ד' : 'קידום למנהל/ת'}
              </button>
            )}
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
          <span className="member-inactive-hint">להחזרה: הזמנה מחדש לפי אימייל</span>
        )
      },
    },
  ]

  const inviteColumns = [
    { key: 'email', label: 'אימייל', render: (row) => row.email },
    {
      key: 'role',
      label: 'תפקיד',
      render: (row) => <span className="chip member-role-chip">{ROLE_LABELS[row.role] || row.role}</span>,
    },
    { key: 'invited_by', label: 'הוזמן/ה על ידי', render: (row) => row.invited_by_name },
    { key: 'created_at', label: 'תאריך הזמנה', render: (row) => formatDate(row.created_at) },
    {
      key: 'actions',
      label: '',
      render: (row) => (
        <button
          type="button"
          className="member-action member-action-danger"
          onClick={() => handleRevoke(row)}
          disabled={actioningId === row.id}
        >
          ביטול הזמנה
        </button>
      ),
    },
  ]

  return (
    <AppShell activeKey="members">
      <div className="cases-header">
        <h1 className="page-title">אנשי צוות</h1>
        <div className="members-invite-buttons">
          <button type="button" className="primary-button cases-new-button" onClick={() => setInviteRole('lawyer')}>
            + הזמנת עורך/ת דין
          </button>
          <button type="button" className="primary-button cases-new-button" onClick={() => setInviteRole('client')}>
            + הזמנת לקוח/ה
          </button>
        </div>
      </div>

      {error && <div className="cases-state cases-state-error">{error}</div>}

      {!error && (
        <div className="card cases-table-card">
          <div className="cases-tabs">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`cases-tab${statusTab === tab.key ? ' active' : ''}`}
                onClick={() => setStatusTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="cases-tabs members-role-tabs">
            {ROLE_TABS.filter((tab) => statusTab !== 'pending' || tab.key !== 'office_manager').map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`cases-tab${roleFilter === tab.key ? ' active' : ''}`}
                onClick={() => setRoleFilter(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {rowError && <FormError message={rowError} />}

          <DataTable
            columns={resultTab === 'pending' ? inviteColumns : memberColumns}
            rows={loading ? undefined : result?.items}
            loading={loading}
            emptyMessage={resultTab === 'pending' ? 'אין הזמנות ממתינות.' : 'אין אנשי צוות להצגה.'}
          />
        </div>
      )}

      <InviteMemberModal
        open={inviteRole !== null}
        role={inviteRole}
        onClose={() => setInviteRole(null)}
        onInvited={handleInvited}
      />
    </AppShell>
  )
}
