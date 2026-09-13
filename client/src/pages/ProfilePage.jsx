import { useState } from 'react'
import AppShell from '../components/AppShell'
import { FormField, FormError } from '../components/Form'
import PasswordConfirmFields, { passwordsValid } from '../components/PasswordConfirmFields'
import { changePassword } from '../api/auth'
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
      <h1 className="page-title">פרופיל אישי</h1>

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
