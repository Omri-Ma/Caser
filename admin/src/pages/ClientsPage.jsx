import AppShell from '../components/AppShell'
import RoleMembersPanel from '../components/RoleMembersPanel'

// One of the two per-role member pages (CLAUDE.md's Members split) —
// clients only. Invitable directly (inviteRole="client").
export default function ClientsPage() {
  return (
    <AppShell activeKey="clients">
      <RoleMembersPanel role="client" inviteRole="client" />
    </AppShell>
  )
}
