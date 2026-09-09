import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { me, logout } from '../api/auth'
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
// (redirects to /login if it isn't valid) and renders the sidebar shell
// around whatever page content is passed in — same pattern as client/'s
// AppShell, recolored navy for admin per CLAUDE.md's "two deliberately
// different designs" rule. Dashboard isn't built yet, so it's a disabled
// placeholder for now, same as client/'s not-yet-built nav items.
export default function AppShell({ activeKey, children }) {
  const navigate = useNavigate()
  const [identity, setIdentity] = useState(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    me()
      .then(setIdentity)
      .catch(() => navigate('/login', { replace: true }))
      .finally(() => setChecking(false))
  }, [navigate])

  async function handleLogout() {
    await logout()
    navigate('/login')
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
          <span className="wordmark">CaseHub · ניהול</span>
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
          <div className="topbar-user">
            <div className="user-avatar">{identity.name.trim().slice(0, 2)}</div>
            <div className="user-name">{identity.name}</div>
          </div>
          <button type="button" className="topbar-logout" onClick={handleLogout}>
            התנתקות
          </button>
        </header>
        <main className="content-body">{children}</main>
      </div>
    </div>
  )
}
