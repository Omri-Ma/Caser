import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { me, logout } from '../api/auth'
import DataTable from '../components/DataTable'

// The actual proof this session sets out to give: a page that only renders
// once /auth/me has been resolved from the session cookie, not just a form
// that submitted successfully.
export default function LandingPage() {
  const navigate = useNavigate()
  const [identity, setIdentity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    me()
      .then(setIdentity)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const rows = identity
    ? [
        { id: 'id', label: 'מזהה', value: identity.id },
        { id: 'name', label: 'שם', value: identity.name },
        { id: 'email', label: 'אימייל', value: identity.email },
      ]
    : []

  return (
    <div className="page-card">
      <h1>{identity ? `שלום, ${identity.name}` : 'איזור אישי'}</h1>
      <DataTable
        columns={[
          { key: 'label', label: 'שדה' },
          { key: 'value', label: 'ערך' },
        ]}
        rows={rows}
        loading={loading}
        error={error}
      />
      {identity && (
        <button type="button" className="secondary-button" onClick={handleLogout} style={{ marginTop: 16 }}>
          התנתקות
        </button>
      )}
    </div>
  )
}
