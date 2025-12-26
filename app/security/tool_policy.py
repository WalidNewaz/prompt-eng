from enum import Enum

class ApprovalPolicy(str, Enum):
    AUTO = "auto"
    REQUIRE_APPROVAL = "require_approval"


TOOL_APPROVAL_POLICY = {
    "send_slack_message": ApprovalPolicy.REQUIRE_APPROVAL,
    "send_email": ApprovalPolicy.REQUIRE_APPROVAL,
    "request_missing_info": ApprovalPolicy.AUTO,
}
