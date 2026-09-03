from functools import wraps

from flask import current_app, g, jsonify, session
from sqlalchemy import select

from database import sqlalchemy_session
from models import Creator, User


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
        user = sqlalchemy_session().get(User, g.user_id)
        if not user or user.email.lower() not in current_app.config.get("ADMIN_EMAILS", set()):
            return jsonify({"error": "Administrator access required."}), 403
        return view(*args, **kwargs)
    return wrapped


def get_creator_for_user(db, user_id):
    return db.scalar(select(Creator).where(Creator.user_id == user_id))


def get_owned_creator(db, user_id):
    return get_creator_for_user(db, user_id)
