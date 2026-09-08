import { createPortal } from 'react-dom'
import './Modal.css'

// Reusable dialog pattern for future confirm/edit flows (reset a member's
// password, permanently delete a document, ...) — established now so those
// screens extend it instead of building their own overlay each time.
export default function Modal({ open, title, onClose, children }) {
  if (!open) return null

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="סגירה">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>,
    document.body,
  )
}
