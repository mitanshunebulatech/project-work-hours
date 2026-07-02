from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # "admin" or "employee"

    # Relationship to work entries
    work_entries = relationship("WorkEntry", back_populates="employee", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(200), unique=True, nullable=False)

    # Relationship to work entries
    work_entries = relationship("WorkEntry", back_populates="project", cascade="all, delete-orphan")


class WorkEntry(Base):
    __tablename__ = "work_entries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    date = Column(Date, nullable=False)
    hours_worked = Column(Float, nullable=False)
    remarks = Column(Text, nullable=True)

    # Relationships
    employee = relationship("User", back_populates="work_entries")
    project = relationship("Project", back_populates="work_entries")
