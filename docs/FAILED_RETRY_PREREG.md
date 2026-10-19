# Failed Retry — Pre-registration

**Scope.** A candidate rule for one shape of context loss: a tool call fails,
and the next call to the same tool fails again. Name: `failed_retry`. This
document asks one question: do people who labelled agent traces mark the
calls this rule picks out as mistakes? No detector ships from it.
**Written.** 2026-10-19, before any label is read against the rule. Engine
`main` at `0b5ce34`. TRAIL snapshot `b424ce63d5973d5dcd7169b1bc3c07ccdee276d1`
(equal to the Hugging Face head on 2026-10-19).
**Results** follow as a separate commit.

## 0. Why

- `TRAIL_CANDIDATE_MAPPING_RESULTS.md` (`#257`) §2 found that TRAIL's
  `Context Handling Failure` counts context loss: L = 29 / 47, and the usable
  pool is gaia's **21 records over 19 traces**. Its §6.2 asked for an axis
  pre-registration with a name of its own.
- Measured 2026-10-19 on those 21 records: the span detectors (`repeat`,
  `pingpong`, `cascade`) confirm **0 / 21**. 20 of the 21 point at an LLM
  span, which `preprocess_trace` moves into `metadata["llm_calls"]`, so span
  detectors cannot see them. `context_resend` flags 19 / 20 of those calls,
  but it flags **370 / 486 = 0.7613** of all LLM calls in the same 19 traces,
  so it does not tell these calls apart.
- The 21 records group as `page_down_args` 7, `did_not_incorporate_error` 6,
  `env_knowledge_forgotten` 3, others 5 (`#257` codes). The first two are
  "an error came back and was not used". That is the one group a rule can
  see without reading text.

## 1. The rule (frozen)

Order each trace's tool calls by start time. For every adjacent pair
`(a, b)`: **`a` failed, `b` calls the same tool as `a`, and `b` failed.**
The event is `b`.

- **Failed.** OpenInference: the span's `status_code` is `"Error"`. Claude
  Code: the `tool_result` has `is_error: true`.
- **Same tool.** OpenInference: equal `span_name`. Claude Code: equal
  `tool_use.name`. The input is not compared.

Why the input is not compared: in TRAIL the retried `page_down` calls vary
their arguments (`{"": ""}` and `{"": {}}`) and fail the same way.

## 2. Counts taken before this document, with no label read

| | TRAIL gaia (117 traces) | TRAIL swe_bench (31) | Claude Code, this machine (79 sessions) |
|---|---:|---:|---:|
| tool calls | 623 | 25 | 8,282 |
| failed | 174 (42 traces) | **0** | 190 (62 sessions) |
| events (§1) | **94** | 0 | **9** |
| … of which `PageDownTool` | **74** (20 traces) | – | – |
| … all other tools | **20** (13 traces) | – | – |

- swe_bench records no `status_code = "Error"`: its agent reports errors in
  the interpreter's output text. The rule cannot see it, and it is left out.
- `PageDownTool` is one harness defect (a tool declared with no parameters,
  called with an empty key). `#257` §3 found it filed under two TRAIL
  categories. It is scored separately and does not count toward the gate.
- Every gaia tool span (623 / 623) sits under a `Step N` CHAIN span that
  holds exactly one LLM span. That LLM span is the call that chose the tool.

## 3. What counts as a match (frozen)

An event `b` **matches** when at least one TRAIL error record, of any
category, has `location` equal to `b`'s span id or to the LLM span in `b`'s
`Step` chain.

A secondary count restricts the records to `Context Handling Failure(s)` and
`Incorrect Memory Usage`.

🔴 TRAIL annotators labelled what they saw as errors, not every repeated
failure. A miss can be an unlabelled true event. So the precision below is a
**lower bound against these labels**, and it is reported as that.

## 4. Measures

- **M1 (gate).** Matched / events, over the **20 non-`PageDownTool` events**.
  Clopper–Pearson 95% two-sided interval.
- **M2.** The same over all 94 events, and over the 74 `PageDownTool` events.
- **M3.** M1 and M2 restricted to the context categories (§3, secondary).
- **M4.** Of the 13 records in the gaia L pool with family
  `did_not_incorporate_error` or `page_down_args`, how many have an event
  `b` whose `Step` LLM span or tool span is the record's `location`.
