import { Link } from 'react-router-dom'
import './Layout.css'

// The brand is the first child so it lands on the right edge in RTL row
// layout (the "start" side in RTL, under justify-content: space-between) —
// nav sits after it, on the left. Matches AppShell's sidebar, where the
// brand is likewise the first child and sits top-right.
//
// No "About" modal here anymore (it duplicated what HomePage's own hero
// section already explains) — replaced with real Login/Signup links, since
// a logged-out visitor landing on the general homepage had no obvious way
// into the app at all from this corner.
export default function Layout({ children }) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-brand">
          <span className="wordmark">Caser</span> · פורטל לקוחות
        </Link>
        <nav className="app-nav">
          <Link to="/login" className="app-nav-link">
            התחברות
          </Link>
          <Link to="/register" className="app-nav-link">
            הרשמה
          </Link>
        </nav>
      </header>
      <main className="app-main">{children}</main>
    </div>
  )
}
