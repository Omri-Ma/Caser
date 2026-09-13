import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import LobbyLoginPage from './pages/LobbyLoginPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'
import DashboardPage from './pages/DashboardPage'
import MembersPage from './pages/MembersPage'
import AuditLogPage from './pages/AuditLogPage'
import BrandingPage from './pages/BrandingPage'
import SubscriptionPage from './pages/SubscriptionPage'
import WorkLogImportPage from './pages/WorkLogImportPage'
import PlatformLoginPage from './pages/PlatformLoginPage'
import PlatformDashboardPage from './pages/PlatformDashboardPage'
import { isPlatformHost, isLobbyHost } from './utils/host'

// This bundle serves three entirely different route trees depending on the
// hostname it's reached at (CLAUDE.md's Multi-tenancy architecture):
// platform.<BASE_DOMAIN> is super_admin's fixed, non-tenant address,
// www.<BASE_DOMAIN> is the reserved, non-tenant lobby (signup + multi-firm
// login, neither of which has a subdomain to resolve yet), and every other
// subdomain is a real firm's office_manager CMS. Nobody cross-logs into
// another tree's routes, so the route tree itself branches on hostname
// rather than trying to make one set of routes cover all three.
export default function App() {
  const platform = isPlatformHost()
  const lobby = isLobbyHost()

  return (
    <BrowserRouter>
      <Routes>
        {platform ? (
          <>
            <Route
              path="/login"
              element={
                <Layout>
                  <PlatformLoginPage />
                </Layout>
              }
            />
            <Route path="/dashboard" element={<PlatformDashboardPage />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </>
        ) : lobby ? (
          <>
            <Route
              path="/signup"
              element={
                <Layout>
                  <SignupPage />
                </Layout>
              }
            />
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
              path="/login"
              element={
                <Layout>
                  <LoginPage />
                </Layout>
              }
            />
            <Route path="/cases" element={<CasesListPage />} />
            <Route path="/cases/:caseId" element={<CaseDetailPage />} />
            <Route path="/members" element={<MembersPage />} />
            <Route path="/audit-log" element={<AuditLogPage />} />
            <Route path="/work-logs/import" element={<WorkLogImportPage />} />
            <Route path="/settings/branding" element={<BrandingPage />} />
            <Route path="/settings/subscription" element={<SubscriptionPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/" element={<Navigate to="/cases" replace />} />
            <Route path="*" element={<Navigate to="/cases" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}
