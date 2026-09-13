import { useState } from 'react'
import AppShell from '../components/AppShell'
import SettingsTabs from '../components/SettingsTabs'
import { FormField, FormError } from '../components/Form'
import PasswordConfirmFields, { passwordsValid } from '../components/PasswordConfirmFields'
import { changePassword } from '../api/auth'
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
    <AppShell activeKey="settings">
      <h1 className="page-title settings-title">הגדרות משרד</h1>
      <SettingsTabs active="profile" />

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
