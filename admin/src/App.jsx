import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import SignupPage from './pages/SignupPage'
import LobbyLoginPage from './pages/LobbyLoginPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DevOutboxPage from './pages/DevOutboxPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'
import DashboardPage from './pages/DashboardPage'
import LawyersPage from './pages/LawyersPage'
import ClientsPage from './pages/ClientsPage'
import AuditLogPage from './pages/AuditLogPage'
import BrandingPage from './pages/BrandingPage'
import SubscriptionPage from './pages/SubscriptionPage'
import ProfilePage from './pages/ProfilePage'
import WorkLogImportPage from './pages/WorkLogImportPage'
import PlatformLoginPage from './pages/PlatformLoginPage'
import PlatformDashboardPage from './pages/PlatformDashboardPage'
import PlatformFirmsPage from './pages/PlatformFirmsPage'
import PlatformProfilePage from './pages/PlatformProfilePage'
import PlatformUsersPage from './pages/PlatformUsersPage'
import PlatformAuditLogPage from './pages/PlatformAuditLogPage'
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
            <Route path="/firms" element={<PlatformFirmsPage />} />
            <Route path="/users" element={<PlatformUsersPage />} />
            <Route path="/audit-log" element={<PlatformAuditLogPage />} />
            <Route path="/profile" element={<PlatformProfilePage />} />
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
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </>
        ) : (
          // No tenant-subdomain /login here anymore — office_manager only
          // ever logs in via the lobby now (CLAUDE.md's Multi-tenancy
          // architecture: the lobby is the one login entry point per app).
          // An unauthenticated visitor lands here (via the catch-all below)
          // only via a direct/stale URL; AppShell's own session check is
          // what actually sends them to the lobby (see AppShell.jsx).
          <>
            <Route path="/cases" element={<CasesListPage />} />
            <Route path="/cases/:caseId" element={<CaseDetailPage />} />
            <Route path="/members/lawyers" element={<LawyersPage />} />
            <Route path="/members/clients" element={<ClientsPage />} />
            {/* Old combined /members link (bookmarks, external references) -
                lands on Lawyers, the first of the two split pages. */}
            <Route path="/members" element={<Navigate to="/members/lawyers" replace />} />
            <Route path="/audit-log" element={<AuditLogPage />} />
            <Route path="/work-logs/import" element={<WorkLogImportPage />} />
            <Route path="/settings/branding" element={<BrandingPage />} />
            <Route path="/settings/subscription" element={<SubscriptionPage />} />
            <Route path="/settings/profile" element={<ProfilePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/" element={<Navigate to="/cases" replace />} />
            <Route path="*" element={<Navigate to="/cases" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}
