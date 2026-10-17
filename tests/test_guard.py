"""clew.guard — session pricing, the hook verdict, and settings merge/removal."""
from __future__ import annotations

import json

import pytest

from clew import guard
from clew.cost.pricing import resolve_pricing


def _assistant(mid, model, *, inp=0, read=0, write=0, out=0, w1h=None):
    usage = {
        "input_tokens": inp,
        "cache_read_input_tokens": read,
        "cache_creation_input_tokens": write,
        "output_tokens": out,
    }
    if w1h is not None:
        usage["cache_creation"] = {
            "ephemeral_1h_input_tokens": w1h,
            "ephemeral_5m_input_tokens": write - w1h,
        }
    return {"type": "assistant", "message": {"id": mid, "model": model, "usage": usage}}


def _write_jsonl(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")


def _usd(model, *, inp=0, read=0, write5=0, write1h=0, out=0):
    p, _ = resolve_pricing(model)
    return (inp * p.base_input_per_mtok + read * p.cache_read_per_mtok
            + write5 * p.cache_write_5m_per_mtok + write1h * p.cache_write_1h_per_mtok
            + out * p.output_per_mtok) / 1_000_000


@pytest.fixture
def session(tmp_path):
    main = tmp_path / "proj" / "s1.jsonl"
    call_a = _assistant("msg_a", "claude-opus-4-7", inp=100, read=1000, write=500, out=50, w1h=500)
    _write_jsonl(main, [
        {"type": "user", "message": {"content": "hi"}},
        call_a,
        call_a,  # second content block of the same call repeats its usage
        _assistant("msg_syn", "<synthetic>"),  # zero usage: not a call
    ])
    _write_jsonl(main.with_suffix("") / "subagents" / "agent-x.jsonl", [
        _assistant("msg_b", "claude-haiku-5-5", inp=200, out=20),
    ])
    return main


def test_session_cost_dedupes_by_message_id_and_reads_subagents(session):
    cost = guard.session_cost(session)
    expected = (_usd("claude-opus-4-7", inp=100, read=1000, write1h=500, out=50)
                + _usd("claude-haiku-5-5", inp=200, out=20))
    assert cost["calls"] == 2
    assert cost["usd"] == pytest.approx(expected)
    assert cost["unpriced_models"] == []


def test_unknown_model_is_counted_and_named(tmp_path):
    main = tmp_path / "s.jsonl"
    _write_jsonl(main, [_assistant("m1", "claude-opus-9-9", inp=1000, out=10)])
    cost = guard.session_cost(main)
    assert cost["usd"] > 0
    assert cost["unpriced_models"] == ["claude-opus-9-9"]
    _, out = guard.decide(cost, cap_usd=cost["usd"] / 2, warn_at=None)
    assert "lower bound" in out["stopReason"]


def test_missing_transcript_costs_nothing(tmp_path):
    assert guard.session_cost(tmp_path / "none.jsonl") == {
        "usd": 0.0, "calls": 0, "unpriced_models": []}


def test_decide_deny_carries_both_fields():
    verdict, out = guard.decide({"usd": 5.0, "unpriced_models": []}, 5.0, None)
    assert verdict == "deny"
    assert out["continue"] is False
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


def test_decide_warn_and_allow():
    assert guard.decide({"usd": 4.0, "unpriced_models": []}, 5.0, 0.8)[0] == "warn"
    assert guard.decide({"usd": 3.9, "unpriced_models": []}, 5.0, 0.8) == ("allow", None)
    assert guard.decide({"usd": 4.9, "unpriced_models": []}, 5.0, None) == ("allow", None)


def test_check_warns_once_per_session_and_logs(session, tmp_path, monkeypatch):
    monkeypatch.setattr(guard, "EVENTS_PATH", tmp_path / "events.jsonl")
    usd = guard.session_cost(session)["usd"]
    stdin = json.dumps({"transcript_path": str(session), "session_id": "s1", "tool_name": "Bash"})
    first = guard.check(stdin, cap_usd=usd * 1.1, warn_at=0.5)
    assert "systemMessage" in json.loads(first)
    assert guard.check(stdin, cap_usd=usd * 1.1, warn_at=0.5) == ""
    denied = json.loads(guard.check(stdin, cap_usd=usd, warn_at=0.5))
    assert denied["continue"] is False
    events = [e["event"] for e in guard.read_events()]
    assert events == ["warn", "deny"]


def test_install_preserves_other_hooks_and_is_idempotent(tmp_path):
    path = tmp_path / ".claude" / "settings.local.json"
    theirs = {"matcher": "Bash", "hooks": [{"type": "command", "command": "lint.sh"}]}
    path.parent.mkdir()
    path.write_text(json.dumps({"permissions": {"allow": ["Read"]},
                                "hooks": {"PreToolUse": [theirs]}}), encoding="utf-8")
    guard.install(tmp_path, 5, None)
    guard.install(tmp_path, 7.5, 0.8)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["permissions"] == {"allow": ["Read"]}
    assert data["hooks"]["PreToolUse"][0] == theirs
    cmds = guard.installed_commands(tmp_path)
    assert len(cmds) == 1 and "--cap-usd 7.5 --warn-at 0.8" in cmds[0]


def test_uninstall_removes_only_ours(tmp_path):
    path = tmp_path / ".claude" / "settings.local.json"
    path.parent.mkdir()
    shared = {"matcher": "*", "hooks": [
        {"type": "command", "command": "lint.sh"},
        {"type": "command", "command": guard.hook_command(5, None)},
    ]}
    path.write_text(json.dumps({"hooks": {"PreToolUse": [shared]}}), encoding="utf-8")
    assert guard.uninstall(tmp_path) == 1
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["hooks"]["PreToolUse"] == [
        {"matcher": "*", "hooks": [{"type": "command", "command": "lint.sh"}]}]
    assert guard.uninstall(tmp_path) == 0


def test_uninstall_drops_empty_hooks_key(tmp_path):
    guard.install(tmp_path, 5, None)
    guard.uninstall(tmp_path)
    data = json.loads((tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    assert data == {}


def test_invalid_settings_is_not_overwritten(tmp_path):
    path = tmp_path / ".claude" / "settings.local.json"
    path.parent.mkdir()
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        guard.install(tmp_path, 5, None)
    assert path.read_text(encoding="utf-8") == "{not json"


@pytest.mark.parametrize("cap,warn", [(0, None), (-1, None), (5, 1.0), (5, 0)])
def test_install_rejects_bad_values(tmp_path, cap, warn):
    with pytest.raises(ValueError):
        guard.install(tmp_path, cap, warn)
