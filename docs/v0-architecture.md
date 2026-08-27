# UpNext V0 architecture (legacy future-state reference)

> The running application uses Flask and SQLite under `backend/`. This document and `db/schema.sql` describe an earlier PostgreSQL-oriented future design; neither is used at runtime.

## Assessment and choice

The repository was empty. V0 uses React, TypeScript and Vite for a fast, portable public UI. Plain CSS keeps the visual system light and easy to replace. PostgreSQL is the proposed production datastore; `db/schema.sql` is intentionally database-agnostic and can later be adopted by Prisma, Drizzle, or the deployment's migration system.

## Boundaries

- `src/domain`: product types shared by UI and future APIs.
- `src/data`: explicitly fictional demo data only.
- `src/services/discovery`: replaceable discovery/search adapter. It currently searches in memory.
- `src/services/auth`: provider boundary, presently unconfigured.
- `src/services/verification`: provider boundary that always returns unverified until a platform-authorized integration is configured.
- `db/schema.sql`: production relational model. Internal users/profiles and public external accounts are separate.

## Schema notes

The SQL schema covers User, CreatorProfile, SocialAccount, Project and Report. Foreign keys cascade from a creator profile to its public data. Username and account uniqueness constraints prevent collisions; category and report indexes serve V0 browsing/moderation. Search can start with PostgreSQL full-text/trigram indexes, then swap the discovery service adapter for a dedicated engine without changing UI calls.

Eligibility is time-bound. A provider may record `follower_count_at_verification`, `verified_at`, and its name only after an authorized check. The product should show “Verified under [threshold] on [date]”, never a permanent current-follower assertion. Configure the threshold (initially 10,000) on the server, not in a client.

## Discovery ranking

`discover` is deterministic and deliberately excludes followers: profile completeness is weighted first, then a small stable recency rotation. Other options are newest and profile depth. This should be documented in product copy and audited as the catalog grows.

## Incremental implementation plan

1. **Foundation (complete):** TypeScript app shell, domain types, database schema, service boundaries, demo discovery UI.
2. Connect a database and migration runner; move demo records to a clearly scoped development seed script.
3. Add authentication through the `AuthProvider` boundary and protected profile editing.
4. Add server-side discovery API/search and real profile routes.
5. Implement an authorized verification provider, explicit verification lifecycle, and threshold configuration.
6. Add a rate-limited report endpoint and a private review queue.
7. Add deletion/export workflows, legal copy reviewed by counsel, accessibility testing, and deployment hardening.

## Risks and safeguards

- Do not scrape accounts or ask for external passwords. Use platform-approved OAuth/API or ownership proofs only.
- Verification is not a safety guarantee. Record provider/audit details privately, show limited public status, and plan reassessment/expiry.
- Minimize personal data: location is optional, no birth-date collection, and never expose email/auth identifiers.
- Reporting can be abused; require authentication or other anti-abuse controls, rate limits, restricted staff access, and retention rules.
- Privacy Policy, Terms, Community Guidelines, reporting process, and deletion process are placeholders—not legal claims—and require review before public launch.

## Backend V0 implementation

The Flask backend lives under `backend/` and keeps the existing session auth endpoints intact. Route modules are split into `routes/auth.py`, `routes/creators.py`, `routes/socials.py`, `routes/projects.py`, and `routes/reports.py`; ownership checks are shared in `helpers/auth.py`, and discovery scoring is isolated in `services/discovery_service.py`.

The SQLite initializer is migration-style and additive. It uses `CREATE TABLE IF NOT EXISTS`, checks existing columns with `PRAGMA table_info`, and applies only missing columns/indexes. It does not delete or recreate `backend/data/upnext.db`. Legacy creator records receive empty timestamp defaults and remain private to discovery until they satisfy publishability requirements.

Public discovery only includes publishable profiles: a profile, display name, username, bio, category, skill, project, and social account are required. Ranking uses search/category relevance, profile completeness, and recency. Follower counts are never accepted as client-supplied verification and are only exposed when a trusted server-side process has marked eligibility verified.

Run locally from `backend/`:

```text
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
python -m unittest discover -s tests -v
```

The API listens on `http://127.0.0.1:5000`; the frontend origin is configured by `FRONTEND_ORIGIN`. Set `DATABASE_PATH` to move SQLite, `SESSION_COOKIE_SECURE=1` in a production configuration, and leave `EXPOSE_DB_INFO=0` unless the restricted development endpoint is explicitly needed.
