import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'
import PublicHomePage from './pages/PublicHomePage'
import { apiFetch } from './api/client'

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
  return (
    <BrowserRouter>
      <Routes>
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
        <Route path="/" element={<RootRoute />} />
        <Route path="*" element={<Navigate to="/cases" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
