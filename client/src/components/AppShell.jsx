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
    key: 'documents',
    label: 'מסמכים',
    icon: (
      <>
        <path d="M6 3h9l5 5v13H6z" />
        <path d="M15 3v5h5" />
      </>
    ),
  },
  {
    key: 'hours',
    label: 'שעות עבודה',
    icon: (
      <>
        <circle cx="12" cy="12" r="8.5" />
        <path d="M12 7.5V12l3 2" />
      </>
    ),
  },
]

// Wraps every authenticated screen: resolves the session once (redirects to
// /login if it isn't valid) and renders the sidebar shell around whatever
// page content is passed in — the same "who is this" check every real page
// needs, written once instead of per-page.
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
          <span className="wordmark">CaseHub</span>
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
