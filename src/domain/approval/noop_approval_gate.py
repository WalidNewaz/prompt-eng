from .entities import ApprovalGateResult

class NoopApprovalGate:
    def evaluate(self, **kwargs) -> ApprovalGateResult:
        return ApprovalGateResult(proceed=True)
