-- CaseHub seed data.
--
-- Currently just the one super_admin bootstrap account (see CLAUDE.md's
-- Multi-tenancy architecture): no route ever creates or promotes a
-- super_admin, so the first one has to be a fixed row here. This is
-- infrastructure, not one of the two required demo users (a client and an
-- office_manager) — those get seeded once Phase 2's office-manager/lawyer
-- vertical slices exist to attach them to a real tenant.
--
-- Logs in at the fixed platform address (platform.<BASE_DOMAIN>, e.g.
-- platform.lvh.me locally) via admin_api's POST /auth/platform-login, never
-- through a tenant subdomain. Demo credentials:
--   email:    super@casehub.example.com
--   password: SuperAdmin123!

INSERT INTO `identities` (`name`, `email`, `password_hash`, `is_super_admin`, `token_version`)
VALUES ('CaseHub Platform', 'super@casehub.example.com', '$2b$12$TpdDukTokhNQO5.FqX0oN.SfB0AdAFVsz/pJGGsH6Hhn8MictIIaW', 1, 0);

-- The two required demo users (README/PDF pair: one client, one
-- office_manager), attached to a dedicated demo tenant so they always work
-- regardless of whatever tenants get created ad hoc during manual testing.
-- Both log in through client_api/admin_api at demo.<BASE_DOMAIN> (e.g.
-- demo.lvh.me locally). Demo credentials:
--   office_manager: office_manager@casehub.example.com / OfficeManager123!
--   client:         client@casehub.example.com / Client123!

INSERT INTO `tenants` (`name`, `subdomain`, `active`)
VALUES ('Demo Firm', 'demo', 1);

INSERT INTO `subscriptions` (`tenant_id`, `plan`, `start_date`, `active`)
VALUES ((SELECT id FROM `tenants` WHERE `subdomain` = 'demo'), 'FREE', CURDATE(), 1);

INSERT INTO `identities` (`name`, `email`, `password_hash`, `is_super_admin`, `token_version`)
VALUES ('Noa Manager', 'office_manager@casehub.example.com', '$2b$12$6Heq4eXhPDuPoTzUA4/GvuZKQB7tyWUAGxWPjPW6Y3lUwn5YKy1ym', 0, 0);

INSERT INTO `identities` (`name`, `email`, `password_hash`, `is_super_admin`, `token_version`)
VALUES ('Dor Client', 'client@casehub.example.com', '$2b$12$UXr596NctaimScUXL7F.h.vhr/TVTxQggE9lnhR.T1XmFBk7iB0pm', 0, 0);

INSERT INTO `memberships` (`identity_id`, `tenant_id`, `role`, `show_on_public_page`, `active`)
VALUES (
  (SELECT id FROM `identities` WHERE `email` = 'office_manager@casehub.example.com'),
  (SELECT id FROM `tenants` WHERE `subdomain` = 'demo'),
  'OFFICE_MANAGER', 1, 1
);

INSERT INTO `memberships` (`identity_id`, `tenant_id`, `role`, `show_on_public_page`, `active`)
VALUES (
  (SELECT id FROM `identities` WHERE `email` = 'client@casehub.example.com'),
  (SELECT id FROM `tenants` WHERE `subdomain` = 'demo'),
  'CLIENT', 0, 1
);
