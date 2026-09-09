import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
          <span className="wordmark">CaseHub · פלטפורמה</span>
        </div>
        <nav className="sidebar-nav">
          <div className="sidebar-nav-item active">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 13h4v7H4z" />
              <path d="M10 8h4v12h-4z" />
              <path d="M16 4h4v16h-4z" />
            </svg>
            לוח בקרה
          </div>
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
