"""SQLAlchemy 2.x schema for UpNext."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"; id:Mapped[int]=mapped_column(primary_key=True); email:Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash:Mapped[str]=mapped_column(String(512)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Creator(Base):
    __tablename__="creators"; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),unique=True); display_name:Mapped[str]=mapped_column(String(255)); username:Mapped[str]=mapped_column(String(64),unique=True,index=True); bio:Mapped[str]=mapped_column(Text,default=""); avatar:Mapped[str]=mapped_column(Text,default=""); location:Mapped[str|None]=mapped_column(String(255)); website:Mapped[str|None]=mapped_column(Text); is_public:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
class CreatorCategory(Base):
    __tablename__="creator_categories"; creator_id:Mapped[int]=mapped_column(ForeignKey("creators.id",ondelete="CASCADE"),primary_key=True); category:Mapped[str]=mapped_column(String(100),primary_key=True)
class CreatorSkill(Base):
    __tablename__="creator_skills"; creator_id:Mapped[int]=mapped_column(ForeignKey("creators.id",ondelete="CASCADE"),primary_key=True); skill:Mapped[str]=mapped_column(String(255),primary_key=True)
class CreatorLookingFor(Base):
    __tablename__="creator_looking_for"; creator_id:Mapped[int]=mapped_column(ForeignKey("creators.id",ondelete="CASCADE"),primary_key=True); item:Mapped[str]=mapped_column(String(255),primary_key=True)
class Project(Base):
    __tablename__="projects"; id:Mapped[int]=mapped_column(primary_key=True); creator_id:Mapped[int]=mapped_column(ForeignKey("creators.id",ondelete="CASCADE"),index=True); title:Mapped[str]=mapped_column(String(255)); description:Mapped[str]=mapped_column(Text,default=""); type:Mapped[str]=mapped_column(String(255),default=""); url:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
class SocialAccount(Base):
    __tablename__="social_accounts"; id:Mapped[int]=mapped_column(primary_key=True); creator_id:Mapped[int]=mapped_column(ForeignKey("creators.id",ondelete="CASCADE"),index=True); platform:Mapped[str]=mapped_column(String(64)); username:Mapped[str]=mapped_column(String(255)); profile_url:Mapped[str]=mapped_column(Text); follower_count:Mapped[int|None]=mapped_column(Integer); ownership_verified:Mapped[bool]=mapped_column(Boolean,default=False); eligibility_verified:Mapped[bool]=mapped_column(Boolean,default=False); verification_status:Mapped[str]=mapped_column(String(64),default="unverified"); provider_account_id:Mapped[str|None]=mapped_column(String(255)); verified_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); last_checked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
class Report(Base):
    __tablename__="reports"; id:Mapped[int]=mapped_column(primary_key=True); reporter_user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); creator_id:Mapped[int]=mapped_column(ForeignKey("creators.id",ondelete="CASCADE"),index=True); reason:Mapped[str]=mapped_column(String(100)); details:Mapped[str]=mapped_column(Text,default=""); status:Mapped[str]=mapped_column(String(32),default="open"); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class SpotifyOAuthAttempt(Base):
    __tablename__="spotify_oauth_attempts"; state:Mapped[str]=mapped_column(String(255),primary_key=True); social_id:Mapped[int]=mapped_column(ForeignKey("social_accounts.id",ondelete="CASCADE"),index=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); claimed_user_id:Mapped[str]=mapped_column(String(255)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

Index("idx_creators_updated_at", Creator.updated_at)
