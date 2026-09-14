import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RegisterPage from './pages/RegisterPage'
import LobbyLoginPage from './pages/LobbyLoginPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DevOutboxPage from './pages/DevOutboxPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'
import WorkLogImportPage from './pages/WorkLogImportPage'
import ProfilePage from './pages/ProfilePage'
import PublicHomePage from './pages/PublicHomePage'
import HomePage from './pages/HomePage'
import { isLobbyHost } from './utils/host'
import { setStoredIsManager, setStoredRole } from './api/session'

// A lobby login redirect lands here carrying ?role=lawyer|client (and, for
// a lawyer, ?is_manager=0|1) in the URL — the tenant subdomain it lands on
// is a different origin from the lobby, so it can't read anything the
// lobby page stored client-side (CLAUDE.md's Multi-tenancy architecture).
// Read it once on mount, stash it the same way a normal per-tenant login
// does, then strip it from the URL so it doesn't linger in the address bar
// or get carried into a share link.
function useLobbyRoleParam() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const role = params.get('role')
    if (!role) return
    setStoredRole(role)
    setStoredIsManager(params.get('is_manager') === '1')
    params.delete('role')
    params.delete('is_manager')
    const query = params.toString()
    window.history.replaceState({}, '', window.location.pathname + (query ? `?${query}` : ''))
  }, [])
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
            {/* /auth/register has no tenant dependency at all (a bare
                global Identity) — routed here too so it's actually
                reachable from the lobby, not just via an invite link on a
                tenant subdomain (see the other /register route below). */}
            <Route
              path="/register"
              element={
                <Layout>
                  <RegisterPage />
                </Layout>
              }
            />
            <Route
              path="/forgot-password"
              element={
                <Layout>
                  <ForgotPasswordPage />
                </Layout>
              }
            />
            <Route
              path="/reset-password"
              element={
                <Layout>
                  <ResetPasswordPage />
                </Layout>
              }
            />
            <Route
              path="/dev-outbox"
              element={
                <Layout>
                  <DevOutboxPage />
                </Layout>
              }
            />
            <Route
              path="/"
              element={
                <Layout>
                  <HomePage />
                </Layout>
              }
            />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </>
        ) : (
          // No tenant-subdomain /login here anymore — lawyer/client only
          // ever logs in via the lobby now (CLAUDE.md's Multi-tenancy
          // architecture: the lobby is the one login entry point per app).
          // AppShell's own session check is what sends an unauthenticated
          // visitor to the lobby (see AppShell.jsx); "/" still shows the
          // public homepage for a logged-out visitor, unchanged.
          <>
            <Route
              path="/register"
              element={
                <Layout>
                  <RegisterPage />
                </Layout>
              }
            />
            <Route path="/cases" element={<CasesListPage />} />
            <Route path="/cases/:caseId" element={<CaseDetailPage />} />
            <Route path="/work-logs/import" element={<WorkLogImportPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            {/* Always the firm's public page — even for an already-
                connected visitor clicking through from the directory
                (CLAUDE.md's directory click-through fix: never skip
                straight to /cases). PublicHomePage itself resolves auth
                state and offers the right call-to-action either way. */}
            <Route path="/" element={<PublicHomePage />} />
            <Route path="*" element={<Navigate to="/cases" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}
