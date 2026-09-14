import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { me, myTenants, logout } from '../api/auth'
import { getTenant } from '../api/tenant'
import { lobbyLoginUrl, redirectToTenant } from '../utils/host'
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
    key: 'lawyers',
    label: 'עורכי דין',
    path: '/members/lawyers',
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
    key: 'clients',
    label: 'לקוחות',
    path: '/members/clients',
    icon: (
      <>
        <circle cx="12" cy="8.5" r="3.2" />
        <path d="M5.5 19.5c0-3.6 2.9-6.2 6.5-6.2s6.5 2.6 6.5 6.2" />
      </>
    ),
  },
  {
    key: 'admins',
    label: 'מנהלי משרד',
    path: '/members/admins',
    icon: (
      <>
        <path d="M12 3.5l7 3v5c0 4.5-3 7.5-7 8.5-4-1-7-4-7-8.5v-5z" />
        <path d="M9.5 12l1.8 1.8L14.8 10" />
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
    key: 'branding',
    label: 'מיתוג',
    path: '/settings/branding',
    icon: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19 12a7 7 0 00-.14-1.4l2-1.56-2-3.46-2.36.95a7 7 0 00-2.42-1.4L13.6 3h-3.2l-.48 2.13a7 7 0 00-2.42 1.4l-2.36-.95-2 3.46 2 1.56a7 7 0 000 2.8l-2 1.56 2 3.46 2.36-.95a7 7 0 002.42 1.4L10.4 21h3.2l.48-2.13a7 7 0 002.42-1.4l2.36.95 2-3.46-2-1.56A7 7 0 0019 12z" />
      </>
    ),
  },
  {
    key: 'subscription',
    label: 'מנוי ותוכנית',
    path: '/settings/subscription',
    icon: (
      <>
        <rect x="3.5" y="5" width="17" height="14" rx="2" />
        <path d="M3.5 9.5h17" />
        <path d="M7 14h4" />
      </>
    ),
  },
  {
    key: 'profile',
    label: 'פרופיל אישי',
    path: '/settings/profile',
    icon: (
      <>
        <circle cx="12" cy="8.5" r="3.2" />
        <path d="M5.5 19.5c0-3.6 2.9-6.2 6.5-6.2s6.5 2.6 6.5 6.2" />
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
  // Populated only in the "no access at this subdomain, but more than one
  // other firm to choose from" case (see below) — everything else is a
  // straight redirect, no UI of its own needed.
  const [otherTenants, setOtherTenants] = useState(null)
  // Every *other* active firm this office_manager also manages — powers the
  // multi-firm switcher dropdown (CLAUDE.md's Identity vs. membership: one
  // person can hold this role at more than one firm). Loaded best-effort,
  // after the real shell is already showing — never worth blocking render.
  const [switcherTenants, setSwitcherTenants] = useState([])
  const [switcherOpen, setSwitcherOpen] = useState(false)

  useEffect(() => {
    let cancelled = false

    me()
      .then(async (id) => {
        if (cancelled) return
        // A logged-in identity with no office_manager membership at *this*
        // subdomain (a stale bookmark, a link shared across firms, etc.) —
        // the backend already 403s every real route for this case, but
        // CLAUDE.md wants a real redirect, not a shell that quietly fails
        // to load. Resolve "which firm(s) does this person actually
        // manage" the same way the lobby already does, and act on it
        // before the shell ever renders — awaited here, not fire-and
        // -forget, so there's no flash of a broken CMS in between.
        try {
          const t = await getTenant()
          if (!cancelled) {
            setTenant(t)
            setIdentity(id)
            myTenants()
              .then((tenants) => {
                if (!cancelled) setSwitcherTenants(tenants.filter((other) => other.subdomain !== t.subdomain))
              })
              .catch(() => {})
          }
          return
        } catch (err) {
          if (cancelled || err.status !== 403) return
        }
        try {
          const tenants = await myTenants()
          if (cancelled) return
          if (tenants.length === 1) {
            redirectToTenant(tenants[0].subdomain, '/cases')
          } else if (tenants.length > 1) {
            setIdentity(id)
            setOtherTenants(tenants)
          } else {
            // No office_manager membership anywhere active — nothing to
            // redirect to but the lobby login.
            window.location.assign(lobbyLoginUrl())
          }
        } catch {
          window.location.assign(lobbyLoginUrl())
        }
      })
      // A hard, cross-origin redirect, not react-router navigation — this
      // tenant subdomain has no /login of its own anymore, office_manager
      // only ever logs in via the lobby (CLAUDE.md's Multi-tenancy
      // architecture).
      .catch(() => window.location.assign(lobbyLoginUrl()))
      .finally(() => {
        if (!cancelled) setChecking(false)
      })

    return () => {
      cancelled = true
    }
  }, [navigate])

  // ProfilePage saves the photo/bio/etc. via a plain PATCH, not a
  // navigation — this shell's own `identity` (fetched once, above) would
  // otherwise keep showing the pre-save name/photo in the header until the
  // next full page load. ProfilePage dispatches this event with the
  // already-updated identity the save response returned, so no second
  // fetch is needed here.
  useEffect(() => {
    function handleIdentityUpdated(event) {
      setIdentity(event.detail)
    }
    window.addEventListener('caser:identity-updated', handleIdentityUpdated)
    return () => window.removeEventListener('caser:identity-updated', handleIdentityUpdated)
  }, [])

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

  if (otherTenants) {
    return (
      <div className="no-access-page">
        <div className="no-access-picker">
          <h1>אין לך גישה למשרד הזה</h1>
          <p>בחרו את המשרד שאליו תרצו לעבור:</p>
          <ul className="no-access-picker-list">
            {otherTenants.map((t) => (
              <li key={t.tenant_id}>
                <button type="button" className="primary-button" onClick={() => redirectToTenant(t.subdomain, '/cases')}>
                  {t.firm_name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    )
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
            <span className="wordmark">Caser</span> · ניהול
          </span>
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
                {switcherTenants.length > 0 && (
                  <div className="tenant-switcher">
                    <button
                      type="button"
                      className="tenant-switcher-toggle"
                      onClick={() => setSwitcherOpen((open) => !open)}
                      title="מעבר בין משרדים"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                    {switcherOpen && (
                      <ul className="tenant-switcher-menu">
                        {switcherTenants.map((t) => (
                          <li key={t.tenant_id}>
                            <button type="button" onClick={() => redirectToTenant(t.subdomain, '/cases')}>
                              {t.firm_name}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            )}
            <div className="topbar-user">
              <div className="user-avatar">
                {identity.photo_url ? (
                  <img src={identity.photo_url} alt="" className="user-avatar-img" />
                ) : (
                  identity.name.trim().slice(0, 2)
                )}
              </div>
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
