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

The backend runs at `http://localhost:5000` (it also listens on `127.0.0.1`), and Vite runs at `http://localhost:5173`. Use `localhost` for both during HTTP development: mixing it with `127.0.0.1` can prevent the Flask `SameSite=Lax` session cookie from being sent. Backend configuration is read from `backend/.env`; SQLite defaults to the canonical `backend/data/upnext.db`. Database initialization is additive and does not require deleting the existing database. The repository-root `data/upnext.db` is a legacy artifact and is not read by the application; it is preserved rather than merged or removed automatically.

### GitHub ownership verification (local)

GitHub ownership verification uses the official OAuth web flow only for a creator's existing GitHub social account. It confirms account ownership; it does **not** check follower counts or eligibility.

1. Create an OAuth App in GitHub's developer settings.
2. Set its authorization callback URL exactly to `http://localhost:5000/api/creator/socials/github/callback`.
3. Copy `backend/.env.example` to `backend/.env` and set `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `GITHUB_OAUTH_CALLBACK_URL` to that same callback URL.
4. Restart the Flask server, add a GitHub social whose handle matches its profile URL (for example `maker` and `https://github.com/maker`), then choose **Verify with GitHub** from profile management.

The token is exchanged and used only by the backend to call GitHub's authenticated-user endpoint. It is never sent to the browser or stored in SQLite.

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

GitHub account ownership verification is implemented through OAuth. Other platforms, GitHub follower-count eligibility, and all other eligibility checks remain unimplemented. UpNext does not store external platform passwords, scrape platforms, or include likes, follows, feeds, messaging, or monetization in V0.

Privacy, terms, community guidelines, reporting, and account deletion documents remain launch placeholders and require proper review before public release.
