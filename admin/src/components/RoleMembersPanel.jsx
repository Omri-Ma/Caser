import { useCallback, useEffect, useState } from 'react'
import DataTable from './DataTable'
import InviteMemberModal from './InviteMemberModal'
import { FormError } from './Form'
import {
  deactivateMember,
  listMembers,
  updateHourlyRate,
  updateManagerStatus,
  updatePublicVisibility,
} from '../api/members'
import { listInvites, revokeInvite } from '../api/invites'
import { me } from '../api/auth'
import { formatDate } from '../utils/format'
import './RoleMembersPanel.css'

const STATUS_TABS = [
  { key: 'active', label: 'פעילים' },
  { key: 'pending', label: 'ממתינים' },
  { key: 'removed', label: 'הוסרו' },
]

const ROLE_LABELS = {
  lawyer: 'עורך/ת דין',
  client: 'לקוח/ה',
}

// Plural page titles — a firm's roster is split into exactly two pages
// (Lawyers/Clients — CLAUDE.md's Memberships note: there is no third
// Admins page, since a firm has exactly one office_manager, fixed at
// founding, never more and never promoted/demoted into or out of).
const PAGE_TITLES = {
  lawyer: 'עורכי דין',
  client: 'לקוחות',
}

// Shared table + tab logic behind both per-role member pages (LawyersPage /
// ClientsPage) — CLAUDE.md's reusable-component rule: the active/pending/
// removed table itself only differs per page in which role it's scoped to
// and which actions apply, so that's the one thing parameterized here
// rather than duplicating the whole fetch/tabs/table logic twice.
//
// role: 'lawyer' | 'client' — which membership role this page manages
//   (also the role a new invite gets created as).
// inviteRole: pass the role to invite as, to show the "+ invite" button.
export default function RoleMembersPanel({ role, inviteRole }) {
  const [statusTab, setStatusTab] = useState('active')
  const [result, setResult] = useState(null)
  // Which tab `result` actually belongs to — set together with the data
  // itself (not read off `statusTab` directly), so columns never render
  // against rows from the *previous* tab's shape (see MembersPage's
  // original note this carries forward from).
  const [resultTab, setResultTab] = useState('active')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [rowError, setRowError] = useState(null)
  const [actioningId, setActioningId] = useState(null)
  const [inviting, setInviting] = useState(false)
  const [myEmail, setMyEmail] = useState(null)
  const [rateEditingId, setRateEditingId] = useState(null)
  const [rateDraft, setRateDraft] = useState('')
  const [rateSaving, setRateSaving] = useState(false)

  useEffect(() => {
    me().then((identity) => setMyEmail(identity.email)).catch(() => {})
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const tabAtRequestTime = statusTab
    const request =
      statusTab === 'pending'
        ? listInvites({ role, status: 'pending' })
        : listMembers({ role, active: statusTab === 'active' })
    request
      .then((data) => {
        setResult(data)
        setResultTab(tabAtRequestTime)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [statusTab, role])

  useEffect(() => {
    load()
  }, [load])

  function handleInvited() {
    setInviting(false)
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

  function startRateEdit(member) {
    setRateEditingId(member.id)
    setRateDraft(member.hourly_rate != null ? String(member.hourly_rate) : '')
    setRowError(null)
  }

  async function saveRate(member) {
    const value = Number(rateDraft)
    if (!rateDraft || !Number.isFinite(value) || value <= 0) {
      setRowError('יש להזין תעריף שעתי חיובי')
      return
    }
    setRateSaving(true)
    setRowError(null)
    try {
      await updateHourlyRate(member.id, value)
      setRateEditingId(null)
      load()
    } catch (err) {
      setRowError(err.message)
    } finally {
      setRateSaving(false)
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

  // Grants/revokes case-oversight authority only (full case visibility +
  // narrative generation in client_api) — never firm administration or a
  // role change; there is no such thing as a role change (CLAUDE.md's
  // Memberships note: a firm's office_manager is fixed at founding).
  async function handleToggleManagerStatus(member) {
    const verb = member.is_manager ? 'לבטל את סטטוס המנהל/ת של' : 'להעניק סטטוס מנהל/ת ל'
    if (!window.confirm(`${verb} ${member.identity_name}? סטטוס מנהל/ת מעניק ראייה מלאה על כל התיקים במשרד ויכולת ליצור נרטיבים, ללא סמכויות ניהול משרד.`)) {
      return
    }
    setActioningId(member.id)
    setRowError(null)
    try {
      await updateManagerStatus(member.id, !member.is_manager)
      load()
    } catch (err) {
      setRowError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  const showPublicToggle = role === 'lawyer'

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
    ...(role === 'lawyer'
      ? [
          {
            key: 'hourly_rate',
            label: 'תעריף שעתי',
            render: (row) => {
              if (statusTab !== 'active') return null
              if (rateEditingId === row.id) {
                return (
                  <div className="member-rate-edit">
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      className="member-rate-input"
                      value={rateDraft}
                      onChange={(event) => setRateDraft(event.target.value)}
                      autoFocus
                    />
                    <button type="button" className="member-action" onClick={() => saveRate(row)} disabled={rateSaving}>
                      {rateSaving ? 'שומר…' : 'שמירה'}
                    </button>
                    <button type="button" className="member-action" onClick={() => setRateEditingId(null)}>
                      ביטול
                    </button>
                  </div>
                )
              }
              return (
                <button type="button" className="member-rate-display" onClick={() => startRateEdit(row)}>
                  {row.hourly_rate != null ? `${Number(row.hourly_rate).toFixed(2)} ש"ח` : 'הגדרת תעריף'}
                </button>
              )
            },
          },
        ]
      : []),
    ...(role === 'lawyer'
      ? [
          {
            key: 'is_manager',
            label: 'מנהל/ת תיקים',
            render: (row) => {
              if (statusTab !== 'active') return null
              return (
                <label className="member-public-toggle">
                  <input
                    type="checkbox"
                    checked={row.is_manager}
                    disabled={actioningId === row.id}
                    onChange={() => handleToggleManagerStatus(row)}
                  />
                  מנהל/ת
                </label>
              )
            },
          },
        ]
      : []),
    ...(showPublicToggle
      ? [
          {
            key: 'public_page',
            label: 'עמוד ציבורי',
            render: (row) => {
              if (statusTab !== 'active') return null
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
        ]
      : []),
    {
      key: 'actions',
      label: '',
      render: (row) => {
        const isSelf = row.identity_email === myEmail
        return statusTab === 'active' ? (
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
          <span className="member-inactive-hint">להחזרה: הזמנה מחדש לפי אימייל</span>
        )
      },
    },
  ]

  const inviteColumns = [
    { key: 'email', label: 'אימייל', render: (row) => row.email },
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
    <>
      <div className="cases-header">
        <h1 className="page-title">{PAGE_TITLES[role]}</h1>
        {inviteRole && (
          <button type="button" className="primary-button cases-new-button" onClick={() => setInviting(true)}>
            + הזמנת {ROLE_LABELS[inviteRole]}
          </button>
        )}
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

          {rowError && <FormError message={rowError} />}

          <DataTable
            columns={resultTab === 'pending' ? inviteColumns : memberColumns}
            rows={loading ? undefined : result?.items}
            loading={loading}
            emptyMessage={resultTab === 'pending' ? 'אין הזמנות ממתינות.' : `אין ${PAGE_TITLES[role]} להצגה.`}
          />
        </div>
      )}

      {inviteRole && (
        <InviteMemberModal open={inviting} role={inviteRole} onClose={() => setInviting(false)} onInvited={handleInvited} />
      )}
    </>
  )
}
