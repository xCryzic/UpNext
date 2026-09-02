from functools import wraps

from flask import current_app, g, jsonify, session

from database import get_db


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Authentication required."}), 401
        g.user_id = int(user_id)
        return view(*args, **kwargs)

    return wrapped


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        connection = get_db()
        try:
            user = connection.execute("SELECT email FROM users WHERE id = ?", (g.user_id,)).fetchone()
        finally:
            connection.close()
        if not user or user["email"].lower() not in current_app.config.get("ADMIN_EMAILS", set()):
            return jsonify({"error": "Administrator access required."}), 403
        return view(*args, **kwargs)
    return wrapped


def get_creator_for_user(connection, user_id):
    return connection.execute(
        "SELECT * FROM creators WHERE user_id = ?", (user_id,)
    ).fetchone()


def get_owned_creator(connection, user_id):
    return get_creator_for_user(connection, user_id)


def close_db(connection):
    if connection:
        connection.close()
