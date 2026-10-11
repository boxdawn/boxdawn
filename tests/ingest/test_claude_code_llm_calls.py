"""tests/ingest/test_claude_code_llm_calls.py — CC adapter populates llm_calls.

Extends `docs/CONTEXT_RESEND_DETECTOR_PREREG.md` §3 schema to the Claude Code
JSONL adapter. Same metadata contract as the OpenInference adapter path —
`trace.metadata["llm_calls"]` is populated from assistant turns even though
the Span layer remains tool-only per §22.3 of CC_TRANSCRIPT.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


from clew.ingest.claude_code import ingest_claude_code_jsonl


def _write_jsonl(tmp_path: Path, entries: list[dict[str, Any]]) -> Path:
    p = tmp_path / "session.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return p


def _base_session_entries() -> list[dict[str, Any]]:
    """Minimum viable CC session: one user + one assistant with one tool_use +
    one user tool_result. Produces a single tool span pair.
    """
    return [
        {
            "type": "user",
            "sessionId": "sess-A",
            "uuid": "u-1",
            "timestamp": "2026-01-01T00:00:00.000Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "hi"}],
            },
        },
        {
            "type": "assistant",
            "sessionId": "sess-A",
            "uuid": "a-1",
            "timestamp": "2026-01-01T00:00:01.000Z",
            "message": {
                "id": "msg_001",
                "model": "claude-sonnet-4-6",
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool_001",
                        "name": "search",
                        "input": {"q": "hello"},
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 40,
                },
            },
        },
        {
            "type": "user",
            "sessionId": "sess-A",
            "uuid": "u-2",
            "timestamp": "2026-01-01T00:00:02.000Z",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_001",
                        "content": "result of hello search",
                    }
                ],
            },
        },
    ]


def test_llm_calls_populated_from_single_assistant_turn(tmp_path):
    p = _write_jsonl(tmp_path, _base_session_entries())
    trace = ingest_claude_code_jsonl(p)

    calls = trace.metadata["llm_calls"]
    assert len(calls) == 1
    entry = calls[0]
    assert entry["span_id"] == "msg_001"
    assert entry["model"] == "claude-sonnet-4-6"
    assert entry["input_tokens"] == 100
    assert entry["output_tokens"] == 40
    # No cost tables supplied — rates stay None (legacy fallback path).
    assert entry["input_cost_rate"] is None
    assert entry["output_cost_rate"] is None


def test_consecutive_same_message_id_entries_grouped(tmp_path):
    """Two consecutive assistant entries sharing message.id are ONE API call."""
    entries = _base_session_entries()
    # Insert a second block for the same message.id right after the first assistant entry.
    entries.insert(2, {
        "type": "assistant",
        "sessionId": "sess-A",
        "uuid": "a-1b",
        "timestamp": "2026-01-01T00:00:01.500Z",
        "message": {
            "id": "msg_001",  # same as previous assistant
            "model": "claude-sonnet-4-6",
            "role": "assistant",
            "content": [{"type": "text", "text": "thinking aloud"}],
            "usage": {
                "input_tokens": 100,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "output_tokens": 40,
            },
        },
    })
    p = _write_jsonl(tmp_path, entries)
    trace = ingest_claude_code_jsonl(p)

    # Only ONE llm_calls entry — the same message.id was grouped.
    calls = trace.metadata["llm_calls"]
    assert len(calls) == 1
    assert calls[0]["span_id"] == "msg_001"


def test_multiple_turns_input_text_grows_across_turns(tmp_path):
    """Each subsequent assistant turn's input_text includes prior turns."""
    entries = _base_session_entries()
    # Add a second full turn.
    entries.extend([
        {
            "type": "user",
            "sessionId": "sess-A",
            "uuid": "u-3",
            "timestamp": "2026-01-01T00:00:03.000Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "second question"}],
            },
        },
        {
            "type": "assistant",
            "sessionId": "sess-A",
            "uuid": "a-2",
            "timestamp": "2026-01-01T00:00:04.000Z",
            "message": {
                "id": "msg_002",
                "model": "claude-sonnet-4-6",
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool_002",
                        "name": "search",
                        "input": {"q": "again"},
                    }
                ],
                "usage": {
                    "input_tokens": 500,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 30,
                },
            },
        },
        {
            "type": "user",
            "sessionId": "sess-A",
            "uuid": "u-4",
            "timestamp": "2026-01-01T00:00:05.000Z",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_002",
                        "content": "result of again search",
                    }
                ],
            },
        },
    ])
    p = _write_jsonl(tmp_path, entries)
    trace = ingest_claude_code_jsonl(p)

    calls = trace.metadata["llm_calls"]
    assert len(calls) == 2
    # First call: user turn only (before its assistant).
    # Second call: user + assistant(tool_use) + user(tool_result) before it.
    assert len(calls[1]["input_text"]) > len(calls[0]["input_text"])


