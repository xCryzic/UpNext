import hmac
import json
import re
import secrets
import sqlite3
from base64 import b64encode
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, g, jsonify, redirect, request, session

from database import get_db
from helpers.auth import require_login
from services.rate_limit import rate_limit

socials_bp = Blueprint("socials", __name__)
PLATFORMS = {"Instagram", "TikTok", "YouTube", "GitHub", "Spotify", "X", "Twitch", "Behance", "Dribbble", "LinkedIn", "Website/Portfolio"}
URL_PATTERN = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
OAUTH_SESSION_KEYS = ("github_oauth_state", "github_oauth_social_id", "github_oauth_claimed_login", "github_oauth_user_id")
SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_PROFILE_URL = "https://api.spotify.com/v1/me"
SPOTIFY_OAUTH_SESSION_KEYS = ("spotify_oauth_state", "spotify_oauth_social_id")


def owned_creator(connection):
    return connection.execute("SELECT id FROM creators WHERE user_id = ?", (g.user_id,)).fetchone()


def serialize_social(row):
    keys = ("id", "platform", "username", "profile_url", "follower_count", "ownership_verified", "eligibility_verified", "verification_status", "verified_at", "last_checked_at", "created_at", "updated_at")
    return {key: row[key] for key in keys}


def social_by_id(connection, social_id):
    return connection.execute("SELECT * FROM social_accounts WHERE id = ?", (social_id,)).fetchone()


def clear_oauth_context():
    for key in OAUTH_SESSION_KEYS:
        session.pop(key, None)


def clear_spotify_oauth_context():
    for key in SPOTIFY_OAUTH_SESSION_KEYS:
        session.pop(key, None)


def oauth_redirect(result):
    provider = "spotify" if "/spotify/" in request.path else "github"
    return redirect(f"{current_app.config['FRONTEND_ORIGIN']}?{provider}_verification={result}")


def github_login_from_claim(username, profile_url):
    """Return a normalized login only for a GitHub profile root URL matching username."""
    try:
        parsed = urlparse(profile_url.strip())
    except (AttributeError, ValueError):
        return None
    if parsed.scheme.lower() not in {"http", "https"} or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    url_login = parts[0].strip() if len(parts) == 1 and not parsed.params and not parsed.query and not parsed.fragment else ""
    claimed_login = str(username or "").strip()
    if not url_login or not claimed_login or url_login.casefold() != claimed_login.casefold():
        return None
    return url_login.casefold()


