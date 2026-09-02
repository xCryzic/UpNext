from flask import Blueprint, jsonify, request

from database import get_db
from helpers.auth import require_admin, require_login
from routes.creators import publishability, serialize_creator

admin_bp = Blueprint("admin", __name__)
REPORT_STATUSES = {"open", "dismissed", "actioned"}


@admin_bp.get("/api/admin/reports")
@require_login
@require_admin
def list_reports():
    connection = get_db()
    try:
        rows = connection.execute(
            """SELECT reports.id, reports.reason, reports.details, reports.status, reports.created_at,
                      creators.id AS creator_id, creators.display_name, creators.username,
                      users.email AS reporter_email
               FROM reports
               JOIN creators ON creators.id = reports.creator_id
               JOIN users ON users.id = reports.reporter_user_id
               ORDER BY reports.created_at DESC, reports.id DESC"""
        ).fetchall()
        return jsonify({"reports": [dict(row) for row in rows]})
    finally:
        connection.close()


@admin_bp.patch("/api/admin/reports/<int:report_id>")
@require_login
@require_admin
def update_report(report_id):
    status = str((request.get_json(silent=True) or {}).get("status", "")).strip()
    if status not in REPORT_STATUSES:
        return jsonify({"error": "status must be open, dismissed, or actioned."}), 400
    connection = get_db()
    try:
        if not connection.execute("SELECT 1 FROM reports WHERE id = ?", (report_id,)).fetchone():
            return jsonify({"error": "Report not found."}), 404
        connection.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
        connection.commit()
        return jsonify({"report": {"id": report_id, "status": status}})
    finally:
        connection.close()


@admin_bp.patch("/api/admin/creators/<int:creator_id>/visibility")
@require_login
@require_admin
def update_creator_visibility(creator_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("is_public"), bool):
        return jsonify({"error": "is_public must be true or false."}), 400
    connection = get_db()
    try:
        creator = connection.execute("SELECT * FROM creators WHERE id = ?", (creator_id,)).fetchone()
        if not creator:
            return jsonify({"error": "Creator not found."}), 404
        if data["is_public"] and not publishability(connection, creator)["publishable"]:
            return jsonify({"error": "Only publishable profiles can be restored."}), 400
        connection.execute("UPDATE creators SET is_public = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (int(data["is_public"]), creator_id))
        connection.commit()
        creator = connection.execute("SELECT * FROM creators WHERE id = ?", (creator_id,)).fetchone()
        return jsonify({"creator": serialize_creator(connection, creator, True)})
    finally:
        connection.close()
