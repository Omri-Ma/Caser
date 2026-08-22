# CaseHub — Law Firm Multi-Tenant SaaS

A multi-tenant SaaS platform for law firms. Each law firm is a tenant with its own
subdomain, branding, and subscription plan.

> Status: scaffolding in progress (Phase 1). This README is updated progressively
> as features land, per project convention — not reconstructed at the end.

## Architecture

- **Backend**: FastAPI + SQLAlchemy + Alembic, MySQL (shared DB, row-level tenant
  isolation via `tenant_id` on every tenant-scoped table), Redis for caching.
- **Frontend**: two separate React (Vite) apps — `client/` (lawyer + client portal)
  and `admin/` (office manager + super admin CMS).
- **Tenancy**: identified by subdomain (`office1.lvh.me`), resolved by a FastAPI
  middleware/dependency that injects `tenant_id` into request state. Every
  tenant-scoped query goes through one reusable filtering dependency.
- **Auth**: JWT (access + refresh), bcrypt/argon2 password hashing, RBAC enforced
  server-side (frontend route guards are UX only).

See `/docs` for the ERD, OpenAPI export, and Postman collection (added as endpoints
stabilize).

## Install & run

_Coming as Phase 1 completes — will include Docker Compose instructions
(`docker-compose up`) and manual local setup for backend/frontend._

## Demo users

_Two seed users (one client, one admin) will be listed here once seeding is in place._

## Screenshots

_Added as UI screens are completed._
