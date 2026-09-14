import { useState } from 'react'
import Modal from './Modal'
import './Layout.css'

// The brand is the first child so it lands on the right edge in RTL row
// layout (the "start" side in RTL, under justify-content: space-between) —
// nav sits after it, on the left. Matches AppShell's sidebar, where the
// brand is likewise the first child and sits top-right.
export default function Layout({ children }) {
  const [aboutOpen, setAboutOpen] = useState(false)

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand">
          <span className="wordmark">Caser</span> · ניהול
        </div>
        <nav className="app-nav">
          <button type="button" className="app-nav-link" onClick={() => setAboutOpen(true)}>
            אודות
          </button>
        </nav>
      </header>
      <main className="app-main">{children}</main>
      <Modal open={aboutOpen} title="אודות Caser" onClose={() => setAboutOpen(false)}>
        <p>מערכת הניהול (CMS) עבור מנהלי משרד — ניהול עורכי דין, לקוחות ותיקים.</p>
      </Modal>
    </div>
  )
}
