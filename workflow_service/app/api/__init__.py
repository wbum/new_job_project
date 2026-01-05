# Expose api submodules as package attributes so code that does
# `from .api import health` works as expected.
from . import health, records, reports

__all__ = ["health", "records", "reports"]
