# Local Organization Auth Testing

This guide verifies the real shared-organization workspace flow on a local machine using:

- local frontend
- local backend
- Supabase Auth
- Postgres/Supabase-backed organization data

## Required Environment

Backend [backend/.env](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/.env):

```env
APP_ENV=development
LOG_LEVEL=INFO
API_PORT=8000
ALLOWED_ORIGINS_RAW=http://localhost:3000
REQUIRE_AUTH=true
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
RUN_DB_MIGRATIONS_ON_STARTUP=false
```

Frontend [frontend/.env.local](/Users/aravindbandipelli/Desktop/AravindCode-bot/frontend/.env.local):

```env
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
```

## Startup Commands

Run the backend:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
./.venv/bin/alembic -c alembic.ini upgrade head
set -a && source .env && set +a && ./scripts/start_backend.sh
```

Run the frontend:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/frontend
set -a && source .env.local && set +a && npm run dev:local
```

Optional local readiness check:

```bash
cd /Users/aravindbandipelli/Desktop/AravindCode-bot/backend
./.venv/bin/python scripts/local_auth_doctor.py
```

The doctor script automatically reads:

- [backend/.env](/Users/aravindbandipelli/Desktop/AravindCode-bot/backend/.env)
- [frontend/.env.local](/Users/aravindbandipelli/Desktop/AravindCode-bot/frontend/.env.local)

and reports whether the local database, backend health endpoint, and Supabase env vars are ready for auth testing.

## Local URLs

- frontend: [http://127.0.0.1:3000/login](http://127.0.0.1:3000/login)
- backend: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Test Scenario A: First User Creates C3U

1. Open the local login page.
2. Create a new user with:
   - full name
   - personal email
   - password
   - organization name `C3U`
3. Sign in if email confirmation is enabled.
4. Confirm the app redirects to `/documents`.
5. Upload a document.
6. Confirm the sidebar shows:
   - user name
   - organization name `C3U`
7. Confirm `/documents` shows the uploaded file.

Expected:

- one new `organizations` row for slug `c3u`
- one `organization_members` row linking the new user to that organization
- first member role is `admin`
- uploaded documents are visible to the creator in `/documents`

## Test Scenario B: Second User Joins Existing C3U

1. Open an incognito window.
2. Create a second user with:
   - different full name
   - different email
   - different password
   - organization name `C3U`
3. Sign in.
4. Open `/documents`.
5. Confirm the second user sees the file uploaded by User 1.
6. Open `/search`.
7. Ask a question that should retrieve from the uploaded document.

Expected:

- no second `organizations` row for C3U
- second user gets an `organization_members` row for the same org
- second user role is `member`
- second user can view and search the same organization documents
- citations only reference documents from the shared `C3U` organization

## Test Scenario B2: Case/Whitespace Normalization

Repeat the same flow with a third user using organization name:

- `c3u`
- or ` C3U `

Expected:

- still maps to the same organization row
- still sees the same organization files

## Test Scenario C: Different Organization Isolation

1. Open another incognito window.
2. Create a third user in a different organization, for example `Northwind`.
3. Sign in.
4. Open `/documents`.
5. Open `/search`.

Expected:

- `/documents` does not show C3U files
- search results do not cite or retrieve C3U content
- organization label shows `Northwind`
- sidebar still shows the signed-in user name and organization name correctly

## SQL Verification

Check organization rows:

```sql
select id, name, slug, created_at
from public.organizations
order by created_at desc;
```

Check memberships:

```sql
select organization_id, user_id, role, joined_at
from public.organization_members
order by joined_at desc;
```

Check documents by organization:

```sql
select organization_id, original_name, user_id, status, created_at
from public.documents
order by created_at desc;
```

Check that `C3U`, `c3u`, and ` C3U ` all map to one row:

```sql
select id, name, slug
from public.organizations
where slug = 'c3u';
```

## Expected Product Behavior

- same organization name joins the same shared workspace
- same-org users can see the same uploaded files
- same-org users can search the same organization documents
- different-org users cannot see or retrieve those documents
- chat history remains per-user within the shared organization

## Debug Tips

- Backend health:

```bash
curl -sS http://127.0.0.1:8000/api/health
```

- Frontend login page:

```bash
curl -I http://127.0.0.1:3000/login
```

- If `/documents` fails after login:
  - confirm the backend is on the latest migration
  - confirm `DATABASE_URL` points to the database you expect
  - confirm Supabase auth env vars are set on both frontend and backend
