import AppShell from '../components/AppShell'
import RoleMembersPanel from '../components/RoleMembersPanel'

// One of the three per-role member pages (CLAUDE.md's Members split) —
// office_managers only. No inviteRole: an office_manager is never invited
// directly, only ever created by promoting an existing lawyer (see
// LawyersPage) — CLAUDE.md's Memberships note. Surfaces the demote action
// (toggleToRole="lawyer") per row instead. The pending tab is always empty
// here by design (invites are only ever lawyer/client), kept for the same
// consistent active/pending/removed shape every role page has.
export default function AdminsPage() {
  return (
    <AppShell activeKey="admins">
      <RoleMembersPanel
        role="office_manager"
        toggleToRole="lawyer"
        toggleLabel="הורדה לעו״ד"
        noInviteHint="מנהל/ת משרד לא מוזמנ/ת ישירות — קדמו עורך/ת דין קיים/ת מעמוד עורכי הדין."
      />
    </AppShell>
  )
}
