# UpNext

UpNext is a work-first discovery directory for emerging creators and developers. It is not a social feed: V0 focuses on profiles, projects, external work links, search, and moderation signals.

## Local development

Frontend:

```text
npm install
npm run dev
```

Copy `.env.example` to `.env` first if you need to override the API URL. The default is `http://localhost:5000`.

Backend, from `backend/`:

```text
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The backend runs at `http://localhost:5000` (it also listens on `127.0.0.1`), and Vite runs at `http://localhost:5173`. Use `localhost` for both during HTTP development: mixing it with `127.0.0.1` can prevent the Flask `SameSite=Lax` session cookie from being sent. Backend configuration is read from `backend/.env`; SQLite defaults to the canonical `backend/data/upnext.db`. Relative `DATABASE_PATH` values are resolved from `backend/`, so use `data/upnext.db`; absolute paths remain supported. Database initialization is additive and does not require deleting the existing database. The repository-root `data/upnext.db` is a legacy artifact and is not read by the application; it is preserved rather than merged or removed automatically.

### GitHub ownership verification (local)

GitHub ownership verification uses the official OAuth web flow only for a creator's existing GitHub social account. It confirms account ownership; it does **not** check follower counts or eligibility.

1. Create an OAuth App in GitHub's developer settings.
2. Set its authorization callback URL exactly to `http://localhost:5000/api/creator/socials/github/callback`.
3. Copy `backend/.env.example` to `backend/.env` and set `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `GITHUB_OAUTH_CALLBACK_URL` to that same callback URL.
4. Restart the Flask server, add a GitHub social whose handle matches its profile URL (for example `maker` and `https://github.com/maker`), then choose **Verify with GitHub** from profile management.

The token is exchanged and used only by the backend to call GitHub's authenticated-user endpoint. It is never sent to the browser or stored in SQLite.

### Spotify ownership verification (local)

Spotify verification proves ownership of a Spotify **user account** only. It does not verify ownership of an artist profile and does not fetch followers, music, listening activity, or playlists.

1. Create an app in the Spotify Developer Dashboard and add this exact Redirect URI: `http://127.0.0.1:5000/api/creator/socials/spotify/callback`.
2. In `backend/.env`, set `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_OAUTH_CALLBACK_URL` to that exact value.
3. Add a Spotify social using the Spotify user ID for both the handle and a URL in the form `https://open.spotify.com/user/<user-id>`.
4. Choose **Verify with Spotify** from profile management.

UpNext requests only Spotify's `user-read-private` scope to call the current-user profile endpoint. The backend uses the temporary token once, stores the returned immutable `account_id` for the verified link, and discards access and refresh tokens. Spotify requires the explicit `127.0.0.1` loopback callback; do not substitute `localhost`.

Run backend tests with:

```text
python -m unittest discover -s tests -v
```

## API overview

- Auth: `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- Creator profile: `GET /api/creator/me`, `POST/PATCH/DELETE /api/creator`, `GET /api/creator/status`
- Public discovery: `GET /api/creators`, `GET /api/creators/<username>`
- Owned work: `/api/creator/socials` and `/api/creator/projects`
- Reports: `POST /api/reports`
- Health: `GET /api/health`

GitHub and Spotify user-account ownership verification are implemented through OAuth. YouTube may be linked as an ordinary social account but is not verified in V1. Spotify artist ownership, follower-count eligibility, and all other eligibility checks remain unimplemented. UpNext does not store external platform passwords, scrape platforms, or include likes, follows, feeds, messaging, or monetization in V0.

## Production / Railway

UpNext can run as one service: build the Vite frontend, then let Flask serve `dist/` and the API. Do not use Flask's development server in production.

```text
# Build command (repository root)
npm ci && npm run build

# Start command (Railway)
gunicorn --chdir backend --workers 1 --bind 0.0.0.0:$PORT app:app
```

Set `APP_ENV=production` and configure a Railway persistent volume mounted at `/data`. The database setting must be an absolute persistent-volume path: `DATABASE_PATH=/data/upnext.db`. Startup logs the resolved database path without logging credentials. Relative database paths are rejected in production so a deploy cannot silently create an ephemeral SQLite database. Keep this SQLite V1 to one Gunicorn worker unless you deliberately plan and test a different concurrency strategy.

Required production variables are:

```text
APP_ENV=production
SECRET_KEY=<long random value>
DATABASE_PATH=/data/upnext.db
FRONTEND_URL=https://<your-domain>
ADMIN_EMAILS=owner@example.com
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_OAUTH_CALLBACK_URL=https://<your-domain>/api/creator/socials/github/callback
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_OAUTH_CALLBACK_URL=https://<your-domain>/api/creator/socials/spotify/callback
```

Set the GitHub and Spotify OAuth App callback URLs to the matching production URLs above. In production, session cookies are `HttpOnly`, `Secure`, and `SameSite=Lax`; the frontend origin is the only CORS origin allowed when CORS is needed. The app uses modest in-memory, per-process rate limits for login, signup, reports, and OAuth starts. This is suitable for a small V1 but is not shared across multiple server processes.

Create a consistent SQLite backup using SQLite's backup API (not a raw file copy while the app is running):

```text
python backend/scripts/backup_sqlite.py /data/upnext.db /data/backups
```

## Public pages and moderation

The app includes concise `/privacy`, `/terms`, and `/community-guidelines` pages. They describe the data the product actually uses, including account data, profiles, projects, linked socials, account-ownership verification state, reports, and necessary session/security data. They are product notices, not legal advice; have counsel review them before launch.

Authenticated creators can unpublish a profile without deleting their account. Public discovery and public profile endpoints require both a publishable profile and public visibility. Account deletion permanently removes the user's account and its related creator data in a database transaction, then clears the session.

Set `ADMIN_EMAILS` to a comma-separated set of owner email addresses to access the minimal moderation API. Admins can list reports, set `open`, `dismissed`, or `actioned`, and hide or restore a publishable profile. Ownership verification never prevents reporting or moderation action.
