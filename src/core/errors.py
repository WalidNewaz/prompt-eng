# ---------------------------------
# TYPED EXCEPTIONS
# ---------------------------------


class LLMParseError(Exception):
    pass

class OrchestrationError(RuntimeError):
    """Raised when orchestration fails after retries."""
    pass