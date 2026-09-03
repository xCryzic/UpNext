from flask import Blueprint,g,jsonify,session
from database import sqlalchemy_session
from models import User
from helpers.auth import require_login
account_bp=Blueprint("account",__name__)
@account_bp.delete("/api/account")
@require_login
def delete_account():
 db=sqlalchemy_session();user=db.get(User,g.user_id)
 if user:db.delete(user);db.commit()
 session.clear();return jsonify({"status":"deleted"})
