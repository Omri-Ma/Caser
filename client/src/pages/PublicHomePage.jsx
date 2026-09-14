import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPublicProfile } from '../api/public'
import { apiBaseUrl } from '../api/client'
import { checkMyMembership } from '../api/auth'
import './PublicHomePage.css'

const ROLE_LABELS = {
  office_manager: 'מנהל/ת משרד',
  lawyer: 'עורך/ת דין',
}

// This firm's public landing page — shown at "/" to EVERY visitor, logged
// in or not, connected to this firm or not (CLAUDE.md's directory
// click-through fix: clicking through to an already-connected firm must
// still land here first, never skip straight to /cases). Renders only
// non-sensitive firm profile info (name/logo/color/about); never touches
// cases, documents, or members. The one thing that changes with auth state
// is the call-to-action at the bottom (see `connected`, below).
export default function PublicHomePage() {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // Whether this visitor has real access at THIS firm specifically (not
  // just "logged in somewhere") — resolved separately from the public
  // profile fetch, and never blocks rendering the page itself.
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getPublicProfile()
      .then(setProfile)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
    checkMyMembership({ redirectOn401: false })
      .then(() => setConnected(true))
      .catch(() => setConnected(false))
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

        {profile.about && <p className="public-home-about">{profile.about}</p>}

        {connected ? (
          <Link to="/cases" className="primary-button public-home-signin">
            כניסה לתיקים שלי
          </Link>
        ) : (
          <Link to="/login" className="primary-button public-home-signin">
            כניסה לפורטל
          </Link>
        )}
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
