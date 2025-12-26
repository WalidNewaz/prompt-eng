# ============================================================
# DB access layer
# ============================================================
from typing import Protocol, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
import json

from .entities import ApprovalRequestEntity as ApprovalRequest

class ApprovalRequestRepositoryProtocol(Protocol):
    def mark_approved(self, approval_id: str, approved_by: str) -> ApprovalRequest:
        """Mark approval as approved"""
        ...

    def mark_rejected(self, approval_id: str, approved_by: str) -> ApprovalRequest:
        """Mark approval as rejected"""
        ...

    def create_pending(
            self,
            trace_id: str,
            workflow: str,
            plan: dict[str, Any],
            requested_by: str,
    ) -> str:
        """Create a new pending approval"""
        ...

    def get(self, approval_id: str) -> ApprovalRequest:
        """Get an approval by id"""
        ...

class ApprovalRequestRepository(ApprovalRequestRepositoryProtocol):
    def __init__(self, db: Session):
        self.db = db

    def mark_approved(self, approval_id: str, approved_by: str) -> ApprovalRequest:
        """Mark approval as approved"""
        query = text("""
                UPDATE approval_requests
                SET
                    status = 'APPROVED',
                    decided_at = :decided_at,
                    decided_by = :decided_by
                WHERE id = :id
                """)
        params = {
            "id": approval_id,
            "decided_at": datetime.now(),
            "decided_by": approved_by,
        }

        result = self.db.execute(query, params)
        self.db.commit()
        return result

    def mark_rejected(self, approval_id: str, approved_by: str) -> ApprovalRequest:
        """Mark approval as rejected"""
        query = text("""
                UPDATE approval_requests
                SET
                    status = 'REJECTED',
                    decided_at = :decided_at,
                    decided_by = :decided_by
                WHERE id = :id
                """)
        params = {
            "id": approval_id,
            "decided_at": datetime.now(),
            "decided_by": approved_by,
        }

        result = self.db.execute(query, params)
        self.db.commit()
        return result

    def create_pending(
            self,
            trace_id: str,
            workflow: str,
            safe_user_request: str,
            plan: dict[str, Any],
            requested_by: str,
    ) -> str:
        """Create a new pending approval"""
        query = text("""
                INSERT INTO approval_requests (
                    trace_id,
                    workflow,
                    safe_user_request,
                    plan,
                    status,
                    requested_by,
                    requested_at
                ) VALUES (
                    :trace_id,
                    :workflow,
                    :safe_user_request,
                    :plan,
                    :status,
                    :requested_by,
                    :requested_at
                )
                RETURNING *
                """)
        params = {
            "trace_id": trace_id,
            "workflow": workflow,
            "safe_user_request": safe_user_request,
            "plan": json.dumps(plan, ensure_ascii=False),
            "status": 'PENDING',
            "requested_by": requested_by,
            "requested_at": datetime.now(),
        }
        result = self.db.execute(query, params)
        # approval_id = result.scalar_one()
        new_row = result.fetchone()
        print("new_row", new_row)
        self.db.commit()
        approval_id = new_row.id

        return approval_id


    def get(self, approval_id: str) -> ApprovalRequest:
        """Get an approval by id"""
        query = text("""
                SELECT * FROM approval_requests
                WHERE id = :id
                """)

        row = self.db.execute(query, {"id": approval_id}).mappings().one()
        return ApprovalRequest (
            id = approval_id,
            trace_id = row.trace_id,
            workflow = row.workflow,
            tool_name = row.tool_name,
            safe_user_request = row.safe_user_request,
            plan = json.loads(row.plan),
            reason = row.reason,
            status = row.status,
            requested_at = row.requested_at,
            decided_at = row.decided_at,
            decided_by = row.decided_by,
        )