def spotify_user_id_from_claim(username, profile_url):
    """Accept only Spotify *user* profile URLs; artist/catalog URLs are not identities."""
    try:
        parsed = urlparse(profile_url.strip())
    except (AttributeError, ValueError):
        return None
    if parsed.scheme.lower() not in {"http", "https"} or parsed.netloc.lower() not in {"open.spotify.com", "www.open.spotify.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[0] != "user" or parsed.params or parsed.fragment:
        return None
    user_id = parts[1].strip()
    claimed_id = str(username or "").strip()
    if not user_id or not claimed_id or user_id != claimed_id:
        return None
    return user_id


def validate(data):
    platform = str(data.get("platform", "")).strip()
    username = str(data.get("username", "")).strip()
    profile_url = str(data.get("profile_url", "")).strip()
    if platform not in PLATFORMS or not username or not URL_PATTERN.fullmatch(profile_url):
        return None, "platform, username, and a valid http(s) profile_url are required."
    return (platform, username, profile_url), None


def get_owned_social(connection, social_id):
    return connection.execute("SELECT social_accounts.* FROM social_accounts JOIN creators ON creators.id = social_accounts.creator_id WHERE social_accounts.id = ? AND creators.user_id = ?", (social_id, g.user_id)).fetchone()


def github_token_exchange(code):
    payload = urlencode({"client_id": current_app.config["GITHUB_CLIENT_ID"], "client_secret": current_app.config["GITHUB_CLIENT_SECRET"], "code": code, "redirect_uri": current_app.config["GITHUB_OAUTH_CALLBACK_URL"]}).encode()
    outbound = Request(GITHUB_TOKEN_URL, data=payload, headers={"Accept": "application/json", "User-Agent": "UpNext-GitHub-Verification"}, method="POST")
    try:
        with urlopen(outbound, timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return result.get("access_token") if isinstance(result, dict) else None


def github_authenticated_user(access_token):
    outbound = Request(GITHUB_USER_URL, headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {access_token}", "User-Agent": "UpNext-GitHub-Verification"})
    try:
        with urlopen(outbound, timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return result if isinstance(result, dict) and result.get("login") and result.get("id") is not None else None


def spotify_token_exchange(code):
    credentials = b64encode(f"{current_app.config['SPOTIFY_CLIENT_ID']}:{current_app.config['SPOTIFY_CLIENT_SECRET']}".encode()).decode()
    payload = urlencode({"grant_type": "authorization_code", "code": code, "redirect_uri": current_app.config["SPOTIFY_OAUTH_CALLBACK_URL"]}).encode()
    outbound = Request(SPOTIFY_TOKEN_URL, data=payload, headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json", "User-Agent": "UpNext-Spotify-Verification"}, method="POST")
    try:
        with urlopen(outbound, timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return result.get("access_token") if isinstance(result, dict) else None


def spotify_authenticated_user(access_token):
    outbound = Request(SPOTIFY_PROFILE_URL, headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json", "User-Agent": "UpNext-Spotify-Verification"})
    try:
        with urlopen(outbound, timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return result if isinstance(result, dict) and result.get("id") and result.get("account_id") else None


@socials_bp.get("/api/creator/socials")
@require_login
def list_socials():
    connection = get_db()
    try:
        creator = owned_creator(connection)
        if not creator:
            return jsonify({"social_accounts": []})
        rows = connection.execute("SELECT * FROM social_accounts WHERE creator_id = ? ORDER BY id", (creator["id"],)).fetchall()
        return jsonify({"social_accounts": [serialize_social(row) for row in rows]})
    finally:
        connection.close()

@socials_bp.post("/api/creator/socials")
@require_login
def create_social():
    values, error = validate(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    connection = get_db()
    try:
        creator = owned_creator(connection)
        if not creator:
            return jsonify({"error": "Create a creator profile first."}), 400
        cursor = connection.execute("INSERT INTO social_accounts (creator_id, platform, username, profile_url) VALUES (?, ?, ?, ?)", (creator["id"], *values))
        connection.commit()
        return jsonify({"social_account": serialize_social(social_by_id(connection, cursor.lastrowid))}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Could not create social account."}), 409
    finally:
        connection.close()


@socials_bp.patch("/api/creator/socials/<int:social_id>")
@socials_bp.put("/api/creator/socials/<int:social_id>")
@require_login
def update_social(social_id):
    data = request.get_json(silent=True) or {}
    connection = get_db()
    try:
        row = get_owned_social(connection, social_id)
        if not row:
            return jsonify({"error": "Social account not found."}), 404
        updates = {field: str(data[field]).strip() for field in ("platform", "username", "profile_url") if field in data}
        if "platform" in updates and updates["platform"] not in PLATFORMS:
            return jsonify({"error": "Unsupported platform."}), 400
        if "profile_url" in updates and not URL_PATTERN.fullmatch(updates["profile_url"]):
            return jsonify({"error": "Invalid profile URL."}), 400
        if not updates:
            return jsonify({"error": "No editable fields provided."}), 400
        final_platform = updates.get("platform", row["platform"])
        final_username = updates.get("username", row["username"])
        final_url = updates.get("profile_url", row["profile_url"])
        original_identity = github_login_from_claim(row["username"], row["profile_url"]) if row["platform"] == "GitHub" else spotify_user_id_from_claim(row["username"], row["profile_url"]) if row["platform"] == "Spotify" else None
        final_identity = github_login_from_claim(final_username, final_url) if final_platform == "GitHub" else spotify_user_id_from_claim(final_username, final_url) if final_platform == "Spotify" else None
        identity_changed = row["platform"] in {"GitHub", "Spotify"} and (final_platform != row["platform"] or original_identity != final_identity)
        assignments = [f"{field} = ?" for field in updates]
        values = list(updates.values())
        if identity_changed:
            assignments.extend(["ownership_verified = 0", "verification_status = 'unverified'", "verified_at = NULL", "provider_account_id = NULL"])
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        connection.execute(f"UPDATE social_accounts SET {', '.join(assignments)} WHERE id = ?", [*values, social_id])
        connection.commit()
        return jsonify({"social_account": serialize_social(social_by_id(connection, social_id))})
    finally:
        connection.close()


@socials_bp.delete("/api/creator/socials/<int:social_id>")
@require_login
def delete_social(social_id):
    connection = get_db()
    try:
        if not get_owned_social(connection, social_id):
            return jsonify({"error": "Social account not found."}), 404
        connection.execute("DELETE FROM social_accounts WHERE id = ?", (social_id,))
        connection.commit()
        return jsonify({"status": "ok"})
    finally:
        connection.close()


@socials_bp.get("/api/creator/socials/<int:social_id>/verify/github")
@require_login
@rate_limit("RATE_LIMIT_OAUTH_PER_MINUTE", 10)
def start_github_verification(social_id):
    if not current_app.config.get("GITHUB_CLIENT_ID") or not current_app.config.get("GITHUB_CLIENT_SECRET") or not current_app.config.get("GITHUB_OAUTH_CALLBACK_URL"):
        return jsonify({"error": "GitHub verification is not configured."}), 503
    connection = get_db()
    try:
        social = get_owned_social(connection, social_id)
        if not social:
            return jsonify({"error": "Social account not found."}), 404
        if social["platform"] != "GitHub":
            return jsonify({"error": "GitHub verification is only available for GitHub accounts."}), 400
        claimed_login = github_login_from_claim(social["username"], social["profile_url"])
        if not claimed_login:
            return jsonify({"error": "Use a matching GitHub username and profile URL such as https://github.com/username before verifying."}), 400
        state = secrets.token_urlsafe(32)
        session["github_oauth_state"] = state
        session["github_oauth_social_id"] = social["id"]
        session["github_oauth_claimed_login"] = claimed_login
        session["github_oauth_user_id"] = g.user_id
        query = urlencode({"client_id": current_app.config["GITHUB_CLIENT_ID"], "redirect_uri": current_app.config["GITHUB_OAUTH_CALLBACK_URL"], "state": state, "scope": "read:user"})
        return redirect(f"{GITHUB_AUTHORIZE_URL}?{query}")
    finally:
        connection.close()


@socials_bp.get("/api/creator/socials/github/callback")
@require_login
def github_verification_callback():
    stored_state = session.get("github_oauth_state")
    stored_social_id = session.get("github_oauth_social_id")
    stored_claimed_login = session.get("github_oauth_claimed_login")
    stored_user_id = session.get("github_oauth_user_id")
    received_state = request.args.get("state", "")
    clear_oauth_context()
    if not stored_state or not received_state or not hmac.compare_digest(str(stored_state), received_state) or not stored_social_id or stored_user_id != g.user_id:
        return oauth_redirect("failed")
    if request.args.get("error"):
        return oauth_redirect("denied")
    code = request.args.get("code")
    if not code:
        return oauth_redirect("failed")
    access_token = github_token_exchange(code)
    github_user = github_authenticated_user(access_token) if access_token else None
    if not github_user or str(github_user["login"]).casefold() != str(stored_claimed_login).casefold():
        return oauth_redirect("failed")
    connection = get_db()
    try:
        social = get_owned_social(connection, int(stored_social_id))
        if not social or social["platform"] != "GitHub" or github_login_from_claim(social["username"], social["profile_url"]) != stored_claimed_login:
            return oauth_redirect("failed")
        connection.execute("UPDATE social_accounts SET ownership_verified = 1, verification_status = 'verified', verified_at = ?, provider_account_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (datetime.now(timezone.utc).isoformat(), str(github_user["id"]), social["id"]))
        connection.commit()
        return oauth_redirect("success")
    finally:
        connection.close()


@socials_bp.get("/api/creator/socials/<int:social_id>/verify/spotify")
@require_login
@rate_limit("RATE_LIMIT_OAUTH_PER_MINUTE", 10)
def start_spotify_verification(social_id):
    if not current_app.config.get("SPOTIFY_CLIENT_ID") or not current_app.config.get("SPOTIFY_CLIENT_SECRET") or not current_app.config.get("SPOTIFY_OAUTH_CALLBACK_URL"):
        return jsonify({"error": "Spotify verification is not configured."}), 503
    connection = get_db()
    try:
        social = get_owned_social(connection, social_id)
        if not social:
            return jsonify({"error": "Social account not found."}), 404
        if social["platform"] != "Spotify":
            return jsonify({"error": "Spotify verification is only available for Spotify user accounts."}), 400
        claimed_user_id = spotify_user_id_from_claim(social["username"], social["profile_url"])
        if not claimed_user_id:
            return jsonify({"error": "Use a matching Spotify user ID and user URL such as https://open.spotify.com/user/your-user-id before verifying. Artist and catalog URLs cannot be verified here."}), 400
        state = secrets.token_urlsafe(32)
        # The session records the active flow. The database attempt also bridges Spotify's required 127.0.0.1 callback host.
        session["spotify_oauth_state"] = state
        session["spotify_oauth_social_id"] = social["id"]
        connection.execute("DELETE FROM spotify_oauth_attempts WHERE social_id = ?", (social["id"],))
        connection.execute("INSERT INTO spotify_oauth_attempts (state, social_id, user_id, claimed_user_id) VALUES (?, ?, ?, ?)", (state, social["id"], g.user_id, claimed_user_id))
        connection.commit()
        query = urlencode({"client_id": current_app.config["SPOTIFY_CLIENT_ID"], "response_type": "code", "redirect_uri": current_app.config["SPOTIFY_OAUTH_CALLBACK_URL"], "state": state, "scope": "user-read-private"})
        return redirect(f"{SPOTIFY_AUTHORIZE_URL}?{query}")
    finally:
        connection.close()


@socials_bp.get("/api/creator/socials/spotify/callback")
def spotify_verification_callback():
    received_state = request.args.get("state", "")
    clear_spotify_oauth_context()
    if not received_state:
        return oauth_redirect("failed")
    connection = get_db()
    try:
        attempt = connection.execute("SELECT * FROM spotify_oauth_attempts WHERE state = ?", (received_state,)).fetchone()
        # Consume a valid attempt before exchanging a code: no OAuth state is reusable.
        if attempt:
            connection.execute("DELETE FROM spotify_oauth_attempts WHERE state = ?", (received_state,))
            connection.commit()
        if not attempt or not hmac.compare_digest(str(attempt["state"]), received_state):
            return oauth_redirect("failed")
        if request.args.get("error"):
            return oauth_redirect("denied")
        code = request.args.get("code")
        if not code:
            return oauth_redirect("failed")
        access_token = spotify_token_exchange(code)
        spotify_user = spotify_authenticated_user(access_token) if access_token else None
        if not spotify_user or str(spotify_user["id"]) != attempt["claimed_user_id"]:
            return oauth_redirect("failed")
        social = connection.execute("SELECT social_accounts.* FROM social_accounts JOIN creators ON creators.id = social_accounts.creator_id WHERE social_accounts.id = ? AND creators.user_id = ?", (attempt["social_id"], attempt["user_id"])).fetchone()
        if not social or social["platform"] != "Spotify" or spotify_user_id_from_claim(social["username"], social["profile_url"]) != attempt["claimed_user_id"]:
            return oauth_redirect("failed")
        connection.execute("UPDATE social_accounts SET ownership_verified = 1, verification_status = 'verified', verified_at = ?, provider_account_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (datetime.now(timezone.utc).isoformat(), str(spotify_user["account_id"]), social["id"]))
        connection.commit()
        return oauth_redirect("success")
    finally:
        connection.close()
