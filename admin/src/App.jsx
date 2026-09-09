import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'
import MembersPage from './pages/MembersPage'
import BrandingPage from './pages/BrandingPage'
import SubscriptionPage from './pages/SubscriptionPage'
import PlatformLoginPage from './pages/PlatformLoginPage'
import PlatformDashboardPage from './pages/PlatformDashboardPage'
import { isPlatformHost } from './utils/host'

// This bundle serves two entirely different logins depending on the
// hostname it's reached at (CLAUDE.md's Multi-tenancy architecture):
// platform.<BASE_DOMAIN> is super_admin's fixed, non-tenant address, every
// other subdomain is a real firm's office_manager CMS. Nobody cross-logs
// into the other's routes, so the route tree itself branches on hostname
// rather than trying to make one set of routes cover both.
export default function App() {
  const platform = isPlatformHost()

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
        ) : (
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
                  <LoginPage />
                </Layout>
              }
            />
            <Route path="/cases" element={<CasesListPage />} />
            <Route path="/cases/:caseId" element={<CaseDetailPage />} />
            <Route path="/members" element={<MembersPage />} />
            <Route path="/settings/branding" element={<BrandingPage />} />
            <Route path="/settings/subscription" element={<SubscriptionPage />} />
            <Route path="/" element={<Navigate to="/cases" replace />} />
            <Route path="*" element={<Navigate to="/cases" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}
