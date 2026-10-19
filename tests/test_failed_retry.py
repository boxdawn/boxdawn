"""tests/test_failed_retry.py — Failed Retry Detector (docs/FAILED_RETRY_DETECTOR_PREREG.md §4 P5).

A failing tool call followed by a failing call to the same tool is one event,
on every OpenTelemetry entry point. A different tool is not. Claude Code
traces never produce one, whatever their `error_span_ids`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from clew.detect.failed_retry import find_failed_retries
from clew.ingest.otel_json import ingest_from_openinference_json, ingest_from_otel_json
from clew.model import Span, Trace

_TID = "aabbccdd112233440000000011223344"


def _sdk(name, sid, parent, kind, second, status="OK"):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=second)
    return {
        "name": name,
        "context": {"trace_id": "0x" + _TID, "span_id": "0x" + sid, "trace_state": "[]"},
        "kind": "SpanKind.INTERNAL",
        "parent_id": ("0x" + parent) if parent else None,
        "start_time": t0.isoformat().replace("+00:00", "Z"),
        "end_time": (t0 + timedelta(milliseconds=500)).isoformat().replace("+00:00", "Z"),
        "status": {"status_code": status},
        "attributes": {"openinference.span.kind": kind, "input.value": "{}", "output.value": "out"},
        "events": [], "links": [],
        "resource": {"attributes": {"service.name": "test"}, "schema_url": ""},
    }


def _format_a(tmp_path, second_tool: str):
    spans = [
        _sdk("root", "0000000000000001", None, "CHAIN", 0),
        _sdk("page_down", "0000000000000002", "0000000000000001", "TOOL", 1, "ERROR"),
        _sdk(second_tool, "0000000000000003", "0000000000000001", "TOOL", 2, "ERROR"),
    ]
    p = tmp_path / "a.json"
    p.write_text(json.dumps(spans), encoding="utf-8")
    return ingest_from_otel_json(p)


def test_format_a_same_tool_twice_is_one_event(tmp_path):
    trace = _format_a(tmp_path, "page_down")
    assert sorted(trace.metadata["error_span_ids"]) == ["0000000000000002", "0000000000000003"]
    pairs = find_failed_retries(trace)
    assert [(a.span_id, b.span_id) for a, b in pairs] == [("0000000000000002", "0000000000000003")]


def test_format_a_different_tool_is_none(tmp_path):
    assert find_failed_retries(_format_a(tmp_path, "visit_page")) == []


def test_format_a_ok_status_records_nothing(tmp_path):
    spans = [
        _sdk("root", "0000000000000001", None, "CHAIN", 0),
        _sdk("page_down", "0000000000000002", "0000000000000001", "TOOL", 1),
        _sdk("page_down", "0000000000000003", "0000000000000001", "TOOL", 2),
    ]
    p = tmp_path / "a.json"
    p.write_text(json.dumps(spans), encoding="utf-8")
    trace = ingest_from_otel_json(p)
    assert "error_span_ids" not in trace.metadata
    assert find_failed_retries(trace) == []


def _oi(sid, parent, name, kind, second, status="Ok", children=None):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=second)
    return {
        "span_id": sid, "parent_span_id": parent, "trace_id": _TID,
        "span_name": name, "timestamp": t0.isoformat().replace("+00:00", "Z"),
        "duration": "PT0.5S", "status_code": status,
        "span_attributes": {"openinference.span.kind": kind, "input.value": "{}", "output.value": "out"},
        "child_spans": children or [],
    }


def test_format_c_same_tool_twice_is_one_event(tmp_path):
    root = _oi("0000000000000001", None, "root", "CHAIN", 0, children=[
        _oi("0000000000000002", "0000000000000001", "PageDownTool", "TOOL", 1, "Error"),
        _oi("0000000000000003", "0000000000000001", "PageDownTool", "TOOL", 2, "Error"),
    ])
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"trace_id": _TID, "spans": [root]}), encoding="utf-8")
    pairs = find_failed_retries(ingest_from_openinference_json(p))
    assert [(a.span_id, b.span_id) for a, b in pairs] == [("0000000000000002", "0000000000000003")]


def test_live_readable_spans_one_event():
    pytest.importorskip("opentelemetry.sdk.trace")
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import Status, StatusCode

    from clew.ingest.langgraph import ingest_otel_spans

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("t")
    with tracer.start_as_current_span("root") as root:
        root.set_attribute("openinference.span.kind", "CHAIN")
        root.set_attribute("output.value", "out")
        for _ in range(2):
            with tracer.start_as_current_span("page_down") as s:
                s.set_attribute("openinference.span.kind", "TOOL")
                s.set_attribute("input.value", "{}")
                s.set_attribute("output.value", "error")
                s.set_status(Status(StatusCode.ERROR))
    trace = ingest_otel_spans(list(exporter.get_finished_spans()))
    assert len(find_failed_retries(trace)) == 1


def test_claude_code_source_never_fires():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def span(sid, parent, kind, sec):
        return Span(trace_id="t", span_id=sid, parent_span_id=parent, agent_or_node_id="Bash",
                    span_kind=kind, start_time=t0 + timedelta(seconds=sec),
                    end_time=t0 + timedelta(seconds=sec), input_text="x", output_text="Exit code 1")

    trace = Trace(trace_id="t", spans=[span("r", None, "chain", 0), span("a", "r", "tool", 1),
                                       span("b", "r", "tool", 2)],
                  metadata={"source": "claude_code_jsonl", "error_span_ids": ["a", "b"]})
    assert find_failed_retries(trace) == []


def test_reports_carry_it_only_when_present(tmp_path):
    from clew.detect.cascade import CascadeResult
    from clew.report.json_report import render_json
    from clew.report.markdown import render_markdown

    hit = _format_a(tmp_path, "page_down")
    cr = CascadeResult(trace_id=hit.trace_id, wasteful=False)
    assert json.loads(render_json(hit, cr, []))["failed_retries"] == [
        {"tool": "page_down", "failed_span_id": "0000000000000002",
         "retry_span_id": "0000000000000003"}
    ]
    md = render_markdown(hit, cr, [])
    assert "## Failed retries" in md and "context" not in md.split("## Failed retries")[1].split("##")[0]

    miss = _format_a(tmp_path, "visit_page")
    assert "failed_retries" not in json.loads(render_json(miss, cr, []))
    assert "## Failed retries" not in render_markdown(miss, cr, [])