def test_cache_tokens_counted_as_input(tmp_path):
    """cache_read + cache_creation contribute to input_tokens per prereg §4."""
    entries = _base_session_entries()
    # Modify assistant usage to include cache tokens.
    for e in entries:
        if e["type"] == "assistant":
            e["message"]["usage"] = {
                "input_tokens": 3,
                "cache_read_input_tokens": 200,
                "cache_creation_input_tokens": 500,
                "output_tokens": 10,
            }
    p = _write_jsonl(tmp_path, entries)
    trace = ingest_claude_code_jsonl(p)

    entry = trace.metadata["llm_calls"][0]
    assert entry["input_tokens"] == 703  # 3 + 200 + 500


def test_cost_tables_pass_through(tmp_path):
    p = _write_jsonl(tmp_path, _base_session_entries())
    trace = ingest_claude_code_jsonl(
        p,
        input_cost_table={"claude-sonnet-4-6": 3e-6},
        output_cost_table={"claude-sonnet-4-6": 15e-6},
    )

    entry = trace.metadata["llm_calls"][0]
    assert entry["input_cost_rate"] == 3e-6
    assert entry["output_cost_rate"] == 15e-6


def test_no_assistant_turns_returns_empty_llm_calls(tmp_path):
    """Session with only user + system entries -> llm_calls empty."""
    entries = [
        {
            "type": "user",
            "sessionId": "sess-B",
            "uuid": "u-1",
            "timestamp": "2026-01-01T00:00:00.000Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "hi"}],
            },
        },
    ]
    p = _write_jsonl(tmp_path, entries)
    # No tool spans and no assistant → but adapter requires paired tool_use/result.
    # Use empty-tool recovery: no_tool_use path returns root-only Trace (§29.1).
    trace = ingest_claude_code_jsonl(p)
    assert trace.metadata["llm_calls"] == []


def _same_id_block_after_tool_result() -> list[dict[str, Any]]:
    """One API call whose blocks straddle the tool_result line it produced.

    This is the real Claude Code shape for parallel/sequential tool use: the
    assistant's tool_use block is written, the tool runs and its result is
    written as a `user` line, and the next content block of the SAME API call
    follows. Every one of those assistant lines repeats the same usage record.
    """
    entries = _base_session_entries()
    entries.append({
        "type": "assistant",
        "sessionId": "sess-A",
        "uuid": "a-1c",
        "timestamp": "2026-01-01T00:00:03.000Z",
        "message": {
            "id": "msg_001",  # same API call as the first assistant entry
            "model": "claude-sonnet-4-6",
            "role": "assistant",
            "content": [{"type": "text", "text": "second block"}],
            "usage": {
                "input_tokens": 100,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "output_tokens": 40,
            },
        },
    })
    return entries


def test_same_message_id_across_tool_result_is_one_call(tmp_path):
    """A user tool_result between two blocks does not split one API call.

    Grouping on adjacency alone restarted the group here and added the
    repeated usage a second time: on the cited trace that counted 39 calls
    for 27 billed ones and inflated total_analyzed_cost by 1.523x.
    """
    p = _write_jsonl(tmp_path, _same_id_block_after_tool_result())
    trace = ingest_claude_code_jsonl(p)

    calls = trace.metadata["llm_calls"]
    assert len(calls) == 1
    # The charge is counted once, not once per content block.
    assert calls[0]["input_tokens"] == 100
    assert calls[0]["output_tokens"] == 40


