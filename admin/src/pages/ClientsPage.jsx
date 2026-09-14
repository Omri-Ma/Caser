import AppShell from '../components/AppShell'
import RoleMembersPanel from '../components/RoleMembersPanel'

// One of the three per-role member pages (CLAUDE.md's Members split) —
// clients only. Invitable directly (inviteRole="client"); no role-toggle
// prop at all — a client is never involved in the office_manager<->lawyer
// promote/demote toggle, in or out of it (CLAUDE.md's Memberships note).
export default function ClientsPage() {
  return (
    <AppShell activeKey="clients">
      <RoleMembersPanel role="client" inviteRole="client" />
    </AppShell>
  )
}
