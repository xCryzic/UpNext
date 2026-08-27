import sqlite3

from flask import Blueprint, g, jsonify, request

from database import get_db
from helpers.auth import require_login

projects_bp = Blueprint("projects", __name__)


def owned_creator(connection):
    return connection.execute("SELECT id FROM creators WHERE user_id = ?", (g.user_id,)).fetchone()


def valid_project(data):
    title = str(data.get("title", "")).strip()
    url = str(data.get("url", "")).strip()
    if not title or not url or not url.lower().startswith(("http://", "https://")):
        return None
    return title, str(data.get("description", "")).strip(), str(data.get("type", "")).strip(), url


def own_project(connection, project_id):
    return connection.execute("SELECT projects.* FROM projects JOIN creators ON creators.id = projects.creator_id WHERE projects.id = ? AND creators.user_id = ?", (project_id, g.user_id)).fetchone()


@projects_bp.get("/api/creator/projects")
@require_login
def list_projects():
    connection = get_db()
    try:
        creator = owned_creator(connection)
        rows = connection.execute("SELECT id, title, description, type, url, created_at, updated_at FROM projects WHERE creator_id = ? ORDER BY created_at DESC", (creator["id"],)).fetchall() if creator else []
        return jsonify({"projects": [dict(row) for row in rows]})
    finally: connection.close()


@projects_bp.post("/api/creator/projects")
@require_login
def create_project():
    data = request.get_json(silent=True) or {}
    values = valid_project(data)
    if not values: return jsonify({"error": "title and a valid http(s) url are required."}), 400
    connection = get_db()
    try:
        creator = owned_creator(connection)
        if not creator: return jsonify({"error": "Create a creator profile first."}), 400
        cursor = connection.execute("INSERT INTO projects (creator_id, title, description, type, url) VALUES (?, ?, ?, ?, ?)", (creator["id"], *values))
        connection.commit()
        row = connection.execute("SELECT id, title, description, type, url, created_at, updated_at FROM projects WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify({"project": dict(row)}), 201
    except sqlite3.IntegrityError: return jsonify({"error": "Could not create project."}), 409
    finally: connection.close()


@projects_bp.patch("/api/creator/projects/<int:project_id>")
@projects_bp.put("/api/creator/projects/<int:project_id>")
@require_login
def update_project(project_id):
    data = request.get_json(silent=True) or {}
    connection = get_db()
    try:
        project = own_project(connection, project_id)
        if not project: return jsonify({"error": "Project not found."}), 404
        updates = {field: data[field] for field in ("title", "description", "type", "url") if field in data}
        if "title" in updates: updates["title"] = str(updates["title"]).strip()
        if "url" in updates:
            updates["url"] = str(updates["url"]).strip()
            if not updates["url"].lower().startswith(("http://", "https://")): return jsonify({"error": "Invalid project URL."}), 400
        if not updates: return jsonify({"error": "No editable fields provided."}), 400
        assignments = ", ".join(f"{field} = ?" for field in updates) + ", updated_at = CURRENT_TIMESTAMP"
        connection.execute(f"UPDATE projects SET {assignments} WHERE id = ?", [*updates.values(), project_id])
        connection.commit()
        updated = connection.execute("SELECT id, title, description, type, url, created_at, updated_at FROM projects WHERE id = ?", (project_id,)).fetchone()
        return jsonify({"project": dict(updated)})
    finally: connection.close()


@projects_bp.delete("/api/creator/projects/<int:project_id>")
@require_login
def delete_project(project_id):
    connection = get_db()
    try:
        project = own_project(connection, project_id)
        if not project: return jsonify({"error": "Project not found."}), 404
        connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        connection.commit()
        return jsonify({"status": "ok"})
    finally: connection.close()
