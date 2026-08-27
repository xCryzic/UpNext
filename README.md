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

Social verification is intentionally not faked. Accounts are stored as unverified until a future trusted, platform-authorized provider updates verification fields. UpNext does not store external platform passwords, scrape platforms, or include likes, follows, feeds, messaging, or monetization in V0.

Privacy, terms, community guidelines, reporting, and account deletion documents remain launch placeholders and require proper review before public release.
