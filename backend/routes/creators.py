import re
import sqlite3

from flask import Blueprint, g, jsonify, request

from database import get_db
from helpers.auth import require_login
from services.discovery_service import sort_profiles

creators_bp = Blueprint("creators", __name__)

CATEGORIES = {
    "Artist", "Musician", "Developer", "Game Developer", "Video Creator",
    "Writer", "Photographer", "Designer", "3D Artist", "Other",
}


def clean_list(value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("must be a list")
    return list(dict.fromkeys(item.strip() for item in value if isinstance(item, str) and item.strip()))


def validate_username(username):
    return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9_.-]{1,28}[a-z0-9])?", username))


def creator_id_for_user(connection):
    row = connection.execute("SELECT id FROM creators WHERE user_id = ?", (g.user_id,)).fetchone()
    return row["id"] if row else None


def relation_values(connection, table, column, creator_id):
    return [row[column] for row in connection.execute(
        f"SELECT {column} FROM {table} WHERE creator_id = ? ORDER BY {column}", (creator_id,)
    ).fetchall()]


def publishability(connection, creator):
    creator_id = creator["id"]
    missing = []
    required = {
        "display_name": bool(creator["display_name"]),
        "username": bool(creator["username"]),
        "bio": bool((creator["bio"] or "").strip()),
        "category": bool(relation_values(connection, "creator_categories", "category", creator_id)),
        "skill": bool(relation_values(connection, "creator_skills", "skill", creator_id)),
        "project": connection.execute("SELECT 1 FROM projects WHERE creator_id = ? LIMIT 1", (creator_id,)).fetchone() is not None,
        "social_account": connection.execute("SELECT 1 FROM social_accounts WHERE creator_id = ? LIMIT 1", (creator_id,)).fetchone() is not None,
    }
    for key, present in required.items():
        if not present:
            missing.append(key)
    return {"publishable": not missing, "missing": missing}


