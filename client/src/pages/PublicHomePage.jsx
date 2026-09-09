import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPublicProfile } from '../api/public'
import './PublicHomePage.css'

// Unauthenticated tenant landing page (CLAUDE.md's public homepage
// requirement) — shown at "/" to anyone who isn't logged in. Renders only
// non-sensitive firm profile info (name/logo/color/about); never touches
// cases, documents, or members.
export default function PublicHomePage() {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getPublicProfile()
      .then(setProfile)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="public-home">
        <div className="public-home-state">טוען…</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="public-home">
        <div className="public-home-state public-home-state-error">{error}</div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="public-home">
        <div className="public-home-state">לא נמצא מידע על משרד זה.</div>
      </div>
    )
  }

  return (
    <div className="public-home">
      <div className="public-home-card" style={{ borderColor: profile.primary_color || undefined }}>
        {profile.logo_url ? (
          <img
            src={profile.logo_url}
            alt={`לוגו ${profile.name}`}
            className="public-home-logo"
            onError={(event) => {
              event.target.style.display = 'none'
            }}
          />
        ) : (
          <div className="public-home-logo-placeholder">{profile.name.trim().slice(0, 2)}</div>
        )}

        <h1 className="public-home-name" style={{ color: profile.primary_color || undefined }}>
          {profile.name}
        </h1>

        <p className="public-home-about">{profile.about || 'המשרד טרם הוסיף תיאור.'}</p>

        <Link to="/login" className="primary-button public-home-signin">
          כניסה לפורטל
        </Link>
      </div>
    </div>
  )
}
