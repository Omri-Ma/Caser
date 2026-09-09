import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'
import MembersPage from './pages/MembersPage'
import BrandingPage from './pages/BrandingPage'
import SubscriptionPage from './pages/SubscriptionPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
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
      </Routes>
    </BrowserRouter>
  )
}
