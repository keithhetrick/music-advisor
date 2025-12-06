"""
Example logging plugin that returns a structured logger factory.
"""
from adapters.logging_adapter import make_structured_logger


def factory(prefix: str = "", defaults=None):
    return make_structured_logger(prefix=prefix, defaults=defaults or {})
