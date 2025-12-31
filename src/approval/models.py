from sqlalchemy import (
    Column, String, DateTime, JSON, Enum, Text, Integer,
)
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class ApprovalStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)  # UUID
    trace_id = Column(String, index=True)
    workflow = Column(String)
    tool_name = Column(String)
    safe_user_request = Column(String)
    plan = Column(JSON)          # Full plan snapshot
    reason = Column(Text)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    requested_at = Column(DateTime, default=datetime.utcnow)
    requested_by = Column(String),
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(String, nullable=True)
