from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db

auth_bp = Blueprint("auth", __name__)


def user_response(row):
    return {"id": str(row["id"]), "email": row["email"]}


@auth_bp.post("/api/auth/signup")
def signup():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    if not email: return jsonify({"error": "Email is required."}), 400
    if not password: return jsonify({"error": "Password is required."}), 400
    if len(password) < 8: return jsonify({"error": "Password must be at least 8 characters."}), 400
    connection = get_db()
    try:
        if connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            return jsonify({"error": "An account with this email already exists."}), 409
        cursor = connection.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, generate_password_hash(password)))
        connection.commit()
        session.clear()
        session["user_id"] = cursor.lastrowid
        return jsonify({"user": {"id": str(cursor.lastrowid), "email": email}}), 201
    finally: connection.close()


@auth_bp.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    if not email or not password: return jsonify({"error": "Email and password are required."}), 400
    connection = get_db()
    try:
        user = connection.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid email or password."}), 401
        session.clear()
        session["user_id"] = user["id"]
        return jsonify({"user": user_response(user)})
    finally: connection.close()


@auth_bp.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"status": "ok"})


@auth_bp.get("/api/auth/me")
def current_user():
    user_id = session.get("user_id")
    if not user_id: return jsonify({"user": None})
    connection = get_db()
    try:
        user = connection.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            session.clear()
            return jsonify({"user": None})
        return jsonify({"user": user_response(user)})
    finally: connection.close()
