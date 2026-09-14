import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { me, logout } from '../api/auth'
import './AppShell.css'

// super_admin's equivalent of AppShell — same sidebar/topbar structure and
// CSS (AppShell.css has nothing tenant-specific in it), just a different
// brand and nav, since super_admin only ever has the one dashboard screen
// (CLAUDE.md's Roles: firm-level/aggregate data only, no cases/members/
// settings to navigate to). me()/logout() are the same identity-level auth
// calls AppShell uses — they don't care whether the identity is a
// super_admin or a regular Membership holder.
export default function PlatformAppShell({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
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
          <span>
            <span className="wordmark">Caser</span> · פלטפורמה
          </span>
        </div>
        <nav className="sidebar-nav">
          <button
            type="button"
            className={`sidebar-nav-item${location.pathname === '/dashboard' ? ' active' : ''}`}
            onClick={() => navigate('/dashboard')}
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 13h4v7H4z" />
              <path d="M10 8h4v12h-4z" />
              <path d="M16 4h4v16h-4z" />
            </svg>
            לוח בקרה
          </button>
          <button
            type="button"
            className={`sidebar-nav-item${location.pathname === '/users' ? ' active' : ''}`}
            onClick={() => navigate('/users')}
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="9" cy="8" r="3.2" />
              <path d="M3.5 19c0-3.3 2.5-5.5 5.5-5.5s5.5 2.2 5.5 5.5" />
              <circle cx="17" cy="8.5" r="2.4" />
              <path d="M15.5 13.7c2.4.4 4 2.4 4 5.3" />
            </svg>
            אנשי צוות ולקוחות
          </button>
          <button
            type="button"
            className={`sidebar-nav-item${location.pathname === '/audit-log' ? ' active' : ''}`}
            onClick={() => navigate('/audit-log')}
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M6 3.5h9l3.5 3.5V20.5H6z" />
              <path d="M8.5 10.5h7M8.5 13.5h7M8.5 16.5h4.5" />
            </svg>
            יומן פעולות
          </button>
          <button
            type="button"
            className={`sidebar-nav-item${location.pathname === '/profile' ? ' active' : ''}`}
            onClick={() => navigate('/profile')}
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="12" cy="8.5" r="3.2" />
              <path d="M5.5 19.5c0-3.6 2.9-6.2 6.5-6.2s6.5 2.6 6.5 6.2" />
            </svg>
            פרופיל אישי
          </button>
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
