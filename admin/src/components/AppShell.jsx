import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { me, logout } from '../api/auth'
import { getTenant } from '../api/tenant'
import { lobbyLoginUrl } from '../utils/host'
import './AppShell.css'

const NAV_ITEMS = [
  {
    key: 'cases',
    label: 'תיקים',
    path: '/cases',
    icon: (
      <path d="M3 6a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V6z" />
    ),
  },
  {
    key: 'members',
    label: 'אנשי צוות',
    path: '/members',
    icon: (
      <>
        <circle cx="9" cy="8" r="3.2" />
        <path d="M3.5 19c0-3.3 2.5-5.5 5.5-5.5s5.5 2.2 5.5 5.5" />
        <circle cx="17" cy="8.5" r="2.4" />
        <path d="M15.5 13.7c2.4.4 4 2.4 4 5.3" />
      </>
    ),
  },
  {
    key: 'audit-log',
    label: 'יומן פעולות',
    path: '/audit-log',
    icon: (
      <>
        <path d="M6 3.5h9l3.5 3.5V20.5H6z" />
        <path d="M8.5 10.5h7M8.5 13.5h7M8.5 16.5h4.5" />
      </>
    ),
  },
  {
    key: 'work-log-import',
    label: 'ייבוא שעות מאקסל',
    path: '/work-logs/import',
    icon: (
      <>
        <circle cx="12" cy="12" r="8.5" />
        <path d="M12 7.5V12l3 2" />
      </>
    ),
  },
  {
    key: 'settings',
    label: 'הגדרות משרד',
    path: '/settings/branding',
    icon: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19 12a7 7 0 00-.14-1.4l2-1.56-2-3.46-2.36.95a7 7 0 00-2.42-1.4L13.6 3h-3.2l-.48 2.13a7 7 0 00-2.42 1.4l-2.36-.95-2 3.46 2 1.56a7 7 0 000 2.8l-2 1.56 2 3.46 2.36-.95a7 7 0 002.42 1.4L10.4 21h3.2l.48-2.13a7 7 0 002.42-1.4l2.36.95 2-3.46-2-1.56A7 7 0 0019 12z" />
      </>
    ),
  },
  {
    key: 'dashboard',
    label: 'לוח בקרה',
    path: '/dashboard',
    icon: (
      <>
        <path d="M4 13h4v7H4z" />
        <path d="M10 8h4v12h-4z" />
        <path d="M16 4h4v16h-4z" />
      </>
    ),
  },
]

// Wraps every authenticated admin screen: resolves the session once
// (redirects to the lobby's login if it isn't valid) and renders the sidebar shell
// around whatever page content is passed in — same pattern as client/'s
// AppShell, recolored navy for admin per CLAUDE.md's "two deliberately
// different designs" rule.
export default function AppShell({ activeKey, children }) {
  const navigate = useNavigate()
  const [identity, setIdentity] = useState(null)
  const [checking, setChecking] = useState(true)
  // Which firm this office_manager is currently managing — shown in the
  // header since a person can hold this same role at more than one firm
  // (CLAUDE.md's Identity vs. membership), so it isn't otherwise obvious
  // from the chrome alone. Best-effort: failing to load it is a display
  // nicety, not worth blocking the rest of the shell over.
  const [tenant, setTenant] = useState(null)
  const [logoFailed, setLogoFailed] = useState(false)

  useEffect(() => {
    me()
      .then(setIdentity)
      // A hard, cross-origin redirect, not react-router navigation — this
      // tenant subdomain has no /login of its own anymore, office_manager
      // only ever logs in via the lobby (CLAUDE.md's Multi-tenancy
      // architecture).
      .catch(() => window.location.assign(lobbyLoginUrl()))
      .finally(() => setChecking(false))
    getTenant()
      .then(setTenant)
      .catch(() => {})
  }, [navigate])

  async function handleLogout() {
    await logout()
    window.location.assign(lobbyLoginUrl())
  }

  if (checking) {
    return <div className="shell-loading">טוען…</div>
  }

  if (!identity) {
    return null
  }

  return (
    <div className="app-shell-layout">
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="4" width="18" height="16" rx="4" stroke="#fff" strokeWidth="1.8" />
            <path d="M7 9h10M7 13h6" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <span className="wordmark">Caser · ניהול</span>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) =>
            item.path ? (
              <button
                key={item.key}
                type="button"
                className={`sidebar-nav-item${activeKey === item.key ? ' active' : ''}`}
                onClick={() => navigate(item.path)}
              >
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  {item.icon}
                </svg>
                {item.label}
              </button>
            ) : (
              <div key={item.key} className="sidebar-nav-item disabled" title="בקרוב">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  {item.icon}
                </svg>
                {item.label}
              </div>
            ),
          )}
        </nav>
      </aside>
      <div className="app-content">
        <header className="content-topbar">
          <div className="topbar-start">
            {tenant && (
              <div className="topbar-tenant">
                {tenant.logo_url && !logoFailed ? (
                  <img
                    src={tenant.logo_url}
                    alt=""
                    className="topbar-tenant-logo"
                    onError={() => setLogoFailed(true)}
                  />
                ) : (
                  <div className="topbar-tenant-logo-placeholder">{tenant.name.trim().slice(0, 2)}</div>
                )}
                <span className="topbar-tenant-name">{tenant.name}</span>
              </div>
            )}
            <div className="topbar-user">
              <div className="user-avatar">{identity.name.trim().slice(0, 2)}</div>
              <div className="user-name">{identity.name}</div>
            </div>
          </div>
          <button type="button" className="topbar-logout" onClick={handleLogout}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 4.5H8a2 2 0 00-2 2v11a2 2 0 002 2h7" strokeLinecap="round" />
              <path d="M10 12h10.5M17.5 8.5L21 12l-3.5 3.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            התנתקות
          </button>
        </header>
        <main className="content-body">{children}</main>
      </div>
    </div>
  )
}
