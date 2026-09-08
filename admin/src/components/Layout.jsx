import { useState } from 'react'
import Modal from './Modal'
import './Layout.css'

// nav is the first child so it lands on the right edge in RTL row layout
// (the "start" side in RTL) — the brand sits after it, on the left.
export default function Layout({ children }) {
  const [aboutOpen, setAboutOpen] = useState(false)

  return (
    <div className="app-shell">
      <header className="app-header">
        <nav className="app-nav">
          <button type="button" className="app-nav-link" onClick={() => setAboutOpen(true)}>
            אודות
          </button>
        </nav>
        <div className="app-brand">CaseHub · ניהול</div>
      </header>
      <main className="app-main">{children}</main>
      <Modal open={aboutOpen} title="אודות CaseHub" onClose={() => setAboutOpen(false)}>
        <p>מערכת הניהול (CMS) עבור מנהלי משרד — ניהול עורכי דין, לקוחות ותיקים.</p>
      </Modal>
    </div>
  )
}
