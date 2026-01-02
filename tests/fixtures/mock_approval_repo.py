from unittest.mock import MagicMock

mock_approval_repo = MagicMock()
mock_approval_repo.create_pending.return_value = "approval_123"