def test_reopened_group_reports_its_count_and_a_clean_usage_check(tmp_path):
    """The merge is reported, and so is the 0 that says the copies agreed."""
    p = _write_jsonl(tmp_path, _same_id_block_after_tool_result())
    notes = ingest_claude_code_jsonl(p).metadata["ingest_notes"]

    assert notes["api_call_merge_count"] == 1
    assert notes["usage_conflict_count"] == 0


def test_disagreeing_usage_copies_are_counted_not_hidden(tmp_path):
    """Same id, different usage: still one call, but the conflict is surfaced.

    Which line is the billed one is undecided in that shape, so the count has
    to reach the report instead of being absorbed by picking the first.
    """
    entries = _same_id_block_after_tool_result()
    entries[-1]["message"]["usage"]["cache_read_input_tokens"] = 777
    p = _write_jsonl(tmp_path, entries)
    trace = ingest_claude_code_jsonl(p)

    assert len(trace.metadata["llm_calls"]) == 1
    assert trace.metadata["ingest_notes"]["usage_conflict_count"] == 1


def test_file_with_nothing_to_merge_stays_silent(tmp_path):
    """No reopened group, no keys — the ordinary file reports nothing."""
    p = _write_jsonl(tmp_path, _base_session_entries())
    notes = ingest_claude_code_jsonl(p).metadata["ingest_notes"]

    assert "api_call_merge_count" not in notes
    assert "usage_conflict_count" not in notes


def _with_cache_creation(ttl_1h: int, ttl_5m: int, total: int) -> list[dict[str, Any]]:
    entries = _base_session_entries()
    for e in entries:
        if e.get("type") != "assistant":
            continue
        e["message"]["usage"] = {
            "input_tokens": 10,
            "cache_read_input_tokens": 100,
            "cache_creation_input_tokens": total,
            "cache_creation": {
                "ephemeral_1h_input_tokens": ttl_1h,
                "ephemeral_5m_input_tokens": ttl_5m,
            },
            "output_tokens": 40,
        }
    return entries


def test_one_hour_writes_are_carried_separately(tmp_path):
    p = _write_jsonl(tmp_path, _with_cache_creation(ttl_1h=800, ttl_5m=200, total=1000))
    calls = ingest_claude_code_jsonl(p).metadata["llm_calls"]

    assert calls[0]["input_tokens_cache_write"] == 1000
    assert calls[0]["input_tokens_cache_write_1h"] == 800


def test_a_sub_object_that_does_not_add_up_is_counted_not_guessed(tmp_path):
    """If the parts miss the total, which part bills at 1h is undecided.

    The whole write then prices at the 5-minute rate — the lower, older
    answer — and the count reaches the report instead of rounding upward.
    """
    p = _write_jsonl(tmp_path, _with_cache_creation(ttl_1h=800, ttl_5m=100, total=1000))
    trace = ingest_claude_code_jsonl(p)

    assert trace.metadata["llm_calls"][0]["input_tokens_cache_write_1h"] == 0
    assert trace.metadata["ingest_notes"]["cache_creation_ttl_mismatch_count"] == 1


def test_no_sub_object_means_no_one_hour_share(tmp_path):
    """Adapters that do not record the TTL keep the pre-existing behaviour."""
    p = _write_jsonl(tmp_path, _base_session_entries())
    trace = ingest_claude_code_jsonl(p)

    assert trace.metadata["llm_calls"][0]["input_tokens_cache_write_1h"] == 0
    assert "cache_creation_ttl_mismatch_count" not in trace.metadata["ingest_notes"]


# ── turns are API calls, not JSONL lines (CC_USAGE_ATTRIBUTION_DECISION §12) ──

def test_total_turns_counts_api_calls_not_assistant_lines(tmp_path):
    """`cc_total_turns` named the line count.

    The fixture is one API call written as two assistant lines around the
    tool_result it produced. Per line it is 2; the model was called once, and
    the report renders this number as "of N total" turns.
    """
    p = _write_jsonl(tmp_path, _same_id_block_after_tool_result())
    trace = ingest_claude_code_jsonl(p)

    assert trace.metadata["cc_total_turns"] == 1


