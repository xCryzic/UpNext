from flask import Blueprint,jsonify,request
from sqlalchemy import select
from database import sqlalchemy_session
from models import Creator,Report,User
from helpers.auth import require_admin,require_login
from routes.creators import publishability,serialize_creator
admin_bp=Blueprint("admin",__name__);REPORT_STATUSES={"open","dismissed","actioned"}
@admin_bp.get("/api/admin/reports")
@require_login
@require_admin
def list_reports():
 db=sqlalchemy_session();rows=db.execute(select(Report,Creator,User).join(Creator,Report.creator_id==Creator.id).join(User,Report.reporter_user_id==User.id).order_by(Report.created_at.desc(),Report.id.desc())).all()
 return jsonify({"reports":[{"id":r.id,"reason":r.reason,"details":r.details,"status":r.status,"created_at":r.created_at.isoformat() if r.created_at else None,"creator_id":c.id,"display_name":c.display_name,"username":c.username,"reporter_email":u.email} for r,c,u in rows]})
@admin_bp.patch("/api/admin/reports/<int:report_id>")
@require_login
@require_admin
def update_report(report_id):
 status=str((request.get_json(silent=True) or {}).get("status","")).strip()
 if status not in REPORT_STATUSES:return jsonify({"error":"status must be open, dismissed, or actioned."}),400
 db=sqlalchemy_session();r=db.get(Report,report_id)
 if not r:return jsonify({"error":"Report not found."}),404
 r.status=status;db.commit();return jsonify({"report":{"id":report_id,"status":status}})
@admin_bp.patch("/api/admin/creators/<int:creator_id>/visibility")
@require_login
@require_admin
def update_creator_visibility(creator_id):
 d=request.get_json(silent=True) or {}
 if not isinstance(d.get("is_public"),bool):return jsonify({"error":"is_public must be true or false."}),400
 db=sqlalchemy_session();c=db.get(Creator,creator_id)
 if not c:return jsonify({"error":"Creator not found."}),404
 if d["is_public"] and not publishability(db,c)["publishable"]:return jsonify({"error":"Only publishable profiles can be restored."}),400
 c.is_public=d["is_public"];db.commit();return jsonify({"creator":serialize_creator(db,c,True)})
