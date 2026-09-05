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