- **M5.** Per trace: the 13 non-`PageDownTool` traces, how many have at
  least one matched event. Events cluster inside a trace, and this shows it.

## 5. Gate (frozen)

| M1 | Reading | Next |
|---|---|---|
| **≥ 0.40** (8 or more of 20) | the rule picks out calls people mark as mistakes | a detector pre-registration: the OpenInference adapter records failed tool spans (it drops `status_code` today; Claude Code already keeps `error_span_ids`), the detector, and where its finding goes in the report |
| **< 0.40** | the rule mostly picks out calls nobody marked | the rule is not taken further; §2's Claude Code count is still reported |

0.40 is the bar `#256` used for every TRAIL pool.

## 6. Predictions (frozen)

- **P1.** The run counts 94 events, 20 of them non-`PageDownTool`, over the
  same traces as §2. Otherwise the run is void.
- **P2.** M1: unknown. No number is predicted.
- **P3.** M4: unknown. No number is predicted.

## 7. Exposure, stated before the run

- I have read the descriptions of all 49 context-category records, and
  `#257` coded them. M4's 13 records are therefore not blind.
- I have not read any TRAIL record against the events of §1. M1, M2 and M5
  are blind to that extent.

## 8. What this does not settle

- **Claude Code.** 9 events in 79 sessions on one machine is a count, not a
  rate for users. Whether a matched rule is worth a detector there is the
  detector pre-registration's question.
- **The other 8 L records** (`env_knowledge_forgotten`,
  `tool_description_ignored`, plans ignored). They need the text, and no rule
  here reads it.
- **Dollars.** No cost is attached to an event in this document.

Diagnostics stay uncommitted. No TRAIL text is committed (no-redistribution
gate).

## 9. Results (2026-10-19)

Run on `main` at `caaa837`, after this document merged. Scorer and event list
uncommitted (scratchpad `ctxloss/score_failed_retry.py`). Every event's `Step`
chain held exactly one LLM span (94 / 94), as §2 stated.

| | Matched / events | Share | 95% CI (Clopper–Pearson) |
|---|---:|---:|---|
| P1 events reproduce | 94 · 20 non-`PageDownTool` · 13 traces | ✅ | |
| **M1** non-`PageDownTool`, any category | **9 / 20** | **0.45** | 0.2306 – 0.6847 |
| M2 all events | 60 / 94 | 0.6383 | 0.5327 – 0.7349 |
| M2 `PageDownTool` | 51 / 74 | 0.6892 | 0.5710 – 0.7917 |
| M3 non-`PageDownTool`, context categories | **0 / 20** | 0.0000 | 0.0000 – 0.1684 |
| M3 all events, context categories | 6 / 94 | 0.0638 | 0.0238 – 0.1338 |
| M4 L-pool records covered | 5 / 13 | | |
| M5 non-`PageDownTool` traces with a match | 7 / 13 | | |

**Gate (§5): M1 = 0.45 ≥ 0.40, 9 ≥ 8. ✅ Passes.** 🔴 The interval's lower
bound is 0.2306, under the bar. The pass rests on 9 of 20 events.

**🔴 What the matches are labelled as.** Not as context loss. Over the 9
matched non-`PageDownTool` events, the categories on the matched spans are
`Resource Abuse` 4, `Formatting` 4, and one each of `Tool-related`,
`Environment Setup`, `Poor Information Retrieval` and `Incorrect Problem
Identification` (an event can carry more than one). This breakdown was not
pre-registered. It is reported because M3 = 0 / 20 needs it read.

So the rule picks out calls people mark as mistakes, which is what the gate
asked. It does **not** pick out what they call context loss: the six
context-category matches are all `PageDownTool`.

By tool, non-`PageDownTool`: `TextInspectorTool` 4 of 13 matched,
`ArchiveSearchTool` 3 / 3, `SearchInformationTool` 1 / 3, `SimpleTool` 1 / 1.

### What may be said

- *"On TRAIL gaia, 9 of 20 repeated same-tool failures (outside one harness
  defect) carry a human error label (95% CI 0.23–0.68)."*
- 🔴 Not: that the rule detects context loss (M3 0 / 20), any rate for
  Claude Code (§8: 9 events on one machine), or any dollar figure.

### Next (per §5)

A detector pre-registration. It must decide, given this section, what the
finding is called: the labels support "a failed call retried into the same
failure", not "context loss".
