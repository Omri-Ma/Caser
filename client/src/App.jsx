import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import LobbyLoginPage from './pages/LobbyLoginPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'
import WorkLogImportPage from './pages/WorkLogImportPage'
import PublicHomePage from './pages/PublicHomePage'
import { apiFetch } from './api/client'
import { isLobbyHost } from './utils/host'
import { setStoredRole } from './api/session'

// A lobby login redirect lands here carrying ?role=lawyer|client in the
// URL — the tenant subdomain it lands on is a different origin from the
// lobby, so it can't read anything the lobby page stored client-side
// (CLAUDE.md's Multi-tenancy architecture). Read it once on mount, stash it
// the same way a normal per-tenant login does, then strip it from the URL
// so it doesn't linger in the address bar or get carried into a share link.
function useLobbyRoleParam() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const role = params.get('role')
    if (!role) return
    setStoredRole(role)
    params.delete('role')
    const query = params.toString()
    window.history.replaceState({}, '', window.location.pathname + (query ? `?${query}` : ''))
  }, [])
}

// "/" branches on session state: a logged-in visitor goes straight to their
// cases (unchanged behavior), a logged-out one sees the public firm landing
// page (CLAUDE.md's public homepage requirement) instead of being bounced
// straight to /login. Calling apiFetch directly (redirectOn401: false)
// rather than api/auth's me() — me() redirects to /login on a 401 itself
// (AppShell's normal behavior), which is wrong here: a 401 is exactly the
// "show the public page" case, not an error to bounce away from.
function RootRoute() {
  const [checking, setChecking] = useState(true)
  const [authenticated, setAuthenticated] = useState(false)

  useEffect(() => {
    apiFetch('/auth/me', { redirectOn401: false })
      .then(() => setAuthenticated(true))
      .catch(() => setAuthenticated(false))
      .finally(() => setChecking(false))
  }, [])

  if (checking) {
    return <div className="shell-loading">טוען…</div>
  }

  if (authenticated) {
    return <Navigate to="/cases" replace />
  }

  return <PublicHomePage />
}

export default function App() {
  useLobbyRoleParam()
  const lobby = isLobbyHost()

  return (
    <BrowserRouter>
      <Routes>
        {lobby ? (
          <>
            <Route
              path="/login"
              element={
                <Layout>
                  <LobbyLoginPage />
                </Layout>
              }
            />
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </>
        ) : (
          <>
            <Route
              path="/register"
              element={
                <Layout>
                  <RegisterPage />
                </Layout>
              }
            />
            <Route
              path="/login"
              element={
                <Layout>
                  <LoginPage />
                </Layout>
              }
            />
            <Route path="/cases" element={<CasesListPage />} />
            <Route path="/cases/:caseId" element={<CaseDetailPage />} />
            <Route path="/work-logs/import" element={<WorkLogImportPage />} />
            <Route path="/" element={<RootRoute />} />
            <Route path="*" element={<Navigate to="/cases" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}
