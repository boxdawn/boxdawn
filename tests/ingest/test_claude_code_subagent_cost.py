"""CC adapter counts subagent transcripts (docs/CC_SUBAGENT_COST_PREREG.md §3)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from clew import guard
from clew.ingest.claude_code import ingest_claude_code_jsonl
from clew.report._model import build_cost_summary


def _write_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")


def _user(uuid: str, ts: str, text: str) -> dict[str, Any]:
    return {"type": "user", "sessionId": "sess-A", "uuid": uuid, "timestamp": ts,
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


def _assistant(uuid: str, ts: str, mid: str | None, model: str, *,
               inp: int, read: int = 0, write: int = 0, out: int = 1) -> dict[str, Any]:
    message: dict[str, Any] = {
        "model": model, "role": "assistant",
        "content": [{"type": "text", "text": f"reply {uuid}"}],
        "usage": {"input_tokens": inp, "cache_read_input_tokens": read,
                  "cache_creation_input_tokens": write, "output_tokens": out},
    }
    if mid is not None:
        message["id"] = mid
    return {"type": "assistant", "sessionId": "sess-A", "uuid": uuid,
            "timestamp": ts, "message": message}


@pytest.fixture
def session(tmp_path: Path) -> Path:
    main = tmp_path / "proj" / "sess-A.jsonl"
    _write_jsonl(main, [
        _user("u-1", "2026-01-01T00:00:00.000Z", "hi"),
        _assistant("a-1", "2026-01-01T00:00:01.000Z", "msg_main", "claude-opus-4-7",
                   inp=100, read=1000, write=500, out=50),
    ])
    _write_jsonl(main.with_suffix("") / "subagents" / "agent-x1.jsonl", [
        _user("su-1", "2026-01-01T00:00:02.000Z", "look around"),
        _assistant("sa-1", "2026-01-01T00:00:03.000Z", "msg_sub1", "claude-haiku-4-5",
                   inp=200, out=20),
        _user("su-2", "2026-01-01T00:00:04.000Z", "more"),
        _assistant("sa-2", "2026-01-01T00:00:05.000Z", "msg_sub2", "claude-haiku-4-5",
                   inp=10, read=300, out=5),
    ])
    return main


def test_subagent_calls_are_appended_with_their_conversation(session):
    trace = ingest_claude_code_jsonl(session)
    calls = trace.metadata["llm_calls"]
    assert [c["span_id"] for c in calls] == ["msg_main", "msg_sub1", "msg_sub2"]
    assert [c["conversation"] for c in calls] == ["main", "x1", "x1"]
    assert trace.metadata["ingest_notes"]["subagent_files"] == 1
    assert trace.metadata["ingest_notes"]["subagent_llm_calls"] == 2
    # Each subagent history is rebuilt from its own file, not the main one.
    assert "hi" not in calls[1]["input_text"]
    assert "look around" in calls[2]["input_text"]


def test_report_total_equals_the_guard(session):
    trace = ingest_claude_code_jsonl(session)
    summary = build_cost_summary(trace, None, None)
    assert summary.total_analyzed_cost == pytest.approx(guard.session_cost(session)["usd"])


def test_turn_metadata_stays_main_only(session):
    trace = ingest_claude_code_jsonl(session)
    main_calls = [c for c in trace.metadata["llm_calls"] if c["conversation"] == "main"]
    assert trace.metadata["cc_total_turns"] == len(main_calls) == 1


def test_without_subagents_the_trace_is_unchanged(session, tmp_path):
    bare = tmp_path / "bare" / "sess-A.jsonl"
    bare.parent.mkdir()
    bare.write_bytes(session.read_bytes())
    with_sub = ingest_claude_code_jsonl(session)
    without = ingest_claude_code_jsonl(bare)
    assert [c["span_id"] for c in without.metadata["llm_calls"]] == ["msg_main"]
    assert "conversation" not in without.metadata["llm_calls"][0]
    assert "subagent_files" not in without.metadata["ingest_notes"]
    main_only = {k: v for k, v in with_sub.metadata["llm_calls"][0].items()
                 if k != "conversation"}
    assert main_only == without.metadata["llm_calls"][0]


def test_a_message_id_already_counted_is_skipped(session):
    sub_dir = session.with_suffix("") / "subagents"
    _write_jsonl(sub_dir / "agent-x2.jsonl", [
        _user("du-1", "2026-01-01T00:00:06.000Z", "dup"),
        _assistant("da-1", "2026-01-01T00:00:07.000Z", "msg_sub1", "claude-haiku-4-5",
                   inp=200, out=20),
    ])
    trace = ingest_claude_code_jsonl(session)
    ids = [c["span_id"] for c in trace.metadata["llm_calls"]]
    assert ids.count("msg_sub1") == 1
    summary = build_cost_summary(trace, None, None)
    assert summary.total_analyzed_cost == pytest.approx(guard.session_cost(session)["usd"])


def test_a_call_without_message_id_gets_a_unique_span_id(session):
    sub_dir = session.with_suffix("") / "subagents"
    _write_jsonl(sub_dir / "agent-x2.jsonl", [
        _user("nu-1", "2026-01-01T00:00:06.000Z", "no id"),
        _assistant("na-1", "2026-01-01T00:00:07.000Z", None, "claude-haiku-4-5",
                   inp=7, out=1),
    ])
    trace = ingest_claude_code_jsonl(session)
    ids = [c["span_id"] for c in trace.metadata["llm_calls"]]
    assert len(ids) == len(set(ids))
    assert ids[-1].startswith("cc-llm-x2-")