def serialize_creator(connection, creator, include_owner=False):
    creator_id = creator["id"]
    socials = []
    for row in connection.execute("SELECT * FROM social_accounts WHERE creator_id = ? ORDER BY id", (creator_id,)).fetchall():
        item = {
            "id": row["id"], "platform": row["platform"], "username": row["username"],
            "profile_url": row["profile_url"], "ownership_verified": bool(row["ownership_verified"]),
            "eligibility_verified": bool(row["eligibility_verified"]),
            "verification_status": row["verification_status"], "verified_at": row["verified_at"],
            "last_checked_at": row["last_checked_at"],
        }
        if row["eligibility_verified"] and row["follower_count"] is not None:
            item["follower_count"] = row["follower_count"]
        socials.append(item)
    result = {
        "id": creator_id, "display_name": creator["display_name"], "username": creator["username"],
        "bio": creator["bio"] or "", "avatar": creator["avatar"] or "", "location": creator["location"],
        "website": creator["website"], "categories": relation_values(connection, "creator_categories", "category", creator_id),
        "skills": relation_values(connection, "creator_skills", "skill", creator_id),
        "looking_for": relation_values(connection, "creator_looking_for", "item", creator_id),
        "social_accounts": socials,
        "projects": [dict(row) for row in connection.execute("SELECT id, title, description, type, url, created_at, updated_at FROM projects WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,)).fetchall()],
        "created_at": creator["created_at"], "updated_at": creator["updated_at"],
        "publishability": publishability(connection, creator),
    }
    if include_owner:
        result["user_id"] = creator["user_id"]
    return result


def save_relations(connection, creator_id, categories, skills, looking_for):
    for table, column, values in (
        ("creator_categories", "category", categories),
        ("creator_skills", "skill", skills),
        ("creator_looking_for", "item", looking_for),
    ):
        connection.execute(f"DELETE FROM {table} WHERE creator_id = ?", (creator_id,))
        connection.executemany(f"INSERT INTO {table} (creator_id, {column}) VALUES (?, ?)", [(creator_id, value) for value in values])


@creators_bp.get("/api/creator/me")
@require_login
def get_my_creator():
    connection = get_db()
    try:
        creator = connection.execute("SELECT * FROM creators WHERE user_id = ?", (g.user_id,)).fetchone()
        return jsonify({"creator": serialize_creator(connection, creator, True) if creator else None})
    finally:
        connection.close()


@creators_bp.post("/api/creator")
@require_login
def create_creator():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    display_name = str(data.get("display_name", "")).strip()
    if not display_name or not username:
        return jsonify({"error": "display_name and username are required."}), 400
    if not validate_username(username):
        return jsonify({"error": "Username must be 3-30 lowercase letters, numbers, dots, dashes, or underscores."}), 400
    try:
        categories = clean_list(data.get("categories"))
        skills = clean_list(data.get("skills"))
        looking_for = clean_list(data.get("looking_for"))
    except ValueError:
        return jsonify({"error": "categories, skills, and looking_for must be lists."}), 400
    invalid = [item for item in categories if item not in CATEGORIES]
    if invalid:
        return jsonify({"error": "Unsupported category.", "invalid": invalid}), 400
    connection = get_db()
    try:
        if connection.execute("SELECT 1 FROM creators WHERE user_id = ?", (g.user_id,)).fetchone():
            return jsonify({"error": "You already have a creator profile."}), 409
        cursor = connection.execute("INSERT INTO creators (user_id, display_name, username, bio, avatar, location, website) VALUES (?, ?, ?, ?, ?, ?, ?)", (g.user_id, display_name, username, str(data.get("bio", "")).strip(), str(data.get("avatar", "")).strip(), data.get("location"), data.get("website")))
        save_relations(connection, cursor.lastrowid, categories, skills, looking_for)
        connection.commit()
        creator = connection.execute("SELECT * FROM creators WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify({"creator": serialize_creator(connection, creator, True)}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "That username is already in use."}), 409
    finally:
        connection.close()


@creators_bp.patch("/api/creator")
@creators_bp.put("/api/creator")
@require_login
def update_creator():
    data = request.get_json(silent=True) or {}
    connection = get_db()
    try:
        creator = connection.execute("SELECT * FROM creators WHERE user_id = ?", (g.user_id,)).fetchone()
        if not creator:
            return jsonify({"error": "Creator profile not found."}), 404
        fields = {"display_name", "bio", "avatar", "location", "website"}
        updates = {field: data[field] for field in fields if field in data}
        if "username" in data:
            username = str(data["username"]).strip().lower()
            if not validate_username(username):
                return jsonify({"error": "Invalid username."}), 400
            updates["username"] = username
        categories = skills = looking_for = None
        try:
            if "categories" in data: categories = clean_list(data["categories"])
            if "skills" in data: skills = clean_list(data["skills"])
            if "looking_for" in data: looking_for = clean_list(data["looking_for"])
        except ValueError:
            return jsonify({"error": "categories, skills, and looking_for must be lists."}), 400
        if categories is not None:
            invalid = [item for item in categories if item not in CATEGORIES]
            if invalid: return jsonify({"error": "Unsupported category.", "invalid": invalid}), 400
        if updates:
            updates["updated_at"] = "CURRENT_TIMESTAMP"
            assignments = ", ".join(f"{field} = ?" for field in updates if field != "updated_at") + ", updated_at = CURRENT_TIMESTAMP"
            values = [updates[field] for field in updates if field != "updated_at"] + [g.user_id]
            connection.execute(f"UPDATE creators SET {assignments} WHERE user_id = ?", values)
        if categories is not None or skills is not None or looking_for is not None:
            current = {"categories": relation_values(connection, "creator_categories", "category", creator["id"]), "skills": relation_values(connection, "creator_skills", "skill", creator["id"]), "looking_for": relation_values(connection, "creator_looking_for", "item", creator["id"])}
            save_relations(connection, creator["id"], categories if categories is not None else current["categories"], skills if skills is not None else current["skills"], looking_for if looking_for is not None else current["looking_for"])
        connection.commit()
        creator = connection.execute("SELECT * FROM creators WHERE user_id = ?", (g.user_id,)).fetchone()
        return jsonify({"creator": serialize_creator(connection, creator, True)})
    except sqlite3.IntegrityError:
        return jsonify({"error": "That username is already in use."}), 409
    finally:
        connection.close()


@creators_bp.delete("/api/creator")
@require_login
def delete_creator():
    connection = get_db()
    try:
        connection.execute("DELETE FROM creators WHERE user_id = ?", (g.user_id,))
        connection.commit()
        return jsonify({"status": "ok"})
    finally:
        connection.close()


@creators_bp.get("/api/creators")
def list_creators():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "discover")
    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return jsonify({"error": "limit and offset must be integers."}), 400
    connection = get_db()
    try:
        rows = connection.execute("SELECT * FROM creators ORDER BY updated_at DESC").fetchall()
        profiles = [serialize_creator(connection, row) for row in rows]
        profiles = [profile for profile in profiles if profile["publishability"]["publishable"]]
        if category:
            profiles = [profile for profile in profiles if category in profile["categories"]]
        if search:
            needle = search.lower()
            profiles = [profile for profile in profiles if needle in " ".join([profile["display_name"], profile["username"], profile["bio"], " ".join(profile["categories"]), " ".join(profile["skills"]), " ".join(profile["looking_for"]), " ".join(project["title"] + " " + project["description"] for project in profile["projects"])]).lower()]
        profiles = sort_profiles(profiles, sort, search, category)
        return jsonify({"creators": profiles[offset:offset + limit], "total": len(profiles), "limit": limit, "offset": offset})
    finally:
        connection.close()


@creators_bp.get("/api/creators/<username>")
def public_creator(username):
    connection = get_db()
    try:
        creator = connection.execute("SELECT * FROM creators WHERE username = ?", (username.strip().lower(),)).fetchone()
        if not creator:
            return jsonify({"error": "Creator not found."}), 404
        result = serialize_creator(connection, creator)
        if not result["publishability"]["publishable"]:
            return jsonify({"error": "Creator not found."}), 404
        return jsonify({"creator": result})
    finally:
        connection.close()


@creators_bp.get("/api/creator/status")
@require_login
def creator_status():
    connection = get_db()
    try:
        creator = connection.execute("SELECT * FROM creators WHERE user_id = ?", (g.user_id,)).fetchone()
        return jsonify(publishability(connection, creator) if creator else {"publishable": False, "missing": ["profile"]})
    finally:
        connection.close()
