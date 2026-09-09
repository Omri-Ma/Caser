import { useCallback, useEffect, useRef, useState } from 'react'
import { FormError } from './Form'
import {
  archiveDocument,
  downloadDocument,
  listDocuments,
  reclassifyDocument,
  restoreDocument,
  uploadDocument,
} from '../api/documents'
import { formatDate, formatFileSize } from '../utils/format'
import './DocumentsPanel.css'

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

// The case-detail Documents card. showInternalTab is a display-only choice
// (lawyer sees both folders, client only ever sees "client") — the server
// enforces the real boundary regardless (CLAUDE.md: frontend checks are UX
// convenience only).
export default function DocumentsPanel({ caseId, role, showInternalTab, caseClosed }) {
  const isLawyer = role === 'lawyer'
  const [tab, setTab] = useState('client')
  const [viewingArchive, setViewingArchive] = useState(false)
  const [documents, setDocuments] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [actioningId, setActioningId] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    listDocuments(caseId, { folderType: tab, archived: viewingArchive })
      .then((page) => setDocuments(page.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [caseId, tab, viewingArchive])

  useEffect(() => {
    load()
  }, [load])

  function switchTab(nextTab) {
    setTab(nextTab)
    setViewingArchive(false)
    setActionError(null)
    setUploadError(null)
  }

  async function doUpload(file, confirmReplace) {
    setUploading(true)
    setUploadError(null)
    try {
      await uploadDocument(caseId, { file, folderType: tab, confirmReplace })
      load()
    } catch (err) {
      if (err.status === 409) {
        if (window.confirm(`${err.message} — להחליף?`)) {
          await doUpload(file, true)
          return
        }
      } else {
        setUploadError(err.message)
      }
    } finally {
      setUploading(false)
    }
  }

  function handleFileSelected(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (file) doUpload(file, false)
  }

  async function handleDownload(doc) {
    setActionError(null)
    try {
      const { blob, filename } = await downloadDocument(caseId, doc.id)
      triggerBrowserDownload(blob, filename || doc.original_filename)
    } catch (err) {
      setActionError(err.message)
    }
  }

  async function runAction(doc, action) {
    setActioningId(doc.id)
    setActionError(null)
    try {
      await action()
      load()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setActioningId(null)
    }
  }

  const handleArchive = (doc) => runAction(doc, () => archiveDocument(caseId, doc.id))
  const handleRestore = (doc) => runAction(doc, () => restoreDocument(caseId, doc.id))
  const handleReclassify = (doc) =>
    runAction(doc, () => reclassifyDocument(caseId, doc.id, doc.folder_type === 'client' ? 'internal' : 'client'))

  return (
    <div className="card detail-card">
      <div className="detail-tabs">
        <button type="button" className={`detail-tab${tab === 'client' ? ' active' : ''}`} onClick={() => switchTab('client')}>
          מסמכי לקוח
        </button>
        {showInternalTab && (
          <button type="button" className={`detail-tab${tab === 'internal' ? ' active' : ''}`} onClick={() => switchTab('internal')}>
            מסמכים פנימיים
          </button>
        )}
      </div>

      <div className="documents-toolbar">
        {caseClosed ? (
          <div className="documents-closed-note">התיק סגור — לא ניתן להעלות מסמכים חדשים.</div>
        ) : (
          <>
            <button type="button" className="secondary-button documents-upload-button" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
              {uploading ? 'מעלה…' : '+ העלאת מסמך'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.jpg,.jpeg,.png"
              hidden
              onChange={handleFileSelected}
            />
          </>
        )}
        {isLawyer && (
          <button
            type="button"
            className={`documents-archive-toggle${viewingArchive ? ' active' : ''}`}
            onClick={() => setViewingArchive((v) => !v)}
          >
            {viewingArchive ? 'חזרה למסמכים פעילים' : 'צפייה בארכיון'}
          </button>
        )}
      </div>
      {uploadError && <FormError message={uploadError} />}
      {actionError && <FormError message={actionError} />}

      {loading && <div className="detail-state">טוען מסמכים…</div>}
      {!loading && error && <div className="detail-state detail-state-error">{error}</div>}
      {!loading && !error && documents && documents.length === 0 && (
        <div className="detail-state">{viewingArchive ? 'הארכיון ריק.' : 'אין מסמכים בתיקייה זו עדיין.'}</div>
      )}
      {!loading && !error && documents && documents.length > 0 && (
        <ul className="documents-list">
          {documents.map((doc) => (
            <li key={doc.id} className="documents-row">
              <div className="documents-row-main">
                <div className="documents-row-name">{doc.original_filename}</div>
                <div className="documents-row-meta">
                  {doc.uploader_name} · {formatFileSize(doc.file_size)} · {formatDate(doc.created_at)}
                </div>
              </div>
              <div className="documents-row-actions">
                <button type="button" className="documents-action" onClick={() => handleDownload(doc)}>
                  הורדה
                </button>
                {!viewingArchive && (
                  <button
                    type="button"
                    className="documents-action"
                    onClick={() => handleArchive(doc)}
                    disabled={actioningId === doc.id}
                  >
                    העברה לארכיון
                  </button>
                )}
                {viewingArchive && isLawyer && (
                  <button
                    type="button"
                    className="documents-action"
                    onClick={() => handleRestore(doc)}
                    disabled={actioningId === doc.id}
                  >
                    שחזור
                  </button>
                )}
                {!viewingArchive && isLawyer && (
                  <button
                    type="button"
                    className="documents-action documents-action-muted"
                    onClick={() => handleReclassify(doc)}
                    disabled={actioningId === doc.id}
                  >
                    {doc.folder_type === 'client' ? 'העברה לפנימי' : 'העברה ללקוח'}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
