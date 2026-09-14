import { useCallback, useEffect, useState } from 'react'
import { FormError } from './Form'
import { archiveDocument, downloadDocument, listDocuments, permanentlyDeleteDocument, restoreDocument } from '../api/documents'
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

const FOLDER_LABEL = { client: 'לקוח', internal: 'פנימי' }

// office_manager oversight view: both folders, no upload (that's the
// lawyer/client portal's job) — list, archive, and the permanent-delete-
// from-archive flow, per CLAUDE.md's Documents trash lifecycle.
export default function DocumentsPanel({ caseId, refreshSignal }) {
  const [folderFilter, setFolderFilter] = useState('all')
  const [viewingArchive, setViewingArchive] = useState(false)
  const [documents, setDocuments] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [actioningId, setActioningId] = useState(null)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput.trim()), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    listDocuments(caseId, {
      folderType: folderFilter === 'all' ? undefined : folderFilter,
      archived: viewingArchive,
      search: search || undefined,
    })
      .then((page) => setDocuments(page.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [caseId, folderFilter, viewingArchive, search])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, refreshSignal])

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

  function handlePermanentDelete(doc) {
    if (!window.confirm(`למחוק לצמיתות את "${doc.original_filename}"? הפעולה אינה הפיכה.`)) return
    runAction(doc, () => permanentlyDeleteDocument(caseId, doc.id))
  }

  return (
    <div className="card detail-card">
      <div className="detail-assign-header">
        <div className="detail-card-title">מסמכי התיק</div>
        <button
          type="button"
          className={`documents-archive-toggle${viewingArchive ? ' active' : ''}`}
          onClick={() => setViewingArchive((v) => !v)}
        >
          {viewingArchive ? 'חזרה למסמכים פעילים' : 'צפייה בארכיון'}
        </button>
      </div>

      <div className="documents-toolbar">
        <div className="documents-folder-filter">
          {['all', 'client', 'internal'].map((option) => (
            <button
              key={option}
              type="button"
              className={`documents-filter-chip${folderFilter === option ? ' active' : ''}`}
              onClick={() => setFolderFilter(option)}
            >
              {option === 'all' ? 'הכל' : FOLDER_LABEL[option]}
            </button>
          ))}
        </div>
        <input
          type="text"
          className="documents-search-input"
          placeholder="חיפוש לפי שם קובץ…"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />
      </div>
      {actionError && <FormError message={actionError} />}

      {loading && <div className="detail-state">טוען מסמכים…</div>}
      {!loading && error && <div className="detail-state detail-state-error">{error}</div>}
      {!loading && !error && documents && documents.length === 0 && (
        <div className="detail-state">
          {search ? 'לא נמצאו מסמכים התואמים את החיפוש.' : viewingArchive ? 'הארכיון ריק.' : 'אין מסמכים בתיק זה עדיין.'}
        </div>
      )}
      {!loading && !error && documents && documents.length > 0 && (
        <ul className="documents-list">
          {documents.map((doc) => (
            <li key={doc.id} className="documents-row">
              <div className="documents-row-main">
                <div className="documents-row-name">
                  {doc.original_filename} <span className="chip documents-folder-chip">{FOLDER_LABEL[doc.folder_type]}</span>
                </div>
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
                {viewingArchive && (
                  <>
                    <button
                      type="button"
                      className="documents-action"
                      onClick={() => handleRestore(doc)}
                      disabled={actioningId === doc.id}
                    >
                      שחזור
                    </button>
                    <button
                      type="button"
                      className="documents-action documents-action-danger"
                      onClick={() => handlePermanentDelete(doc)}
                      disabled={actioningId === doc.id}
                    >
                      מחיקה לצמיתות
                    </button>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
