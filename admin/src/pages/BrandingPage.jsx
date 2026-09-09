import { useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import SettingsTabs from '../components/SettingsTabs'
import { FormField, FormError } from '../components/Form'
import { getTenant, updateTenant } from '../api/tenant'
import './SettingsPage.css'

// office_manager-only screen to edit the firm's own branding — direct
// Tenants columns (name/logo_url/primary_color), not the generic Settings
// table (CLAUDE.md's Branding requirement). subdomain isn't editable here.
export default function BrandingPage() {
  const [tenant, setTenant] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [name, setName] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [primaryColor, setPrimaryColor] = useState('')
  const [saveError, setSaveError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getTenant()
      .then((data) => {
        setTenant(data)
        setName(data.name)
        setLogoUrl(data.logo_url || '')
        setPrimaryColor(data.primary_color || '')
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    setSaveError(null)
    setSaved(false)
    setSaving(true)
    try {
      const updated = await updateTenant({ name: name.trim(), logoUrl: logoUrl.trim(), primaryColor: primaryColor.trim() })
      setTenant(updated)
      setSaved(true)
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <AppShell activeKey="settings">
      <h1 className="page-title settings-title">הגדרות משרד</h1>
      <SettingsTabs active="branding" />

      {loading && <div className="cases-state">טוען פרטי משרד…</div>}
      {!loading && error && <div className="cases-state cases-state-error">{error}</div>}

      {!loading && !error && tenant && (
        <div className="card settings-card branding-layout">
          <form onSubmit={handleSubmit} className="branding-form">
            <FormError message={saveError} />
            {saved && <div className="reset-password-success">הפרטים נשמרו בהצלחה.</div>}

            <FormField label="שם המשרד">
              <input value={name} onChange={(event) => setName(event.target.value)} required maxLength={255} />
            </FormField>
            <FormField label="כתובת לוגו (URL)">
              <input
                type="url"
                value={logoUrl}
                onChange={(event) => setLogoUrl(event.target.value)}
                placeholder="https://…"
              />
            </FormField>
            <FormField label="צבע ראשי">
              <div className="branding-color-row">
                <input
                  type="color"
                  value={primaryColor || '#1e3a5f'}
                  onChange={(event) => setPrimaryColor(event.target.value)}
                  className="branding-color-input"
                />
                <input
                  value={primaryColor}
                  onChange={(event) => setPrimaryColor(event.target.value)}
                  placeholder="#1e3a5f"
                  maxLength={7}
                  className="branding-color-text"
                />
              </div>
            </FormField>

            <button type="submit" className="primary-button" disabled={saving || !name.trim()}>
              {saving ? 'שומר…' : 'שמירת שינויים'}
            </button>
          </form>

          <div className="branding-preview">
            <div className="branding-preview-label">תצוגה מקדימה</div>
            <div className="branding-preview-card" style={{ borderColor: primaryColor || undefined }}>
              {logoUrl ? (
                <img src={logoUrl} alt="לוגו המשרד" className="branding-preview-logo" onError={(e) => { e.target.style.display = 'none' }} />
              ) : (
                <div className="branding-preview-logo-placeholder">{name.trim().slice(0, 2) || '?'}</div>
              )}
              <div className="branding-preview-name" style={{ color: primaryColor || undefined }}>
                {name || 'שם המשרד'}
              </div>
              <div className="branding-preview-subdomain">{tenant.subdomain}.lvh.me</div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}
