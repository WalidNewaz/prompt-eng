def normalize_usage(obj):
    """
    Normalize LLM usage metadata into a plain dict.
    Safe across dicts, objects, pydantic models, or None.
    """
    if obj is None:
        return None

    if isinstance(obj, dict):
        return obj

    # Pydantic v2
    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    # Pydantic v1
    if hasattr(obj, "dict"):
        return obj.dict()

    # Dataclass / SimpleNamespace / generic object
    if hasattr(obj, "__dict__"):
        return vars(obj)

    # Fallback (last resort)
    return {"value": str(obj)}
