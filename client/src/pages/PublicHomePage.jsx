import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPublicProfile } from '../api/public'
import { apiBaseUrl } from '../api/client'
import './PublicHomePage.css'

const ROLE_LABELS = {
  office_manager: 'מנהל/ת משרד',
  lawyer: 'עורך/ת דין',
}

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

  const team = profile.team || []
  const withPhoto = team.filter((member) => member.photo_url)
  const withoutPhoto = team.filter((member) => !member.photo_url)

  return (
    <div className="public-home">
      <div className="public-home-card" style={{ borderColor: profile.primary_color || undefined }}>
        {profile.has_logo ? (
          <img
            src={`${apiBaseUrl()}/public/logo`}
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

      {team.length > 0 && (
        <div className="public-home-team">
          <h2 className="public-home-team-title">הצוות שלנו</h2>

          {withPhoto.length > 0 && (
            <div className="public-home-team-grid">
              {withPhoto.map((member, index) => (
                <div key={index} className="public-home-team-card">
                  <img src={member.photo_url} alt={member.name} className="public-home-team-photo" />
                  <div className="public-home-team-name">{member.name}</div>
                  <div className="public-home-team-role">{ROLE_LABELS[member.role] || member.role}</div>
                  {member.bio && <p className="public-home-team-bio">{member.bio}</p>}
                </div>
              ))}
            </div>
          )}

          {withoutPhoto.length > 0 && (
            <ul className="public-home-team-plain-list">
              {withoutPhoto.map((member, index) => (
                <li key={index}>
                  <span className="public-home-team-name">{member.name}</span>
                  <span className="public-home-team-role">{ROLE_LABELS[member.role] || member.role}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
