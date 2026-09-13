import { useNavigate } from 'react-router-dom'
import './SettingsTabs.css'

// Sub-navigation between the two office_manager settings screens — branding
// and subscription/plan — kept as two routes under one sidebar nav item
// rather than crammed into a single page component.
export default function SettingsTabs({ active }) {
  const navigate = useNavigate()
  return (
    <div className="settings-tabs">
      <button
        type="button"
        className={`settings-tab${active === 'branding' ? ' active' : ''}`}
        onClick={() => navigate('/settings/branding')}
      >
        מיתוג
      </button>
      <button
        type="button"
        className={`settings-tab${active === 'subscription' ? ' active' : ''}`}
        onClick={() => navigate('/settings/subscription')}
      >
        מנוי ותוכנית
      </button>
      <button
        type="button"
        className={`settings-tab${active === 'profile' ? ' active' : ''}`}
        onClick={() => navigate('/settings/profile')}
      >
        פרופיל אישי
      </button>
    </div>
  )
}
