import { useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import { FormField, FormError } from '../components/Form'
import PasswordConfirmFields, { passwordsValid } from '../components/PasswordConfirmFields'
import { changePassword, leaveFirm, me, updateProfile } from '../api/auth'
import { lobbyLoginUrl } from '../utils/host'
import './ProfilePage.css'

// Self-service "change my password" — lawyer and client alike. Nothing in
// admin/ can touch this account's password (CLAUDE.md's office_manager
// authority boundary), so this is the only place it changes at all besides
// the forgot-password flow.
export default function ProfilePage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Self-reported public-profile fields (CLAUDE.md's Identities note) —
  // meaningful for a lawyer (feeds the firm's public homepage team
  // section, gated separately by the office_manager-controlled
  // show_on_public_page toggle); harmless if a client fills them in too,
  // since a client is never shown there regardless.
  const [profileLoading, setProfileLoading] = useState(true)
  const [bio, setBio] = useState('')
  const [photoUrl, setPhotoUrl] = useState('')
  const [yearsOfExperience, setYearsOfExperience] = useState('')
  const [profileError, setProfileError] = useState(null)
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileSaved, setProfileSaved] = useState(false)

  const [leaving, setLeaving] = useState(false)
  const [leaveError, setLeaveError] = useState(null)

  useEffect(() => {
    me()
      .then((identity) => {
        setBio(identity.bio || '')
        setPhotoUrl(identity.photo_url || '')
        setYearsOfExperience(identity.years_of_experience ?? '')
      })
      .catch(() => {})
      .finally(() => setProfileLoading(false))
  }, [])

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

  async function handleLeaveFirm() {
    if (!window.confirm('לעזוב את המשרד הזה? הגישה לתיקים ולמסמכים כאן תיחסם מיידית.')) {
      return
    }
    setLeaveError(null)
    setLeaving(true)
    try {
      await leaveFirm()
      window.location.assign(lobbyLoginUrl())
    } catch (err) {
      setLeaveError(err.message)
      setLeaving(false)
    }
  }

  return (
    <AppShell activeKey="profile">
      <h1 className="page-title">פרופיל אישי</h1>

      {!profileLoading && (
        <div className="card profile-card">
          <div className="detail-card-title">פרופיל ציבורי</div>
          <p className="profile-public-hint">
            מוצג בעמוד הבית הציבורי של המשרד אם מנהל/ת המשרד הפעיל/ה זאת עבורך (רלוונטי לעורכי דין).
          </p>
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

      <div className="card profile-card">
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
