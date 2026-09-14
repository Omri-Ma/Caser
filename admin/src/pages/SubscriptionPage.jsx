import { useCallback, useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import { FormError } from '../components/Form'
import { getSubscription, switchPlan } from '../api/subscriptions'
import { formatFileSize } from '../utils/format'
import './SettingsPage.css'

const PLAN_LABELS = { free: 'Free', pro: 'Pro', enterprise: 'Enterprise' }
const PLAN_ORDER = ['free', 'pro', 'enterprise']
// Mirrors the hardcoded limits actually enforced server-side
// (shared/plan_limits.py) — display-only, so a mismatch here would only
// ever affect wording, never enforcement (the backend never reads this).
const PLAN_DETAILS = {
  free: { price: 'ללא עלות', lawyers: 'עד 3 עורכי דין', storage: 'עד 1GB אחסון' },
  pro: { price: '99 ₪ לחודש', lawyers: 'עד 15 עורכי דין', storage: 'עד 20GB אחסון' },
  enterprise: { price: '499 ₪ לחודש', lawyers: 'עורכי דין ללא הגבלה', storage: 'עד 100GB אחסון' },
}

// office_manager plan/usage view — plan comes from the active Subscriptions
// row (never Tenants, which has no plan column), usage numbers come from
// the same shared/plan_limits.py helper the backend actually enforces
// against, so this screen can never show a different limit than what's
// really gated. Plan switch is self-service, no payment flow (CLAUDE.md:
// "a resource gate, not a commerce system").
export default function SubscriptionPage() {
  const [usage, setUsage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [switching, setSwitching] = useState(null)
  const [switchError, setSwitchError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getSubscription()
      .then(setUsage)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleSwitch(plan) {
    if (plan === usage.plan) return
    if (!window.confirm(`לעבור לתוכנית ${PLAN_LABELS[plan]}? זהו שינוי מיידי, ללא תהליך תשלום.`)) return
    setSwitching(plan)
    setSwitchError(null)
    try {
      const updated = await switchPlan(plan)
      setUsage(updated)
    } catch (err) {
      setSwitchError(err.message)
    } finally {
      setSwitching(null)
    }
  }

  return (
    <AppShell activeKey="subscription">
      <h1 className="page-title settings-title">מנוי ותוכנית</h1>

      {loading && <div className="cases-state">טוען פרטי מנוי…</div>}
      {!loading && error && <div className="cases-state cases-state-error">{error}</div>}
      {!loading && !error && usage && usage.lawyer_count === 0 && usage.pending_lawyer_invites === 0 && usage.storage_used_bytes === 0 && (
        <div className="card settings-card subscription-empty-note">
          המשרד עדיין לא צבר שימוש (אין עורכי דין או קבצים) — הנתונים למטה יתעדכנו עם הפעילות הראשונה.
        </div>
      )}

      {!loading && !error && usage && (
        <>
          <div className="card settings-card subscription-usage-card">
            <div className="subscription-current-plan">
              תוכנית נוכחית: <strong>{PLAN_LABELS[usage.plan]}</strong>
            </div>

            <UsageBar
              label="עורכי דין"
              // Matches check_plan_limit exactly (shared/plan_limits.py):
              // pending invites count toward the limit too, so the bar
              // shown here must include them or it understates how close
              // the firm actually is to being blocked from inviting more.
              used={usage.lawyer_count + usage.pending_lawyer_invites}
              limit={usage.lawyer_limit}
              formatValue={(v) => String(v)}
              unlimited={usage.plan === 'enterprise'}
              note={usage.pending_lawyer_invites > 0 ? `(מתוכם ${usage.pending_lawyer_invites} ממתינים)` : null}
            />
            <UsageBar
              label="אחסון"
              used={usage.storage_used_bytes}
              limit={usage.storage_limit_bytes}
              formatValue={formatFileSize}
              unlimited={usage.plan === 'enterprise'}
            />
          </div>

          <div className="card settings-card">
            <div className="detail-card-title subscription-plans-title">מעבר תוכנית</div>
            <FormError message={switchError} />
            <div className="subscription-plan-grid">
              {PLAN_ORDER.map((plan) => (
                <div key={plan} className={`subscription-plan-option${plan === usage.plan ? ' current' : ''}`}>
                  <div className="subscription-plan-name">{PLAN_LABELS[plan]}</div>
                  <div className="subscription-plan-price">{PLAN_DETAILS[plan].price}</div>
                  <ul className="subscription-plan-features">
                    <li>{PLAN_DETAILS[plan].lawyers}</li>
                    <li>{PLAN_DETAILS[plan].storage}</li>
                  </ul>
                  {plan === usage.plan ? (
                    <span className="chip member-status-active">התוכנית הנוכחית</span>
                  ) : (
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => handleSwitch(plan)}
                      disabled={switching !== null}
                    >
                      {switching === plan ? 'מעביר…' : 'מעבר לתוכנית זו'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </AppShell>
  )
}

function UsageBar({ label, used, limit, formatValue, unlimited, note }) {
  const percent = unlimited ? 0 : limit > 0 ? Math.min(100, (used / limit) * 100) : 0
  const over = !unlimited && used > limit
  return (
    <div className="usage-bar">
      <div className="usage-bar-header">
        <span>
          {label}
          {note && <span className="usage-bar-note"> {note}</span>}
        </span>
        {/* dir="ltr" forced explicitly — plain numbers/slash have no strong
            directional characters, so left to the surrounding RTL context
            they silently reorder ("1 / 3" renders as "3 / 1"). */}
        {unlimited ? (
          <span>{formatValue(used)} · ללא הגבלה</span>
        ) : (
          <span dir="ltr" className={over ? 'usage-bar-over' : ''}>
            {formatValue(used)} / {formatValue(limit)}
          </span>
        )}
      </div>
      {!unlimited && (
        <div className="usage-bar-track">
          <div className={`usage-bar-fill${over ? ' over' : ''}`} style={{ width: `${percent}%` }} />
        </div>
      )}
    </div>
  )
}
