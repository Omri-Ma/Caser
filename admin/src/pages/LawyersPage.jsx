import AppShell from '../components/AppShell'
import RoleMembersPanel from '../components/RoleMembersPanel'

// One of the two per-role member pages (CLAUDE.md's Members split) —
// lawyers only. Invitable directly (inviteRole="lawyer"). No role-change
// action: a firm's role is fixed at founding and never changes between
// office_manager and lawyer (CLAUDE.md's Memberships note) — case-oversight
// authority (is_manager) is the only thing grantable here, handled inside
// RoleMembersPanel itself.
export default function LawyersPage() {
  return (
    <AppShell activeKey="lawyers">
      <RoleMembersPanel role="lawyer" inviteRole="lawyer" />
    </AppShell>
  )
}
