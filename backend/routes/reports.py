from flask import Blueprint,g,jsonify,request
from database import sqlalchemy_session
from models import Creator,Report
from helpers.auth import require_login
from services.rate_limit import rate_limit
reports_bp=Blueprint("reports",__name__);REASONS={"misleading_work","plagiarism","spam","fake_credentials","ai_misrepresentation","inappropriate_content","other"}
@reports_bp.post("/api/reports")
@require_login
@rate_limit("RATE_LIMIT_REPORTS_PER_MINUTE",5)
def create_report():
 d=request.get_json(silent=True) or {};reason=str(d.get("reason","")).strip();details=str(d.get("details","")).strip()
 try:cid=int(d.get("creator_id"))
 except (TypeError,ValueError):cid=None
 if reason not in REASONS or not cid:return jsonify({"error":"creator_id and a supported reason are required."}),400
 db=sqlalchemy_session()
 if not db.get(Creator,cid):return jsonify({"error":"Creator not found."}),404
 r=Report(reporter_user_id=g.user_id,creator_id=cid,reason=reason,details=details);db.add(r);db.commit();return jsonify({"report":{"id":r.id,"status":"open"}}),201
