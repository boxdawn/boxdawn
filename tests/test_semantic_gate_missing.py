"""tests/test_semantic_gate_missing.py — a trace this install cannot finish says so.

The semantic gate loads its model on the first non-tool pair, not at import, so
the import guard in `_analyze` never sees it. A base install therefore analyses
a tool-only trace to completion and fails only on a trace that repeats a
non-tool span -- and which traces those are is not something the caller knows
beforehand.

Measured 2026-09-09 on a clean `pip install boxdawn==0.5.10` (no torch, empty
embedding cache): all three OpenInference fixtures in this repo exited 1 with a
traceback out of `semantic.py` and wrote no report, while a real Claude Code
session, an external one, and `examples/sample_otel_trace.json` all finished
normally. The scope README states was right. The failure shape was not: a
traceback reads as a broken install rather than as a trace that needs one more
package.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from clew.__main__ import main


def _non_tool_repeat_trace(path: Path) -> Path:
    """Native Trace JSON whose only repeated pair is a chain span.

    `chain` rather than `llm` on purpose: the gate is `span_kind != "tool"`
    (`detect/cascade.py`), not `llm`, and reading it as llm-only is what made
    the first estimate of this defect too narrow.
    """
    span = {
        "trace_id": "t-gate",
        "parent_span_id": "root",
        "agent_or_node_id": "planner",
        "span_kind": "chain",
        "input_text": "summarise the plan",
        "output_text": "build, verify, promote.",
    }
    path.write_text(json.dumps({
        "trace_id": "t-gate",
        "spans": [
            {
                "trace_id": "t-gate",
                "span_id": "root",
                "parent_span_id": None,
                "agent_or_node_id": "session",
                "span_kind": "chain",
                "start_time": "2026-09-09T00:00:00Z",
                "end_time": "2026-09-09T00:00:30Z",
                "input_text": "",
                "output_text": "",
            },
            {**span, "span_id": "c1",
             "start_time": "2026-09-09T00:00:01Z", "end_time": "2026-09-09T00:00:05Z"},
            {**span, "span_id": "c2",
             "start_time": "2026-09-09T00:00:10Z", "end_time": "2026-09-09T00:00:14Z"},
        ],
    }), encoding="utf-8")
    return path


def test_missing_semantic_extra_explains_the_trace_not_the_install(
    tmp_path, monkeypatch, capsys,
):
    trace = _non_tool_repeat_trace(tmp_path / "trace.json")
    out = tmp_path / "report.md"

    # Point the embedding cache at an empty directory. A machine that once had
    # the extra installed keeps vectors keyed on (model, revision, text), so a
    # warm cache satisfies the gate with no torch present and this defect goes
    # invisible on a developer's own machine.
    monkeypatch.setattr("clew.__main__._CACHE_DIR", tmp_path / "embeddings")
    # Break the import rather than stubbing `_load_model`: the install command
    # is named in exactly one place (`semantic.py`), and a stub that invents its
    # own message would let this test pass while the shipped sentence lost the
    # line that tells the caller what to run. `None` in `sys.modules` is what
    # makes `import torch` raise.
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setattr(sys, "argv", ["boxdawn", "analyze", str(trace), "--out", str(out)])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "not a tool call" in err
    assert "boxdawn[semantic]" in err
    # The point of the change: the caller is told which trace this install
    # cannot finish, instead of reading a stack.
    assert "Traceback" not in err
    # Nothing half-written. A report that stops before the cascade would be a
    # measured zero for detectors that never ran.
    assert not out.exists()
