import re
from flask import Blueprint,g,jsonify,request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import sqlalchemy_session
from models import Creator,CreatorCategory,CreatorSkill,CreatorLookingFor,Project,SocialAccount
from helpers.auth import require_login
from services.discovery_service import calculate_profile_strength,sort_profiles
creators_bp=Blueprint("creators",__name__);CATEGORIES={"Artist","Musician","Developer","Game Developer","Video Creator","Writer","Photographer","Designer","3D Artist","Other"};VERIFIABLE_PLATFORMS={"GitHub","Spotify"}
def clean_list(v):
 if v is None:return []
 if not isinstance(v,list):raise ValueError
 return list(dict.fromkeys(x.strip() for x in v if isinstance(x,str) and x.strip()))
def validate_username(v):return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9_.-]{1,28}[a-z0-9])?",v))
def rel(db,m,f,cid):return list(db.scalars(select(getattr(m,f)).where(m.creator_id==cid).order_by(getattr(m,f))))
def publishability(db,c):
 if not c:return {"publishable":False,"missing":["profile"]}
 r={"display_name":bool(c.display_name),"username":bool(c.username),"bio":bool((c.bio or "").strip()),"category":bool(rel(db,CreatorCategory,"category",c.id)),"skill":bool(rel(db,CreatorSkill,"skill",c.id)),"project":db.scalar(select(Project.id).where(Project.creator_id==c.id).limit(1)) is not None,"social_account":db.scalar(select(SocialAccount.id).where(SocialAccount.creator_id==c.id).limit(1)) is not None};return {"publishable":not [x for x in r if not r[x]],"missing":[x for x in r if not r[x]]}
def iso(v):return v.isoformat() if v else None
def serialize_creator(db,c,include_owner=False):
 socials=[]
 for s in db.scalars(select(SocialAccount).where(SocialAccount.creator_id==c.id).order_by(SocialAccount.id)):
  x={"id":s.id,"platform":s.platform,"username":s.username,"profile_url":s.profile_url,"ownership_verified":bool(s.ownership_verified),"eligibility_verified":bool(s.eligibility_verified),"verification_status":s.verification_status,"verified_at":iso(s.verified_at),"last_checked_at":iso(s.last_checked_at)}
  if s.eligibility_verified and s.follower_count is not None:x["follower_count"]=s.follower_count
  socials.append(x)
 out={"id":c.id,"display_name":c.display_name,"username":c.username,"bio":c.bio or "","avatar":c.avatar or "","location":c.location,"website":c.website,"categories":rel(db,CreatorCategory,"category",c.id),"skills":rel(db,CreatorSkill,"skill",c.id),"looking_for":rel(db,CreatorLookingFor,"item",c.id),"social_accounts":socials,"projects":[{"id":p.id,"title":p.title,"description":p.description,"type":p.type,"url":p.url,"created_at":iso(p.created_at),"updated_at":iso(p.updated_at)} for p in db.scalars(select(Project).where(Project.creator_id==c.id).order_by(Project.created_at.desc()))],"created_at":iso(c.created_at),"updated_at":iso(c.updated_at),"publishability":publishability(db,c),"is_public":bool(c.is_public),"verified_social_count":sum(x["platform"] in VERIFIABLE_PLATFORMS and x["ownership_verified"] and x["verification_status"]=="verified" for x in socials)};out["profile_strength"]=calculate_profile_strength(out)
 if include_owner:out["user_id"]=c.user_id
 return out
def save_rel(db,cid,cats,skills,looking):
 for m,f,v in ((CreatorCategory,"category",cats),(CreatorSkill,"skill",skills),(CreatorLookingFor,"item",looking)):
  db.query(m).filter_by(creator_id=cid).delete();db.add_all([m(creator_id=cid,**{f:x}) for x in v])
def mine(db):return db.scalar(select(Creator).where(Creator.user_id==g.user_id))
@creators_bp.get("/api/creator/me")
@require_login
def get_my_creator():
 db=sqlalchemy_session();c=mine(db);return jsonify({"creator":serialize_creator(db,c,True) if c else None})
