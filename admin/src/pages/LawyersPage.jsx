import AppShell from '../components/AppShell'
import RoleMembersPanel from '../components/RoleMembersPanel'

// One of the three per-role member pages (CLAUDE.md's Members split) —
// lawyers only. Invitable directly (inviteRole="lawyer"), and promotable
// to office_manager per row (toggleToRole="office_manager") — CLAUDE.md's
// Memberships note: office_manager can promote a lawyer, never a client.
export default function LawyersPage() {
  return (
    <AppShell activeKey="lawyers">
      <RoleMembersPanel
        role="lawyer"
        inviteRole="lawyer"
        toggleToRole="office_manager"
        toggleLabel="קידום למנהל/ת"
      />
    </AppShell>
  )
}
