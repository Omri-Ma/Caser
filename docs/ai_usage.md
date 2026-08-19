# AI Usage Log

Logged as work happens, per project convention — not reconstructed retroactively.

## 2026-08-19

**Asked**: Read and analyze CLAUDE.md, recommend how to work and how to start.

**Changed**:
- Initialized git repo.
- Created folder structure: `client/`, `admin/`, `server/{routers,schemas,services,models,deps,core,tests}/`,
  `db/migrations/versions/`, `docs/`.
- Added `.gitignore`, `.env.example` (DB/Redis/JWT/CORS/storage/base-domain vars),
  root `README.md` skeleton.

**Learned / decided**:
- Frontend: plain React (Vite), not Next.js — the app is login-gated/users-only
  with no public/SEO pages, so Next's SSR/server layer would add a second runtime
  server for no benefit and cut against the doc's "REST only, no server-side
  rendering" rule.
- Tooling: npm + pip/venv over pnpm/Poetry — doc doesn't mandate either, npm/pip
  need nothing extra installed.
- Local machine is missing a real Python install (only the Windows Store stub
  alias is on PATH) and Docker — both needed before Phase 1 steps 2 (docker-compose)
  and 4 (running FastAPI) can actually be executed/tested, not just written.
