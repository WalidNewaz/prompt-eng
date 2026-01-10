# ============================================================
# DB access layer
# ============================================================
from typing import Protocol, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
import json

from src.api.schemas import ApprovalFilters
from src.domain.approval.entities import (
    ApprovalRequestEntity as ApprovalRequest,
    Pagination,
    Sorting,
    PageResult,
    PageMeta
)

class ApprovalRequestRepositoryProtocol(Protocol):
    def mark_approved(self, approval_id: str, approved_by: str) -> ApprovalRequest:
        """Mark approval as approved"""
        ...

    def mark_rejected(self, approval_id: str, approved_by: str, reason: str) -> ApprovalRequest:
        """Mark approval as rejected"""
        ...

    def create_pending(
            self,
            trace_id: str,
            workflow: str,
            safe_user_request: str,
            tool_name: str,
            plan: dict[str, Any],
            reason: str,
            requested_by: str,
    ) -> str:
        """Create a new pending approval"""
        ...

    def get(self, approval_id: str) -> ApprovalRequest:
        """Get an approval by id"""
        ...

    def get_all(self) -> list[ApprovalRequest]:
        """Get all approvals"""
        ...

class ApprovalRequestRepository(ApprovalRequestRepositoryProtocol):
    # Allowed sort columns at persistence layer (defense in depth)
    _SORT_COLUMNS = {
        "requested_at": "requested_at",
        "status": "status",
        "workflow": "workflow",
    }

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

    def mark_rejected(
            self,
            approval_id: str,
            approved_by: str,
            reason: str,
    ) -> ApprovalRequest:
        """Mark approval as rejected"""
        query = text("""
                UPDATE approval_requests
                SET
                    status = 'REJECTED',
                    reason = :reason,
                    decided_at = :decided_at,
                    decided_by = :decided_by
                WHERE id = :id
                RETURNING *
                """)
        params = {
            "id": approval_id,
            "decided_at": datetime.now(),
            "decided_by": approved_by,
            "reason": reason,
        }

        result = self.db.execute(query, params)
        row = result.mappings().fetchone()

        self.db.commit()
        return ApprovalRequest(**row)

    def create_pending(
            self,
            trace_id: str,
            workflow: str,
            safe_user_request: str,
            tool_name: str,
            plan: dict[str, Any],
            reason: str,
            requested_by: str,
    ) -> str:
        """Create a new pending approval"""
        query = text("""
                INSERT INTO approval_requests (
                    trace_id,
                    workflow,
                    tool_name,
                    safe_user_request,
                    plan,
                    reason,
                    status,
                    requested_at,
                    requested_by
                ) VALUES (
                    :trace_id,
                    :workflow,
                    :tool_name,
                    :safe_user_request,
                    :plan,
                    :reason,
                    :status,
                    :requested_at,
                    :requested_by
                )
                RETURNING *
                """)
        params = {
            "trace_id": trace_id,
            "workflow": workflow,
            "tool_name": tool_name,
            "safe_user_request": safe_user_request,
            "plan": json.dumps(plan, ensure_ascii=False),
            "reason": reason,
            "status": 'PENDING',
            "requested_at": datetime.now(),
            "requested_by": requested_by,
        }
        result = self.db.execute(query, params)
        new_row = result.fetchone()
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

    def get_all(
            self,
            filters: ApprovalFilters,
            paging: Pagination,
            sorting: Sorting
    ) -> PageResult:
        """
        Retrieve approval requests matching the given filters.

        All filters are optional.
        Pagination is always applied.
        """
        conditions: list[str] = []
        params: dict[str, object] = {}

        # --- Filters ---
        if filters.status:
            conditions.append("status = :status")
            params["status"] = filters.status.value

        if filters.requested_by:
            conditions.append("requested_by = :requested_by")
            params["requested_by"] = filters.requested_by

        if filters.decided_by:
            conditions.append("decided_by = :decided_by")
            params["decided_by"] = filters.decided_by

        if filters.workflow:
            conditions.append("workflow = :workflow")
            params["workflow"] = filters.workflow

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # --- Total Count ---
        count_query = text(f"""
            SELECT COUNT(*) AS total
            FROM approval_requests
            {where_clause}
        """)

        total = int(self.db.execute(count_query, params).scalar_one())

        # ORDER BY: use allow-list mapping (cannot bind column names safely)
        sort_col = self._SORT_COLUMNS.get(sorting.sort_by, "requested_at")
        sort_dir = "ASC" if sorting.sort_order == "asc" else "DESC"
        order_clause = f"ORDER BY {sort_col} {sort_dir}"

        # --- Data Query ---
        data_query = text(f"""
            SELECT *
            FROM approval_requests
            {where_clause}
            {order_clause}
            LIMIT :limit
            OFFSET :offset
        """)

        params["limit"] = filters.limit
        params["offset"] = filters.offset

        result = self.db.execute(data_query, params)

        records = [
            ApprovalRequest(**row)
            for row in result.mappings()
        ]

        # --- Pagination Metadata ---
        meta = PageMeta(
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            has_next=(filters.offset + filters.limit) < total,
            has_previous=filters.offset > 0,
        )

        return PageResult(
            data=records,
            meta=meta
        )



