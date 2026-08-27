import re
import sqlite3

from flask import Blueprint, g, jsonify, request

from database import get_db
from helpers.auth import require_login

socials_bp = Blueprint("socials", __name__)
PLATFORMS = {"Instagram", "TikTok", "YouTube", "GitHub", "X", "Twitch", "Behance", "Dribbble", "LinkedIn", "Website/Portfolio"}
URL_PATTERN = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


def owned_creator(connection):
    return connection.execute("SELECT id FROM creators WHERE user_id = ?", (g.user_id,)).fetchone()


def validate(data):
    platform = str(data.get("platform", "")).strip()
    username = str(data.get("username", "")).strip()
    profile_url = str(data.get("profile_url", "")).strip()
    if platform not in PLATFORMS or not username or not URL_PATTERN.fullmatch(profile_url):
        return None, "platform, username, and a valid http(s) profile_url are required."
    return (platform, username, profile_url), None


@socials_bp.get("/api/creator/socials")
@require_login
def list_socials():
    connection = get_db()
    try:
        creator = owned_creator(connection)
        if not creator: return jsonify({"social_accounts": []})
        rows = connection.execute("SELECT id, platform, username, profile_url, follower_count, ownership_verified, eligibility_verified, verification_status, verified_at, last_checked_at, created_at, updated_at FROM social_accounts WHERE creator_id = ? ORDER BY id", (creator["id"],)).fetchall()
        return jsonify({"social_accounts": [dict(row) for row in rows]})
    finally: connection.close()


@socials_bp.post("/api/creator/socials")
@require_login
def create_social():
    data = request.get_json(silent=True) or {}
    values, error = validate(data)
    if error: return jsonify({"error": error}), 400
    connection = get_db()
    try:
        creator = owned_creator(connection)
        if not creator: return jsonify({"error": "Create a creator profile first."}), 400
        cursor = connection.execute("INSERT INTO social_accounts (creator_id, platform, username, profile_url) VALUES (?, ?, ?, ?)", (creator["id"], *values))
        connection.commit()
        row = connection.execute("SELECT id, platform, username, profile_url, follower_count, ownership_verified, eligibility_verified, verification_status, verified_at, last_checked_at, created_at, updated_at FROM social_accounts WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify({"social_account": dict(row)}), 201
    except sqlite3.IntegrityError: return jsonify({"error": "Could not create social account."}), 409
    finally: connection.close()


def get_owned_social(connection, social_id):
    return connection.execute("SELECT social_accounts.* FROM social_accounts JOIN creators ON creators.id = social_accounts.creator_id WHERE social_accounts.id = ? AND creators.user_id = ?", (social_id, g.user_id)).fetchone()


@socials_bp.patch("/api/creator/socials/<int:social_id>")
def update_social(social_id):
    return _update_social(social_id)


@socials_bp.put("/api/creator/socials/<int:social_id>")
def replace_social(social_id):
    return _update_social(social_id)


@require_login
def _update_social(social_id):
    data = request.get_json(silent=True) or {}
    connection = get_db()
    try:
        row = get_owned_social(connection, social_id)
        if not row: return jsonify({"error": "Social account not found."}), 404
        updates = {}
        for field in ("platform", "username", "profile_url"):
            if field in data: updates[field] = str(data[field]).strip()
        if "platform" in updates and updates["platform"] not in PLATFORMS: return jsonify({"error": "Unsupported platform."}), 400
        if "profile_url" in updates and not URL_PATTERN.fullmatch(updates["profile_url"]): return jsonify({"error": "Invalid profile URL."}), 400
        if not updates: return jsonify({"error": "No editable fields provided."}), 400
        assignments = ", ".join(f"{field} = ?" for field in updates) + ", updated_at = CURRENT_TIMESTAMP"
        connection.execute(f"UPDATE social_accounts SET {assignments} WHERE id = ?", [*updates.values(), social_id])
        connection.commit()
        updated = connection.execute("SELECT id, platform, username, profile_url, follower_count, ownership_verified, eligibility_verified, verification_status, verified_at, last_checked_at, created_at, updated_at FROM social_accounts WHERE id = ?", (social_id,)).fetchone()
        return jsonify({"social_account": dict(updated)})
    finally: connection.close()


@socials_bp.delete("/api/creator/socials/<int:social_id>")
@require_login
def delete_social(social_id):
    connection = get_db()
    try:
        row = get_owned_social(connection, social_id)
        if not row: return jsonify({"error": "Social account not found."}), 404
        connection.execute("DELETE FROM social_accounts WHERE id = ?", (social_id,))
        connection.commit()
        return jsonify({"status": "ok"})
    finally: connection.close()
