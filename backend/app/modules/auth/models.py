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
