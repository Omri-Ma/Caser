import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'

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
        <Route path="/" element={<Navigate to="/cases" replace />} />
        <Route path="*" element={<Navigate to="/cases" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
