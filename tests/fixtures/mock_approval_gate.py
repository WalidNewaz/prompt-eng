from unittest.mock import MagicMock

from src.domain.approval.entities import ApprovalGateResult

mock_approval_gate = MagicMock()
mock_approval_gate.evaluate.return_value = ApprovalGateResult(proceed=True)