def test_total_turns_equals_the_number_of_llm_calls(tmp_path):
    """Two descriptions of "how many API calls" that must not drift.

    `_extract_llm_calls` and `_collect_cc_usage_metadata` group by the same
    rule; if only one of them changes, this is what notices.
    """
    for entries in (_base_session_entries(),
                    _same_id_block_after_tool_result(),
                    _two_calls_second_one_split()):
        p = _write_jsonl(tmp_path, entries)
        trace = ingest_claude_code_jsonl(p)
        assert trace.metadata["cc_total_turns"] == len(trace.metadata["llm_calls"])


def _two_calls_second_one_split() -> list[dict[str, Any]]:
    """Two API calls, the second written as two lines with its own usage copy."""
    entries = _same_id_block_after_tool_result()          # call msg_001, 2 lines
    for suffix, block in (("b1", {"type": "tool_use", "id": "t-9", "name": "Read",
                                  "input": {"file_path": "/x"}}),
                          ("b2", {"type": "text", "text": "and done"})):
        entries.append({
            "type": "assistant",
            "sessionId": "sess-A",
            "uuid": f"a-2{suffix}",
            "timestamp": "2026-01-01T00:00:1" + suffix[-1] + ".000Z",
            "message": {
                "id": "msg_002",
                "model": "claude-sonnet-4-6",
                "role": "assistant",
                "content": [block],
                "usage": {
                    "input_tokens": 700,
                    "cache_read_input_tokens": 11,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 9,
                },
            },
        })
    return entries


def test_turn_index_numbers_calls_so_the_second_call_is_turn_two(tmp_path):
    """Four assistant lines, two API calls: the later tool_use is turn 2.

    Line-based numbering made it turn 3, and `cc_total_turns` 4 — so the
    report said "turn 3 of 4" for the second of two model turns.
    """
    p = _write_jsonl(tmp_path, _two_calls_second_one_split())
    trace = ingest_claude_code_jsonl(p)

    assert trace.metadata["cc_total_turns"] == 2
    assert trace.metadata["cc_turn_index"]["t-9"] == 2
    # The first call's tool_use keeps turn 1.
    assert trace.metadata["cc_turn_index"]["tool_001"] == 1


def test_next_usage_is_the_following_call_not_the_same_calls_copy(tmp_path):
    """Why the amplification estimator was discarding real events.

    `next` used to be the next assistant *line*. Inside a multi-block call
    that line is the same call repeating its own usage, so
    `cost/amplification.py::_prev_equals_next` read it as duplicate/retry
    usage and dropped the event. It has to be the following API call's usage.
    """
    from clew.cost.amplification import _prev_equals_next

    p = _write_jsonl(tmp_path, _two_calls_second_one_split())
    trace = ingest_claude_code_jsonl(p)

    pair = trace.metadata["cc_usage_pair"]["tool_001"]
    assert pair["prev"]["input_tokens"] == 100          # its own call
    assert pair["next"]["input_tokens"] == 700          # the *next* call
    assert not _prev_equals_next(pair["prev"], pair["next"])

    # The last call has nothing after it.
    assert trace.metadata["cc_usage_pair"]["t-9"]["next"] is None


def test_an_assistant_line_without_a_message_id_is_its_own_turn(tmp_path):
    """Matches what `_extract_llm_calls` does with it, which is what keeps
    `cc_total_turns == len(llm_calls)` true rather than true by luck."""
    entries = _base_session_entries()
    entries.append({
        "type": "assistant",
        "sessionId": "sess-A",
        "uuid": "a-noid",
        "timestamp": "2026-01-01T00:00:09.000Z",
        "message": {
            "model": "claude-sonnet-4-6",
            "role": "assistant",
            "content": [{"type": "text", "text": "no id on this one"}],
            "usage": {
                "input_tokens": 5,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "output_tokens": 1,
            },
        },
    })
    p = _write_jsonl(tmp_path, entries)
    trace = ingest_claude_code_jsonl(p)

    assert trace.metadata["cc_total_turns"] == 2
    assert trace.metadata["cc_total_turns"] == len(trace.metadata["llm_calls"])
