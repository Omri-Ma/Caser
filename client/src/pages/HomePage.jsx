import { useEffect, useState } from 'react'
import { getPublicDirectory } from '../api/public'
import { apiBaseUrlForSubdomain } from '../api/client'
import { redirectToTenant } from '../utils/host'
import './HomePage.css'

// The lobby's general, non-tenant product homepage (CLAUDE.md's "general,
// non-tenant product homepage" requirement) — what Caser is, plus a public
// firm directory. Reachable anonymously and from a logged-in client
// (AppShell links back here). Deliberately not linked from admin/.
export default function HomePage() {
  const [entries, setEntries] = useState([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getPublicDirectory(page)
      .then((data) => {
        setEntries(data.items)
        setTotal(data.total)
        setPageSize(data.page_size)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="home-page">
      <section className="home-hero">
        <h1>Caser — פלטפורמה לניהול משרדי עורכי דין</h1>
        <p>
          Caser מרכזת עבור משרד עורכי דין את ניהול התיקים, המסמכים, שעות העבודה והלקוחות במקום
          אחד — לכל משרד סביבת עבודה נפרדת ומאובטחת משלו, עם ניהול הרשאות מדויק לכל תפקיד: מנהל
          משרד, עורך/ת דין ולקוח.
        </p>
      </section>

      <section className="home-directory">
        <h2>מדריך משרדים</h2>
        <p className="home-directory-sub">מצאו משרד ועברו לעמוד הבית הציבורי שלו.</p>

        {loading && <div className="home-state">טוען…</div>}
        {error && <div className="home-state home-state-error">{error}</div>}
        {!loading && !error && entries.length === 0 && (
          <div className="home-state">אין עדיין משרדים רשומים.</div>
        )}

        {!loading && !error && entries.length > 0 && (
          <>
            <ul className="home-directory-list">
              {entries.map((entry) => (
                <li key={entry.subdomain} className="home-directory-item">
                  <button
                    type="button"
                    className="home-directory-link"
                    onClick={() => redirectToTenant(entry.subdomain, '/')}
                  >
                    {entry.has_logo ? (
                      <img
                        src={`${apiBaseUrlForSubdomain(entry.subdomain)}/public/logo`}
                        alt=""
                        className="home-directory-logo"
                        onError={(event) => {
                          event.target.style.display = 'none'
                        }}
                      />
                    ) : (
                      <div className="home-directory-logo-placeholder">{entry.name.trim().slice(0, 2)}</div>
                    )}
                    <span className="home-directory-name">{entry.name}</span>
                    <span className="home-directory-subdomain">{entry.subdomain}</span>
                  </button>
                </li>
              ))}
            </ul>

            {totalPages > 1 && (
              <div className="home-directory-pager">
                <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  הקודם
                </button>
                <span>
                  עמוד {page} מתוך {totalPages}
                </span>
                <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  הבא
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
