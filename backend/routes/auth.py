from flask import Blueprint,current_app,jsonify,request,session
import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash,generate_password_hash
from database import sqlalchemy_session
from models import Creator, User
from services.rate_limit import rate_limit
auth_bp=Blueprint("auth",__name__)
def user_response(user):return {"id":str(user.id),"email":user.email,"is_admin":user.email.lower() in current_app.config.get("ADMIN_EMAILS",set())}
def valid_username(value):return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9_.-]{1,28}[a-z0-9])?",value))
@auth_bp.post("/api/auth/signup")
@rate_limit("RATE_LIMIT_SIGNUP_PER_MINUTE",5)
def signup():
 data=request.get_json(silent=True) or {};email=str(data.get("email","")).strip().lower();password=data.get("password","");display_name=str(data.get("display_name","")).strip();username=str(data.get("username","")).strip().lower()
 if not email:return jsonify({"error":"Email is required."}),400
 if not password:return jsonify({"error":"Password is required."}),400
 if len(password)<8:return jsonify({"error":"Password must be at least 8 characters."}),400
 if display_name or username:
  if not display_name or not username:return jsonify({"error":"Display name and username are required together."}),400
  if not valid_username(username):return jsonify({"error":"Username must be 3-30 lowercase letters, numbers, dots, dashes, or underscores."}),400
 db=sqlalchemy_session()
 try:
  user=User(email=email,password_hash=generate_password_hash(password));db.add(user);db.flush()
  if username:db.add(Creator(user_id=user.id,display_name=display_name,username=username))
  db.commit();session.clear();session["user_id"]=user.id;return jsonify({"user":user_response(user)}),201
 except IntegrityError:
  db.rollback()
  if username and db.scalar(select(Creator.id).where(func.lower(Creator.username)==username)) is not None:return jsonify({"error":"That username is already taken."}),409
  return jsonify({"error":"An account with this email already exists."}),409
@auth_bp.post("/api/auth/login")
@rate_limit("RATE_LIMIT_LOGIN_PER_MINUTE",10)
def login():
 data=request.get_json(silent=True) or {};email=str(data.get("email","")).strip().lower();password=data.get("password","")
 if not email or not password:return jsonify({"error":"Email and password are required."}),400
 user=sqlalchemy_session().scalar(select(User).where(User.email==email))
 if not user or not check_password_hash(user.password_hash,password):return jsonify({"error":"Invalid email or password."}),401
 session.clear();session["user_id"]=user.id;return jsonify({"user":user_response(user)})
@auth_bp.post("/api/auth/logout")
def logout():session.clear();return jsonify({"status":"ok"})
@auth_bp.get("/api/auth/me")
def current_user():
 user_id=session.get("user_id")
 if not user_id:return jsonify({"user":None})
 user=sqlalchemy_session().get(User,user_id)
 if not user:session.clear();return jsonify({"user":None})
 return jsonify({"user":user_response(user)})
