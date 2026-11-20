"""papersift: find and rank research papers with LLMs."""

__version__ = "0.1.0"

from papersift.core import Scout, ScoutResult  # noqa: E402
from papersift.models import Paper  # noqa: E402

__all__ = ["Paper", "Scout", "ScoutResult", "__version__"]
