# Failed Retry Detector — Pre-registration

**Scope.** Ship the `failed_retry` rule (`FAILED_RETRY_PREREG.md`) as a
detector for **OpenTelemetry / OpenInference traces only**. A count with no
dollars, shown in its own report section. Claude Code traces are left out.
**Written.** 2026-10-19, before any code change. Engine `main` at `4f8d2d2`.
**Code and results** follow as separate commits.

## 0. Why, and why not Claude Code

- `FAILED_RETRY_PREREG.md` §9: on TRAIL gaia, 9 / 20 non-`PageDownTool` events
  carry a human error label (0.45, CI 0.2306–0.6847). The gate passed. None of
  the 9 is labelled as context loss (M3 0 / 20).
- The same rule on Claude Code, counted 2026-10-19 through
  `ingest_claude_code_jsonl`:

  | | trace-commons 28 + cited trace | this machine, 79 sessions |
  |---|---:|---:|
  | events | 39 | 9 |
  | `Bash` or `PowerShell` | **37** | 6 |
  | same input as the failed call | **1** | 0 |
  | same output as the failed call | 13 | 1 |
  | a user denial, permission denial or cancel on either side | 5 | 1 |

  On TRAIL, "same tool" meant one narrow tool (`page_down`,
  `inspect_file_as_text`). On Claude Code it is almost always the shell, so
  the rule counts "two shell commands in a row failed", 38 / 39 of them with
  different commands. TRAIL's 9 / 20 says nothing about those events, and no
  labelled Claude Code data was found (web search 2026-10-19). Claude Code is
  therefore out of scope.

## 1. Adapter (frozen)

`otel_spans_to_trace` (`ingest/langgraph.py`) is the one function all three
OpenTelemetry entry points go through: `ingest_from_otel_json` (Format A,
source `otel_json`), `ingest_from_openinference_json` (Format C, source
`openinference_json`) and `capture.py` (live spans, source `otel_adapter`).

It records the span ids of **tool** spans whose status is an error into
`trace.metadata["error_span_ids"]`. That is the key and the meaning the Claude
Code adapter already uses for `is_error` tool results. Error status is read
as:

| entry | where | error value |
|---|---|---|
| live `ReadableSpan` | `span.status.status_code` | `StatusCode.ERROR` |
| Format A (`span.to_json()`) | `raw["status"]["status_code"]` | `"ERROR"` (SDK `to_json` writes the enum name) |
| Format C (OpenInference nested) | `raw["status_code"]` | `"Error"` |

The two file shims (`_SdkJsonSpan`, `_OISpan`) gain a `status` attribute
shaped like the live one. Nothing else in the adapter changes.

🔴 **Side effect, stated before the code.** Two consumers already read
`error_span_ids`: `report/_enrich.py` skips waste pairs whose origin or
candidate failed, and `cost/amplification.py` skips failed spans. On
OpenTelemetry traces both start to apply. §4 P4 measures it.

## 2. Detector (frozen)

`src/clew/detect/failed_retry.py`, `find_failed_retries(trace) -> list[tuple[Span, Span]]`.

- Runs only when `trace.metadata["source"]` is `otel_json`,
  `openinference_json` or `otel_adapter`. Otherwise it returns `[]`.
- Takes the trace's tool spans in `(start_time, span_id)` order. For each
  adjacent pair `(a, b)`: `a` and `b` are both in `error_span_ids` and
  `a.agent_or_node_id == b.agent_or_node_id`. Then `(a, b)` is an event.
- On TRAIL, `agent_or_node_id` for a tool span is `tool.name`, and
  `tool.name` maps one-to-one onto the `span_name` the first pre-registration
  used (9 pairs, e.g. `page_down` ↔ `PageDownTool`). Grouping is unchanged.

## 3. Report (frozen)

- **Markdown.** A section `## Failed retries`, after `## Duplicate creation
  check`, only when there is at least one event. Text: *"A tool call failed,
  and the next call to the same tool failed again. Each row is the second
  call. These are not counted as waste and carry no cost."* One row per
  event: tool, first call's span id, second call's span id.
- **JSON.** A top-level key `failed_retries`: a list of
  `{tool, failed_span_id, retry_span_id}`. Present only when non-empty, so
  reports without events are byte-identical to today's.
- No dollar figure, no change to `cost_summary`, the waste totals or any
  rate.
- The word "context" does not appear in the section (`FAILED_RETRY_PREREG.md`
  §9, M3 0 / 20).

## 4. Predictions (frozen)

- **P1. TRAIL reproduces through the product path.** All 148 TRAIL traces
  through `ingest_from_openinference_json` + `find_failed_retries`: gaia
  **94** events, **74** of them `page_down`, **20** others over **13**
  traces; swe_bench **0**.
- **P2. Claude Code reports do not change.** Trace-commons 28, the cited
  trace and the 6 local sessions with sub-agents: JSON reports equal to
  `main` except `analyzed` (`PYTHONHASHSEED=0`, worktree).
- **P3. Public figures do not move.** Corpus A recomputed from P2's reports:
  `0.8449` / `0.9916` unchanged. Corpora B (Toolathlon), C (Exgentic) and D
  (Claude Code) use no OpenTelemetry adapter. Their input path does not
  reach the changed code, and this is stated rather than re-run.
- **P4. Side effect on TRAIL.** Over the 148 traces, the number of waste
  pairs `_enrich` skips for an error span, and the change in
  `total_waste_cost` per trace. **Unknown. No number is predicted.**
- **P5. Format A and live spans.** Unit tests: a Format A file and a live
  `ReadableSpan` list, each with two consecutive failing calls to one tool,
  give one event each. One failing call followed by a different tool gives
  none.

## 5. Stop conditions

- P1 off by any event: the adapter or the ordering differs from the first
  pre-registration's count. Find out why before anything ships.
- P2 or P3 fails: the change reached Claude Code. Stop.
- P4 is reported whatever it is. If any TRAIL trace's `total_waste_cost`
  changes, the results say by how much and why, before a release.

## 6. Shipping and notice

- An analysis-path change: a release, and a cloud pin bump for hosted uploads
  of OpenTelemetry files.
- The web is notified under two clauses: a new detector, and a change to
  report markdown (for OpenTelemetry uploads only).

## 7. What this does not settle

- **Claude Code** (§0). A rule for it needs labelled Claude Code data first.
- **Errors only in output text** (TRAIL swe_bench: 0 error statuses). The
  detector sees status, not text.
- **Context loss.** This detector does not detect it (§3).
- **Dollars.** None attached.
