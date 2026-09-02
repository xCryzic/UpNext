from flask import Blueprint, g, jsonify, request

from database import get_db
from helpers.auth import require_login
from services.rate_limit import rate_limit

reports_bp = Blueprint("reports", __name__)
REASONS = {"misleading_work", "plagiarism", "spam", "fake_credentials", "ai_misrepresentation", "inappropriate_content", "other"}


@reports_bp.post("/api/reports")
@require_login
@rate_limit("RATE_LIMIT_REPORTS_PER_MINUTE", 5)
def create_report():
    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "")).strip()
    details = str(data.get("details", "")).strip()
    try:
        creator_id = int(data.get("creator_id"))
    except (TypeError, ValueError):
        creator_id = None
    if reason not in REASONS or not creator_id:
        return jsonify({"error": "creator_id and a supported reason are required."}), 400
    connection = get_db()
    try:
        if not connection.execute("SELECT 1 FROM creators WHERE id = ?", (creator_id,)).fetchone():
            return jsonify({"error": "Creator not found."}), 404
        cursor = connection.execute("INSERT INTO reports (reporter_user_id, creator_id, reason, details) VALUES (?, ?, ?, ?)", (g.user_id, creator_id, reason, details))
        connection.commit()
        return jsonify({"report": {"id": cursor.lastrowid, "status": "open"}}), 201
    finally:
        connection.close()
