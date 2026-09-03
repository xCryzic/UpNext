import hmac
import json
import re
import secrets
from base64 import b64encode
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, g, jsonify, redirect, request, session

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from database import sqlalchemy_session
from models import Creator, SocialAccount, SpotifyOAuthAttempt
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
    return connection.scalar(select(Creator).where(Creator.user_id == g.user_id))


def serialize_social(row):
    return {"id": row.id, "platform": row.platform, "username": row.username, "profile_url": row.profile_url, "follower_count": row.follower_count, "ownership_verified": bool(row.ownership_verified), "eligibility_verified": bool(row.eligibility_verified), "verification_status": row.verification_status, "verified_at": row.verified_at.isoformat() if row.verified_at else None, "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None, "created_at": row.created_at.isoformat() if row.created_at else None, "updated_at": row.updated_at.isoformat() if row.updated_at else None}


def social_by_id(connection, social_id):
    return connection.get(SocialAccount, social_id)


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
    return connection.scalar(select(SocialAccount).join(Creator, SocialAccount.creator_id == Creator.id).where(SocialAccount.id == social_id, Creator.user_id == g.user_id))


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
    connection = sqlalchemy_session()
    try:
        creator = owned_creator(connection)
        if not creator:
            return jsonify({"social_accounts": []})
        rows = connection.scalars(select(SocialAccount).where(SocialAccount.creator_id == creator.id).order_by(SocialAccount.id)).all()
        return jsonify({"social_accounts": [serialize_social(row) for row in rows]})
    finally: pass

@socials_bp.post("/api/creator/socials")
@require_login
def create_social():
    values, error = validate(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    connection = sqlalchemy_session()
    try:
        creator = owned_creator(connection)
        if not creator:
            return jsonify({"error": "Create a creator profile first."}), 400
        social = SocialAccount(creator_id=creator.id, platform=values[0], username=values[1], profile_url=values[2])
        connection.add(social)
        connection.commit()
        return jsonify({"social_account": serialize_social(social)}), 201
    except IntegrityError:
        connection.rollback()
        return jsonify({"error": "Could not create social account."}), 409
    finally: pass


@socials_bp.patch("/api/creator/socials/<int:social_id>")
@socials_bp.put("/api/creator/socials/<int:social_id>")
@require_login
def update_social(social_id):
    data = request.get_json(silent=True) or {}
    connection = sqlalchemy_session()
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
        final_platform = updates.get("platform", row.platform)
        final_username = updates.get("username", row.username)
        final_url = updates.get("profile_url", row.profile_url)
        original_identity = github_login_from_claim(row.username, row.profile_url) if row.platform == "GitHub" else spotify_user_id_from_claim(row.username, row.profile_url) if row.platform == "Spotify" else None
        final_identity = github_login_from_claim(final_username, final_url) if final_platform == "GitHub" else spotify_user_id_from_claim(final_username, final_url) if final_platform == "Spotify" else None
        identity_changed = row.platform in {"GitHub", "Spotify"} and (final_platform != row.platform or original_identity != final_identity)
        for field, value in updates.items(): setattr(row, field, value)
        if identity_changed:
            row.ownership_verified = False; row.verification_status = "unverified"; row.verified_at = None; row.provider_account_id = None
        connection.commit()
        return jsonify({"social_account": serialize_social(social_by_id(connection, social_id))})
    finally: pass


@socials_bp.delete("/api/creator/socials/<int:social_id>")
@require_login
def delete_social(social_id):
    connection = sqlalchemy_session()
    try:
        if not get_owned_social(connection, social_id):
            return jsonify({"error": "Social account not found."}), 404
        connection.delete(get_owned_social(connection, social_id))
        connection.commit()
        return jsonify({"status": "ok"})
    finally: pass


@socials_bp.get("/api/creator/socials/<int:social_id>/verify/github")
@require_login
@rate_limit("RATE_LIMIT_OAUTH_PER_MINUTE", 10)
def start_github_verification(social_id):
    if not current_app.config.get("GITHUB_CLIENT_ID") or not current_app.config.get("GITHUB_CLIENT_SECRET") or not current_app.config.get("GITHUB_OAUTH_CALLBACK_URL"):
        return jsonify({"error": "GitHub verification is not configured."}), 503
    connection = sqlalchemy_session()
    try:
        social = get_owned_social(connection, social_id)
        if not social:
            return jsonify({"error": "Social account not found."}), 404
        if social.platform != "GitHub":
            return jsonify({"error": "GitHub verification is only available for GitHub accounts."}), 400
        claimed_login = github_login_from_claim(social.username, social.profile_url)
        if not claimed_login:
            return jsonify({"error": "Use a matching GitHub username and profile URL such as https://github.com/username before verifying."}), 400
        state = secrets.token_urlsafe(32)
        session["github_oauth_state"] = state
        session["github_oauth_social_id"] = social.id
        session["github_oauth_claimed_login"] = claimed_login
        session["github_oauth_user_id"] = g.user_id
        query = urlencode({"client_id": current_app.config["GITHUB_CLIENT_ID"], "redirect_uri": current_app.config["GITHUB_OAUTH_CALLBACK_URL"], "state": state, "scope": "read:user"})
        return redirect(f"{GITHUB_AUTHORIZE_URL}?{query}")
    finally: pass


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
    connection = sqlalchemy_session()
    try:
        social = get_owned_social(connection, int(stored_social_id))
        if not social or social.platform != "GitHub" or github_login_from_claim(social.username, social.profile_url) != stored_claimed_login:
            return oauth_redirect("failed")
        social.ownership_verified = True; social.verification_status = "verified"; social.verified_at = datetime.now(timezone.utc); social.provider_account_id = str(github_user["id"])
        connection.commit()
        return oauth_redirect("success")
    finally: pass


@socials_bp.get("/api/creator/socials/<int:social_id>/verify/spotify")
@require_login
@rate_limit("RATE_LIMIT_OAUTH_PER_MINUTE", 10)
def start_spotify_verification(social_id):
    if not current_app.config.get("SPOTIFY_CLIENT_ID") or not current_app.config.get("SPOTIFY_CLIENT_SECRET") or not current_app.config.get("SPOTIFY_OAUTH_CALLBACK_URL"):
        return jsonify({"error": "Spotify verification is not configured."}), 503
    connection = sqlalchemy_session()
    try:
        social = get_owned_social(connection, social_id)
        if not social:
            return jsonify({"error": "Social account not found."}), 404
        if social.platform != "Spotify":
            return jsonify({"error": "Spotify verification is only available for Spotify user accounts."}), 400
        claimed_user_id = spotify_user_id_from_claim(social.username, social.profile_url)
        if not claimed_user_id:
            return jsonify({"error": "Use a matching Spotify user ID and user URL such as https://open.spotify.com/user/your-user-id before verifying. Artist and catalog URLs cannot be verified here."}), 400
        state = secrets.token_urlsafe(32)
        # The session records the active flow. The database attempt also bridges Spotify's required 127.0.0.1 callback host.
        session["spotify_oauth_state"] = state
        session["spotify_oauth_social_id"] = social.id
        connection.execute(delete(SpotifyOAuthAttempt).where(SpotifyOAuthAttempt.social_id == social.id))
        connection.add(SpotifyOAuthAttempt(state=state, social_id=social.id, user_id=g.user_id, claimed_user_id=claimed_user_id))
        connection.commit()
        query = urlencode({"client_id": current_app.config["SPOTIFY_CLIENT_ID"], "response_type": "code", "redirect_uri": current_app.config["SPOTIFY_OAUTH_CALLBACK_URL"], "state": state, "scope": "user-read-private"})
        return redirect(f"{SPOTIFY_AUTHORIZE_URL}?{query}")
    finally: pass


@socials_bp.get("/api/creator/socials/spotify/callback")
def spotify_verification_callback():
    received_state = request.args.get("state", "")
    clear_spotify_oauth_context()
    if not received_state:
        return oauth_redirect("failed")
    connection = sqlalchemy_session()
    try:
        attempt = connection.get(SpotifyOAuthAttempt, received_state)
        # Consume a valid attempt before exchanging a code: no OAuth state is reusable.
        if attempt:
            connection.delete(attempt)
            connection.commit()
        if not attempt or not hmac.compare_digest(str(attempt.state), received_state):
            return oauth_redirect("failed")
        if request.args.get("error"):
            return oauth_redirect("denied")
        code = request.args.get("code")
        if not code:
            return oauth_redirect("failed")
        access_token = spotify_token_exchange(code)
        spotify_user = spotify_authenticated_user(access_token) if access_token else None
        if not spotify_user or str(spotify_user["id"]) != attempt.claimed_user_id:
            return oauth_redirect("failed")
        social = connection.scalar(select(SocialAccount).join(Creator, SocialAccount.creator_id == Creator.id).where(SocialAccount.id == attempt.social_id, Creator.user_id == attempt.user_id))
        if not social or social.platform != "Spotify" or spotify_user_id_from_claim(social.username, social.profile_url) != attempt.claimed_user_id:
            return oauth_redirect("failed")
        social.ownership_verified = True; social.verification_status = "verified"; social.verified_at = datetime.now(timezone.utc); social.provider_account_id = str(spotify_user["account_id"])
        connection.commit()
        return oauth_redirect("success")
    finally: pass
