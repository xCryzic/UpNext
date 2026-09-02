from flask import Blueprint, g, jsonify, session

from database import get_db
from helpers.auth import require_login

account_bp = Blueprint("account", __name__)


@account_bp.delete("/api/account")
@require_login
def delete_account():
    connection = get_db()
    try:
        with connection:
            connection.execute("DELETE FROM users WHERE id = ?", (g.user_id,))
        session.clear()
        return jsonify({"status": "deleted"})
    finally:
        connection.close()
