import { useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import { FormField, FormError } from '../components/Form'
import { getTenant, updateTenant, uploadLogo } from '../api/tenant'
import { apiBaseUrl } from '../api/client'
import './SettingsPage.css'

// office_manager-only screen to edit the firm's own branding — direct
// Tenants columns (name/primary_color), not the generic Settings table
// (CLAUDE.md's Branding requirement). subdomain isn't editable here. Logo
// is a real file upload (POST /tenant/logo), not a URL text field.
export default function BrandingPage() {
  const [tenant, setTenant] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [name, setName] = useState('')
  const [primaryColor, setPrimaryColor] = useState('')
  const [about, setAbout] = useState('')
  const [saveError, setSaveError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [logoFile, setLogoFile] = useState(null)
  const [logoError, setLogoError] = useState(null)
  const [uploadingLogo, setUploadingLogo] = useState(false)
  // Cache-busts the preview <img> after a re-upload — the URL itself
  // (/tenant/logo) never changes, so the browser would otherwise keep
  // showing the previous image from cache.
  const [logoVersion, setLogoVersion] = useState(0)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getTenant()
      .then((data) => {
        setTenant(data)
        setName(data.name)
        setPrimaryColor(data.primary_color || '')
        setAbout(data.about || '')
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
      const updated = await updateTenant({
        name: name.trim(),
        primaryColor: primaryColor.trim(),
        about: about.trim(),
      })
      setTenant(updated)
      setAbout(updated.about || '')
      setSaved(true)
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleLogoUpload(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setLogoFile(file)
    setLogoError(null)
    setUploadingLogo(true)
    try {
      const updated = await uploadLogo(file)
      setTenant(updated)
      setLogoVersion((v) => v + 1)
    } catch (err) {
      setLogoError(err.message)
    } finally {
      setUploadingLogo(false)
      setLogoFile(null)
    }
  }

  return (
    <AppShell activeKey="branding">
      <h1 className="page-title settings-title">מיתוג</h1>

      {loading && <div className="cases-state">טוען פרטי משרד…</div>}
      {!loading && error && <div className="cases-state cases-state-error">{error}</div>}

      {!loading && !error && tenant && (
        <div className="card settings-card branding-layout">
          <form onSubmit={handleSubmit} className="branding-form">
            <FormError message={saveError} />
            {saved && <div className="reset-password-success">הפרטים נשמרו בהצלחה.</div>}

            <FormField label="כתובת המשרד">
              <div className="branding-subdomain-row">
                <input value={`${tenant.subdomain}.lvh.me`} readOnly disabled className="branding-subdomain-input" dir="ltr" />
                <span className="branding-subdomain-note">קבועה, לא ניתנת לשינוי</span>
              </div>
            </FormField>
            <FormField label="שם המשרד">
              <input value={name} onChange={(event) => setName(event.target.value)} required maxLength={255} />
            </FormField>
            <FormField label="לוגו">
              <FormError message={logoError} />
              <input type="file" accept="image/png,image/jpeg" onChange={handleLogoUpload} disabled={uploadingLogo} />
              {uploadingLogo && <div className="branding-logo-uploading">מעלה{logoFile ? ` ${logoFile.name}` : ''}…</div>}
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
            <FormField label="על המשרד (מוצג בעמוד הציבורי)">
              <textarea
                value={about}
                onChange={(event) => setAbout(event.target.value)}
                placeholder="כמה מילים על המשרד שיוצגו לכל מבקר בעמוד הבית הציבורי…"
                maxLength={2000}
                rows={5}
              />
            </FormField>

            <button type="submit" className="primary-button" disabled={saving || !name.trim()}>
              {saving ? 'שומר…' : 'שמירת שינויים'}
            </button>
          </form>

          <div className="branding-preview">
            <div className="branding-preview-label">תצוגה מקדימה</div>
            <div className="branding-preview-card" style={{ borderColor: primaryColor || undefined }}>
              {tenant.has_logo ? (
                <img
                  src={`${apiBaseUrl()}/tenant/logo?v=${logoVersion}`}
                  alt="לוגו המשרד"
                  className="branding-preview-logo"
                  onError={(e) => { e.target.style.display = 'none' }}
                />
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
