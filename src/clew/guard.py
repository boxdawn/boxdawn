"""src/clew/guard.py — stop a Claude Code session once it has spent a set amount.

A `PreToolUse` hook. Before every tool call (main agent and subagents alike)
it prices what the session has spent so far and, at or over the cap the
customer set, denies that tool and stops the session. It does not stop on
repeats or patterns: of 38 hand-coded Claude Code repeats, 23 were re-checks
after an edit (docs/ACCEPTED_PAIR_PRECISION_RESULTS.md).

What was measured before this was written (Claude Code 2.1.299, 2026-10-16,
field_test/diagnostics/_budget_guard_design_DRAFT.md §2):

- To block the tool, the output needs `continue: false` *and*
  `permissionDecision: "deny"`. `continue: false` alone stops the session
  after the tool has already run.
- Stopping inside a subagent stops only that subagent; the main agent's next
  tool call is blocked in turn, which ends the session.
- The hook input carries no cost. It carries `transcript_path`; subagent usage
  is written beside it under `<session>/subagents/*.jsonl`.
- In interactive mode the call that requested the tool is not in the
  transcript yet when the hook runs. So the total is "up to the previous
  call", and a session can end past the cap by a call or two. That is a limit
  to state, not something this module can close.

Pricing is `clew.cost.pricing`, the same table the reports use. A model the
table does not know is priced at the default and still counted: leaving it out
would let that session run with no cap at all. The default is the cheaper
side, so such a total is reported as a lower bound. A long prompt pays its
model's long-context rate where the table carries one (pricing stage 2).

Nothing leaves the machine. Blocks and warnings are appended to
`~/.clew/guard_events.jsonl`.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from clew.cost.pricing import pricing_for_prompt, resolve_pricing, tier_input_cost

EVENTS_PATH = Path.home() / ".clew" / "guard_events.jsonl"
# Per-user and gitignored by Claude Code. The hook command names this
# machine's interpreter by absolute path, which would break for anyone else
# if it were written into the shared, committed `settings.json`.
SETTINGS_RELPATH = Path(".claude") / "settings.local.json"
# How our hook is told apart from the user's own hooks in the same list.
_MARKER = "-m clew guard check"


def _call_cost(msg: dict) -> tuple[float, str | None, bool] | None:
    """(usd, model, matched) for one API call, or None if it billed nothing.

    Usage fields are read the way `ingest/claude_code.py` reads them: the
    1-hour cache write is taken from `usage.cache_creation` only when that
    sub-object adds up to the total, otherwise the whole write is priced at
    the 5-minute rate.
    """
    usage = msg.get("usage")
    if not isinstance(usage, dict):
        return None
    uncached = int(usage.get("input_tokens") or 0)
    cache_read = int(usage.get("cache_read_input_tokens") or 0)
    cache_write = int(usage.get("cache_creation_input_tokens") or 0)
    output = int(usage.get("output_tokens") or 0)
    if uncached + cache_read + cache_write + output == 0:
        # Claude Code writes zero-usage `<synthetic>` messages; pricing them
        # would mark the session as having an unknown model for nothing.
        return None
    write_1h = 0
    cc = usage.get("cache_creation")
    if isinstance(cc, dict):
        ttl_1h = int(cc.get("ephemeral_1h_input_tokens") or 0)
        ttl_5m = int(cc.get("ephemeral_5m_input_tokens") or 0)
        if ttl_1h + ttl_5m == cache_write:
            write_1h = ttl_1h
    model = msg.get("model") if isinstance(msg.get("model"), str) else None
    pricing, matched = resolve_pricing(model)
    pricing = pricing_for_prompt(pricing, uncached + cache_read + cache_write)
    usd = tier_input_cost(
        pricing,
        uncached=uncached,
        cache_read=cache_read,
        cache_write_total=cache_write,
        cache_write_1h=write_1h,
    ) + pricing.output_cost(output)
    return usd, model, matched


def session_cost(transcript_path: str | Path) -> dict:
    """Price a session: the main transcript plus every subagent transcript.

    One API call is one `message.id`. Claude Code writes a line per content
    block and repeats the call's usage on each, so counting lines overstated
    the cited trace's cost 1.523x (ingest/claude_code.py `_extract_llm_calls`).
    A line with no id is its own call, as in the adapter.
    """
    main = Path(transcript_path)
    files = [main]
    sub_dir = main.with_suffix("") / "subagents"
    if sub_dir.is_dir():
        files += sorted(sub_dir.glob("*.jsonl"))

    seen: set[str] = set()
    usd = 0.0
    calls = 0
    unmatched: set[str] = set()
    for path in files:
        try:
            fh = path.open(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        with fh:
            for line in fh:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue  # a line still being written
                if not isinstance(entry, dict) or entry.get("type") != "assistant":
                    continue
                msg = entry.get("message")
                if not isinstance(msg, dict):
                    continue
                mid = msg.get("id")
                if isinstance(mid, str) and mid:
                    if mid in seen:
                        continue
                    seen.add(mid)
                priced = _call_cost(msg)
                if priced is None:
                    continue
                call_usd, model, matched = priced
                usd += call_usd
                calls += 1
                if not matched:
                    unmatched.add(model or "<none>")
    return {"usd": usd, "calls": calls, "unpriced_models": sorted(unmatched)}


def _money(usd: float) -> str:
    # Cents hide the difference under a dollar: an interactive run with a
    # $0.012 cap showed "spent $0.01 >= cap $0.01" (2026-10-17).
    return f"${usd:.2f}" if usd >= 1 else f"${usd:.4f}"


def decide(cost: dict, cap_usd: float, warn_at: float | None) -> tuple[str, dict | None]:
    """("deny" | "warn" | "allow", hook output or None)."""
    usd = cost["usd"]
    floor = " (lower bound: unpriced model " + ", ".join(cost["unpriced_models"]) + ")" \
        if cost["unpriced_models"] else ""
    if usd >= cap_usd:
        reason = f"Boxdawn budget guard: session spent {_money(usd)}{floor} >= cap {_money(cap_usd)}"
        return "deny", {
            "continue": False,
            "stopReason": reason,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
        }
    if warn_at is not None and usd >= cap_usd * warn_at:
        return "warn", {
            "systemMessage": (
                f"Boxdawn budget guard: session spent {_money(usd)}{floor}, "
                f"{usd / cap_usd:.0%} of the {_money(cap_usd)} cap"
            ),
        }
    return "allow", None


def read_events() -> list[dict]:
    try:
        lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _append_event(event: dict) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def check(stdin_text: str, cap_usd: float, warn_at: float | None) -> str:
    """The hook body. Returns what to print on stdout (possibly empty)."""
    inp = json.loads(stdin_text)
    cost = session_cost(inp["transcript_path"])
    verdict, out = decide(cost, cap_usd, warn_at)
    session_id = inp.get("session_id")
    if verdict == "warn" and any(
        e.get("session_id") == session_id and e.get("event") == "warn"
        for e in read_events()
    ):
        return ""  # warn once per session
    if verdict != "allow":
        _append_event({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": verdict,
            "session_id": session_id,
            "agent_id": inp.get("agent_id"),
            "cwd": inp.get("cwd"),
            "tool": inp.get("tool_name"),
            "usd": round(cost["usd"], 6),
            "calls": cost["calls"],
            "cap_usd": cap_usd,
            "unpriced_models": cost["unpriced_models"],
        })
    return json.dumps(out) if out is not None else ""


# ── settings.local.json ─────────────────────────────────────────────────────


def hook_command(cap_usd: float, warn_at: float | None) -> str:
    cmd = f'"{sys.executable}" -I {_MARKER} --cap-usd {cap_usd:g}'
    if warn_at is not None:
        cmd += f" --warn-at {warn_at:g}"
    return cmd


def _is_ours(hook: object) -> bool:
    return isinstance(hook, dict) and _MARKER in str(hook.get("command", ""))


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))  # invalid JSON: raise, write nothing
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def _without_ours(settings: dict) -> tuple[dict, int]:
    """Drop our hook from PreToolUse, keeping every other entry. (settings, removed)."""
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict) or not isinstance(hooks.get("PreToolUse"), list):
        return settings, 0
    removed = 0
    kept_groups = []
    for group in hooks["PreToolUse"]:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            kept_groups.append(group)
            continue
        kept = [h for h in group["hooks"] if not _is_ours(h)]
        removed += len(group["hooks"]) - len(kept)
        if kept:
            kept_groups.append({**group, "hooks": kept})
    if kept_groups:
        hooks["PreToolUse"] = kept_groups
    else:
        del hooks["PreToolUse"]
        if not hooks:
            del settings["hooks"]
    return settings, removed


def _write(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def install(project: Path, cap_usd: float, warn_at: float | None) -> Path:
    if cap_usd <= 0:
        raise ValueError("--cap-usd must be greater than 0")
    if warn_at is not None and not 0 < warn_at < 1:
        raise ValueError("--warn-at must be between 0 and 1 (a fraction of the cap)")
    path = project / SETTINGS_RELPATH
    settings, _ = _without_ours(_load(path))
    hooks = settings.setdefault("hooks", {})
    hooks.setdefault("PreToolUse", []).append({
        "matcher": "*",
        "hooks": [{"type": "command", "command": hook_command(cap_usd, warn_at)}],
    })
    _write(path, settings)
    return path


def uninstall(project: Path) -> int:
    """Remove our hook. Returns how many were removed (0: nothing to do)."""
    path = project / SETTINGS_RELPATH
    if not path.exists():
        return 0
    settings, removed = _without_ours(_load(path))
    if removed:
        _write(path, settings)
    return removed


def installed_commands(project: Path) -> list[str]:
    settings = _load(project / SETTINGS_RELPATH)
    hooks = settings.get("hooks")
    groups = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    if not isinstance(groups, list):
        return []
    return [
        h["command"]
        for g in groups if isinstance(g, dict) and isinstance(g.get("hooks"), list)
        for h in g["hooks"] if _is_ours(h)
    ]
