from flask import Blueprint,g,jsonify,request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import sqlalchemy_session
from models import Creator,Project
from helpers.auth import require_login
projects_bp=Blueprint("projects",__name__)
def owned_creator(db):return db.scalar(select(Creator).where(Creator.user_id==g.user_id))
def serialize(p):return {"id":p.id,"title":p.title,"description":p.description,"type":p.type,"url":p.url,"created_at":p.created_at.isoformat() if p.created_at else None,"updated_at":p.updated_at.isoformat() if p.updated_at else None}
def valid(data):
 title=str(data.get("title","")).strip();url=str(data.get("url","")).strip()
 return (title,str(data.get("description","")).strip(),str(data.get("type","")).strip(),url) if title and url.lower().startswith(("http://","https://")) else None
def own(db,pid):return db.scalar(select(Project).join(Creator,Project.creator_id==Creator.id).where(Project.id==pid,Creator.user_id==g.user_id))
@projects_bp.get("/api/creator/projects")
@require_login
def list_projects():
 db=sqlalchemy_session();c=owned_creator(db);items=[] if not c else list(db.scalars(select(Project).where(Project.creator_id==c.id).order_by(Project.created_at.desc())))
 return jsonify({"projects":[serialize(p) for p in items]})
@projects_bp.post("/api/creator/projects")
@require_login
def create_project():
 values=valid(request.get_json(silent=True) or {})
 if not values:return jsonify({"error":"title and a valid http(s) url are required."}),400
 db=sqlalchemy_session();c=owned_creator(db)
 if not c:return jsonify({"error":"Create a creator profile first."}),400
 try:
  p=Project(creator_id=c.id,title=values[0],description=values[1],type=values[2],url=values[3]);db.add(p);db.commit();return jsonify({"project":serialize(p)}),201
 except IntegrityError:db.rollback();return jsonify({"error":"Could not create project."}),409
@projects_bp.patch("/api/creator/projects/<int:project_id>")
@projects_bp.put("/api/creator/projects/<int:project_id>")
@require_login
def update_project(project_id):
 data=request.get_json(silent=True) or {};db=sqlalchemy_session();p=own(db,project_id)
 if not p:return jsonify({"error":"Project not found."}),404
 fields={k:data[k] for k in ("title","description","type","url") if k in data}
 if not fields:return jsonify({"error":"No editable fields provided."}),400
 if "title" in fields:fields["title"]=str(fields["title"]).strip()
 if "url" in fields and not str(fields["url"]).strip().lower().startswith(("http://","https://")):return jsonify({"error":"Invalid project URL."}),400
 for k,v in fields.items():setattr(p,k,v.strip() if isinstance(v,str) else v)
 db.commit();return jsonify({"project":serialize(p)})
@projects_bp.delete("/api/creator/projects/<int:project_id>")
@require_login
def delete_project(project_id):
 db=sqlalchemy_session();p=own(db,project_id)
 if not p:return jsonify({"error":"Project not found."}),404
 db.delete(p);db.commit();return jsonify({"status":"ok"})
