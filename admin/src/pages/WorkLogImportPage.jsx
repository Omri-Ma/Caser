import { useCallback, useEffect, useRef, useState } from 'react'
import AppShell from '../components/AppShell'
import { FormError } from '../components/Form'
import { listCases } from '../api/cases'
import { downloadWorkLogImportTemplate, importWorkLogs } from '../api/work_logs'
import { caseStatusLabel } from '../utils/caseStatus'
import './WorkLogImportPage.css'

function triggerBrowserDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// Excel import for work logs (CLAUDE.md Phase 3 item 1), office_manager's
// bulk side — this template adds a Lawyer Email column and can import hours
// across multiple lawyers at once (e.g. historical data entry), unlike the
// lawyer self-import screen in client/. Who actually triggered a bulk
// import is recorded in AuditLogs server-side; WorkLogs.lawyer_id still
// records whose hours each row is.
export default function WorkLogImportPage() {
  const [cases, setCases] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState(null)

  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [rowErrors, setRowErrors] = useState(null)
  const [importedCount, setImportedCount] = useState(null)
  const fileInputRef = useRef(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    listCases({ page: 1 })
      .then((page) => setCases(page.items.filter((c) => c.status !== 'closed')))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleDownloadTemplate() {
    setDownloading(true)
    setDownloadError(null)
    try {
      const { blob, filename } = await downloadWorkLogImportTemplate()
      triggerBrowserDownload(blob, filename || 'work_log_bulk_import_template.xlsx')
    } catch (err) {
      setDownloadError(err.message)
    } finally {
      setDownloading(false)
    }
  }

  async function handleFileSelected(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    setUploading(true)
    setUploadError(null)
    setRowErrors(null)
    setImportedCount(null)
    try {
      const result = await importWorkLogs(file)
      setImportedCount(result.imported_count)
      load()
    } catch (err) {
      setUploadError(err.message)
      setRowErrors(err.rowErrors || null)
    } finally {
      setUploading(false)
    }
  }

  return (
    <AppShell activeKey="work-log-import">
      <h1 className="page-title">ייבוא שעות עבודה מרוכז מאקסל</h1>

      <div className="card detail-card work-log-import-card">
        <div className="detail-card-title">שלב 1 — הורדת תבנית</div>
        <p className="work-log-import-hint">
          תבנית זו כוללת עמודת אימייל של עורך הדין וניתן לייבא בה שעות עבור מספר עורכי דין במשרד בבת אחת (למשל, הזנת נתונים היסטוריים).
        </p>
        <button type="button" className="secondary-button" onClick={handleDownloadTemplate} disabled={downloading}>
          {downloading ? 'מוריד…' : 'הורדת תבנית'}
        </button>
        {downloadError && <FormError message={downloadError} />}
      </div>

      <div className="card detail-card work-log-import-card">
        <div className="detail-card-title">שלב 2 — העלאת הקובץ המלא</div>
        <p className="work-log-import-hint">
          אם שורה כלשהי בקובץ שגויה, הייבוא כולו נדחה ולא נשמר דבר — תוקנו את השורה המצוינת ונסו שוב. הפעולה נרשמת ביומן הפעולות.
        </p>
        <button type="button" className="secondary-button" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
          {uploading ? 'מייבא…' : 'בחירת קובץ לייבוא'}
        </button>
        <input ref={fileInputRef} type="file" accept=".xlsx" hidden onChange={handleFileSelected} />

        {importedCount !== null && (
          <div className="work-log-import-success">יובאו בהצלחה {importedCount} רישומי שעות.</div>
        )}
        {uploadError && <FormError message={uploadError} />}
        {rowErrors && rowErrors.length > 0 && (
          <ul className="work-log-import-row-errors">
            {rowErrors.map((rowErr, i) => (
              <li key={`${rowErr.row}-${i}`}>
                שורה {rowErr.row}: {rowErr.message}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card detail-card work-log-import-card">
        <div className="detail-card-title">תיקים פתוחים הזמינים לייבוא</div>
        {loading && <div className="detail-state">טוען תיקים…</div>}
        {!loading && error && <div className="detail-state detail-state-error">{error}</div>}
        {!loading && !error && cases && cases.length === 0 && (
          <div className="detail-state">אין כרגע תיקים פתוחים במשרד — אין תיקים לייבוא שעות אליהם.</div>
        )}
        {!loading && !error && cases && cases.length > 0 && (
          <ul className="work-log-import-case-list">
            {cases.map((c) => (
              <li key={c.id}>
                #{c.id} — {c.title} ({caseStatusLabel(c.status)})
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  )
}
