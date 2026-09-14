import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { me, logout, checkMyMembership, myTenants } from '../api/auth'
import { getPublicProfile } from '../api/public'
import { apiBaseUrl } from '../api/client'
import { getStoredRole } from '../api/session'
import { lobbyHomeUrl, lobbyLoginUrl, redirectToTenant } from '../utils/host'
import InvitesInbox from './InvitesInbox'
import './AppShell.css'

function navItems(role) {
  return [
    {
      key: 'cases',
      label: 'תיקים',
      path: '/cases',
      icon: (
        <path d="M3 6a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V6z" />
      ),
    },
    {
      key: 'hours',
      label: 'ייבוא שעות מאקסל',
      // WorkLogs are never client-visible (CLAUDE.md) — only a lawyer gets a
      // real path here; a client sees the same disabled "coming soon" state
      // the whole nav uses for not-yet-built items, since this screen would
      // just 403 them.
      path: role === 'lawyer' ? '/work-logs/import' : undefined,
      icon: (
        <>
          <circle cx="12" cy="12" r="8.5" />
          <path d="M12 7.5V12l3 2" />
        </>
      ),
    },
    {
      key: 'profile',
      label: 'פרופיל אישי',
      path: '/profile',
      icon: (
        <>
          <circle cx="12" cy="8.5" r="3.2" />
          <path d="M5.5 19.5c0-3.6 2.9-6.2 6.5-6.2s6.5 2.6 6.5 6.2" />
        </>
      ),
    },
  ]
}

// Wraps every authenticated screen: resolves the session once (redirects to
// the lobby's login if it isn't valid) and renders the sidebar shell around whatever
// page content is passed in — the same "who is this" check every real page
// needs, written once instead of per-page.
export default function AppShell({ activeKey, children }) {
  const navigate = useNavigate()
  const [identity, setIdentity] = useState(null)
  const [checking, setChecking] = useState(true)
  const items = useMemo(() => navItems(getStoredRole()), [identity])
  // Every *other* active firm this identity also works with, as a lawyer
  // or client (CLAUDE.md's Identity vs. membership) — powers the multi-firm
  // switcher. Loaded best-effort, after the shell already renders.
  const [switcherTenants, setSwitcherTenants] = useState([])
  const [switcherOpen, setSwitcherOpen] = useState(false)
  // Which firm this actually is — same gap admin/'s header already closed
  // (GET /tenant + initials fallback); client/ never had its own tenant
  // lookup, so it reuses the existing public/unauthenticated profile route
  // (name + has_logo) instead of adding a new authenticated one.
  const [tenant, setTenant] = useState(null)
  const [logoFailed, setLogoFailed] = useState(false)

  useEffect(() => {
    let cancelled = false

    me()
      .then(async (id) => {
        if (cancelled) return
        // A logged-in lawyer/client with no membership at *this*
        // subdomain (stale bookmark, a link shared across firms, etc.)
        // lands on the general homepage instead of a shell whose every
        // real data call would 403 individually — CLAUDE.md's "Landing
        // somewhere you have no access" rule: "a client isn't necessarily
        // trying to reach a specific firm", unlike office_manager/lawyer,
        // so the homepage (not the lobby) is the useful landing spot.
        // Awaited before the shell ever renders, so there's no flash of a
        // broken CMS in between.
        try {
          await checkMyMembership()
        } catch (err) {
          if (!cancelled && err.status === 403) {
            window.location.assign(lobbyHomeUrl())
          }
          return
        }
        if (!cancelled) {
          setIdentity(id)
          const currentSubdomain = window.location.hostname.split('.')[0]
          myTenants()
            .then((tenants) => {
              if (!cancelled) setSwitcherTenants(tenants.filter((t) => t.subdomain !== currentSubdomain))
            })
            .catch(() => {})
          getPublicProfile()
            .then((profile) => {
              if (!cancelled) setTenant(profile)
            })
            .catch(() => {})
        }
      })
      // A hard, cross-origin redirect, not react-router navigation — this
      // tenant subdomain has no /login of its own anymore, lawyer/client
      // only ever log in via the lobby (CLAUDE.md's Multi-tenancy
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

  return (
    <div className="app-shell-layout">
      <aside className="app-sidebar">
        <button type="button" className="sidebar-brand sidebar-brand-link" onClick={() => navigate('/cases')}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="4" width="18" height="16" rx="4" stroke="#fff" strokeWidth="1.8" />
            <path d="M7 9h10M7 13h6" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <span className="wordmark">Caser</span>
        </button>
        <nav className="sidebar-nav">
          {items.map((item) =>
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
              <div className="topbar-firm">
                <div className="topbar-firm-identity">
                  {tenant.has_logo && !logoFailed ? (
                    <img
                      src={`${apiBaseUrl()}/public/logo`}
                      alt=""
                      className="topbar-tenant-logo"
                      onError={() => setLogoFailed(true)}
                    />
                  ) : (
                    <div className="topbar-tenant-logo-placeholder">{tenant.name.trim().slice(0, 2)}</div>
                  )}
                  <span className="topbar-tenant-name">{tenant.name}</span>
                </div>
                {switcherTenants.length > 0 && (
                  <div className="tenant-switcher tenant-switcher-under">
                    <button
                      type="button"
                      className="tenant-switcher-toggle-labeled"
                      onClick={() => setSwitcherOpen((open) => !open)}
                    >
                      מעבר בין משרדים
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
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
          <div className="topbar-actions">
            <InvitesInbox />
            <a href={lobbyHomeUrl()} className="topbar-home-link">
              לדף הבית של Caser
            </a>
            <button type="button" className="topbar-logout" onClick={handleLogout}>
              התנתקות
            </button>
          </div>
        </header>
        <main className="content-body">{children}</main>
      </div>
    </div>
  )
}
