# Fields required by each step of a plan.
# These fields are required by the associated tool.

REQUIRED_FIELDS = {
    "send_slack_message": ["channel", "text"],
    "send_email": ["to", "subject", "body"],
}