@creators_bp.post("/api/creator")
@require_login
def create_creator():
 d=request.get_json(silent=True) or {};u=str(d.get("username","")).strip().lower();name=str(d.get("display_name","")).strip()
 if not name or not u:return jsonify({"error":"display_name and username are required."}),400
 if not validate_username(u):return jsonify({"error":"Username must be 3-30 lowercase letters, numbers, dots, dashes, or underscores."}),400
 try:cats,skills,looking=clean_list(d.get("categories")),clean_list(d.get("skills")),clean_list(d.get("looking_for"))
 except ValueError:return jsonify({"error":"categories, skills, and looking_for must be lists."}),400
 invalid=[x for x in cats if x not in CATEGORIES]
 if invalid:return jsonify({"error":"Unsupported category.","invalid":invalid}),400
 db=sqlalchemy_session()
 if mine(db):return jsonify({"error":"You already have a creator profile."}),409
 try:
  c=Creator(user_id=g.user_id,display_name=name,username=u,bio=str(d.get("bio","")).strip(),avatar=str(d.get("avatar","")).strip(),location=d.get("location"),website=d.get("website"));db.add(c);db.flush();save_rel(db,c.id,cats,skills,looking);db.commit();return jsonify({"creator":serialize_creator(db,c,True)}),201
 except IntegrityError:db.rollback();return jsonify({"error":"That username is already in use."}),409
@creators_bp.patch("/api/creator")
@creators_bp.put("/api/creator")
@require_login
def update_creator():
 d=request.get_json(silent=True) or {};db=sqlalchemy_session();c=mine(db)
 if not c:return jsonify({"error":"Creator profile not found."}),404
 try:
  if "username" in d:
   u=str(d["username"]).strip().lower()
   if not validate_username(u):return jsonify({"error":"Invalid username."}),400
   c.username=u
  for f in ("display_name","bio","avatar","location","website"):
   if f in d:setattr(c,f,d[f])
  vals=[]
  for key in ("categories","skills","looking_for"):
   if key in d:vals.append(clean_list(d[key]))
   else:vals.append(rel(db,{"categories":CreatorCategory,"skills":CreatorSkill,"looking_for":CreatorLookingFor}[key],{"categories":"category","skills":"skill","looking_for":"item"}[key],c.id))
  if any(k in d for k in ("categories","skills","looking_for")):
   invalid=[x for x in vals[0] if x not in CATEGORIES]
   if invalid:return jsonify({"error":"Unsupported category.","invalid":invalid}),400
   save_rel(db,c.id,*vals)
  db.commit();return jsonify({"creator":serialize_creator(db,c,True)})
 except ValueError:return jsonify({"error":"categories, skills, and looking_for must be lists."}),400
 except IntegrityError:db.rollback();return jsonify({"error":"That username is already in use."}),409
@creators_bp.delete("/api/creator")
@require_login
def delete_creator():
 db=sqlalchemy_session();c=mine(db)
 if c:db.delete(c);db.commit()
 return jsonify({"status":"ok"})
@creators_bp.patch("/api/creator/visibility")
@require_login
def update_creator_visibility():
 d=request.get_json(silent=True) or {}
 if not isinstance(d.get("is_public"),bool):return jsonify({"error":"is_public must be true or false."}),400
 db=sqlalchemy_session();c=mine(db)
 if not c:return jsonify({"error":"Creator profile not found."}),404
 if d["is_public"] and not publishability(db,c)["publishable"]:return jsonify({"error":"Complete the required profile sections before publishing."}),400
 c.is_public=d["is_public"];db.commit();return jsonify({"creator":serialize_creator(db,c,True)})
@creators_bp.get("/api/creators")
def list_creators():
 search=request.args.get("search","").strip();category=request.args.get("category","").strip();sort=request.args.get("sort","discover")
 try:limit=min(max(int(request.args.get("limit",20)),1),100);offset=max(int(request.args.get("offset",0)),0)
 except ValueError:return jsonify({"error":"limit and offset must be integers."}),400
 db=sqlalchemy_session();ps=[serialize_creator(db,c) for c in db.scalars(select(Creator).order_by(Creator.updated_at.desc()))];ps=[p for p in ps if p["publishability"]["publishable"] and p["is_public"]]
 if category:ps=[p for p in ps if category in p["categories"]]
 if search:
  n=search.lower();ps=[p for p in ps if n in " ".join([p["display_name"],p["username"],p["bio"]," ".join(p["categories"])," ".join(p["skills"])," ".join(p["looking_for"])," ".join(x["title"]+" "+x["description"] for x in p["projects"])]).lower()]
 ps=sort_profiles(ps,sort,search,category);return jsonify({"creators":ps[offset:offset+limit],"total":len(ps),"limit":limit,"offset":offset})
@creators_bp.get("/api/creators/<username>")
def public_creator(username):
 db=sqlalchemy_session();c=db.scalar(select(Creator).where(Creator.username==username.strip().lower()))
 if not c:return jsonify({"error":"Creator not found."}),404
 r=serialize_creator(db,c)
 if not r["publishability"]["publishable"] or not c.is_public:return jsonify({"error":"Creator not found."}),404
 return jsonify({"creator":r})
@creators_bp.get("/api/creator/status")
@require_login
def creator_status():return jsonify(publishability(sqlalchemy_session(),mine(sqlalchemy_session())))
