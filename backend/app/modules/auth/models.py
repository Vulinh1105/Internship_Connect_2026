from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    code = Column(String(80), unique=True)
    password = Column(String(160))
    role = Column(String(32), ForeignKey('roles.code'), nullable=False)
    active = Column(Boolean, nullable=False, default=False)
    locked_at = Column(DateTime)
    session_version = Column(Integer, nullable=False, default=0, server_default="0")

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    created_at = Column(DateTime, default=now, nullable=False)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    code = Column(String(32), nullable=False, unique=True)
    label = Column(String(100), nullable=False)

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True)
    description = Column(String(250), nullable=False)

class Grant(Base):
    __tablename__ = "role_permissions"
    id = Column(Integer, primary_key=True)
    role = Column(String(32), ForeignKey('roles.code'), nullable=False)
    permission = Column(String(100), ForeignKey('permissions.code'), nullable=False)
    __table_args__ = (UniqueConstraint('role','permission'),)


class AccountSettings(Base):
    __tablename__ = "account_settings"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    options = Column(JSON, nullable=False, default=dict)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    device = Column(String(250), nullable=False)
    created_at = Column(DateTime, nullable=False, default=now)
    expires_at = Column(DateTime, nullable=False)


class EmailChange(Base):
    __tablename__ = "email_changes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    email = Column(String(255), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
