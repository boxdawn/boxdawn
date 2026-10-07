"""Stage 4 Phase 1: suppress redundant reads at the tool-call boundary.

Design: docs/STAGE4_AUTOFIX_DESIGN.md (Phase 1 section).

Requires the `adapter` extra (`pip install "boxdawn[adapter]"`) — the wrapper
sits on `langchain_core.tools.BaseTool`, which is not a base dependency.
"""
from __future__ import annotations

from clew.autofix.tool_cache import ToolCache, ToolCacheReport

__all__ = ["ToolCache", "ToolCacheReport"]
