from app.security.tool_policy import TOOL_APPROVAL_POLICY, ApprovalPolicy

def plan_requires_approval(plan) -> bool:
    for step in plan.steps:
        policy = TOOL_APPROVAL_POLICY.get(step.name, ApprovalPolicy.AUTO)
        if policy == ApprovalPolicy.REQUIRE_APPROVAL:
            return True
    return False
