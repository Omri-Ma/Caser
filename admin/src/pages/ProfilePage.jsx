import { useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import { FormField, FormError } from '../components/Form'
import PasswordConfirmFields, { passwordsValid } from '../components/PasswordConfirmFields'
import { changePassword, getMyPublicVisibility, me, updateMyPublicVisibility, updateProfile } from '../api/auth'
import './SettingsPage.css'

// Self-service "change my password" — the only lever anyone (including
// office_manager themselves) has over their own account here. This is
// deliberately the *only* password-changing path left in admin/ now that
// office_manager's admin-driven reset for other members is gone (CLAUDE.md's
// office_manager authority boundary: password is an Identities-level thing,
// never a Memberships-level lever another party gets to pull).
export default function ProfilePage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Self-reported public-profile fields (CLAUDE.md's Identities note) — feed
  // the firm's public homepage team section, gated separately per firm by
  // the office_manager-controlled show_on_public_page toggle (Members page).
  const [profileLoading, setProfileLoading] = useState(true)
  const [bio, setBio] = useState('')
  const [photoUrl, setPhotoUrl] = useState('')
  const [yearsOfExperience, setYearsOfExperience] = useState('')
  const [profileError, setProfileError] = useState(null)
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileSaved, setProfileSaved] = useState(false)

  // Own show_on_public_page — used to only be reachable through the now-
  // removed Admins page (RoleMembersPanel listing office_manager rows).
  // Self-service here instead: there's exactly one office_manager per
  // firm, so "which member" is never a real question for this toggle.
  const [showOnPublicPage, setShowOnPublicPage] = useState(false)
  const [visibilitySaving, setVisibilitySaving] = useState(false)
  const [visibilityError, setVisibilityError] = useState(null)

  useEffect(() => {
    me()
      .then((identity) => {
        setBio(identity.bio || '')
        setPhotoUrl(identity.photo_url || '')
        setYearsOfExperience(identity.years_of_experience ?? '')
      })
      .catch(() => {})
      .finally(() => setProfileLoading(false))
    getMyPublicVisibility()
      .then((data) => setShowOnPublicPage(data.show_on_public_page))
      .catch((err) => setVisibilityError(err.message))
  }, [])

  async function handleToggleVisibility() {
    const next = !showOnPublicPage
    setVisibilitySaving(true)
    setVisibilityError(null)
    try {
      const updated = await updateMyPublicVisibility(next)
      setShowOnPublicPage(updated.show_on_public_page)
    } catch (err) {
      setVisibilityError(err.message)
    } finally {
      setVisibilitySaving(false)
    }
  }

  async function handleProfileSubmit(event) {
    event.preventDefault()
    setProfileError(null)
    setProfileSaved(false)
    setProfileSaving(true)
    try {
      const updated = await updateProfile({
        bio,
        photoUrl,
        yearsOfExperience: yearsOfExperience === '' ? null : Number(yearsOfExperience),
      })
      // AppShell's header (photo/name) fetched the identity once on mount —
      // tell it about the fresh one so the avatar updates immediately,
      // without needing a page reload or navigation away and back.
      window.dispatchEvent(new CustomEvent('caser:identity-updated', { detail: updated }))
      setProfileSaved(true)
    } catch (err) {
      setProfileError(err.message)
    } finally {
      setProfileSaving(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSaved(false)
    setSaving(true)
    try {
      await changePassword({ currentPassword, newPassword })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setSaved(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <AppShell activeKey="profile">
      <h1 className="page-title settings-title">פרופיל אישי</h1>

      {!profileLoading && (
        <div className="card settings-card">
          <div className="detail-card-title">פרופיל ציבורי</div>
          <p className="profile-public-hint">
            כמנהל/ת המשרד, זהו הבקרה היחידה על הצגת הפרופיל שלך — אין מי שיפעיל אותה עבורך.
          </p>
          <FormError message={visibilityError} />
          <label className="member-public-toggle profile-visibility-toggle">
            <input
              type="checkbox"
              checked={showOnPublicPage}
              disabled={visibilitySaving}
              onChange={handleToggleVisibility}
            />
            הצגה בעמוד הבית הציבורי של המשרד
          </label>
          <form onSubmit={handleProfileSubmit}>
            <FormError message={profileError} />
            {profileSaved && <div className="reset-password-success">הפרופיל עודכן בהצלחה.</div>}
            <FormField label="תמונה (כתובת URL)">
              <input type="url" value={photoUrl} onChange={(event) => setPhotoUrl(event.target.value)} placeholder="https://…" />
            </FormField>
            <FormField label="שנות ניסיון">
              <input
                type="number"
                min="0"
                max="80"
                value={yearsOfExperience}
                onChange={(event) => setYearsOfExperience(event.target.value)}
              />
            </FormField>
            <FormField label="קצת עליי">
              <textarea value={bio} onChange={(event) => setBio(event.target.value)} maxLength={2000} rows={4} />
            </FormField>
            <button type="submit" className="primary-button" disabled={profileSaving}>
              {profileSaving ? 'שומר…' : 'שמירת פרופיל'}
            </button>
          </form>
        </div>
      )}

      <div className="card settings-card">
        <div className="detail-card-title">שינוי סיסמה</div>
        <form onSubmit={handleSubmit}>
          <FormError message={error} />
          {saved && <div className="reset-password-success">הסיסמה עודכנה בהצלחה.</div>}
          <FormField label="סיסמה נוכחית">
            <input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              required
              autoFocus
            />
          </FormField>
          <PasswordConfirmFields
            password={newPassword}
            onPasswordChange={(event) => setNewPassword(event.target.value)}
            confirmPassword={confirmPassword}
            onConfirmPasswordChange={(event) => setConfirmPassword(event.target.value)}
          />
          <button
            type="submit"
            className="primary-button"
            disabled={saving || !currentPassword || !passwordsValid(newPassword, confirmPassword)}
          >
            {saving ? 'מעדכן…' : 'עדכון סיסמה'}
          </button>
        </form>
      </div>
    </AppShell>
  )
}
