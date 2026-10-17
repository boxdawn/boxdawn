# Toolathlon Funnel Breakdown — Results

**What this is.** A full count of the two places Toolathlon trajectories leave the
waste-rate metric: the adapter failing to build a trace (7,116 scanned → 6,780 built),
and a built trace carrying no `llm_calls` (6,780 → 6,659 included). The totals were
already published in `docs/WASTE_RATE_TOOLATHLON_ADAPTER_AMENDMENT_PREREG.md` §10.2 and
§10.4. The breakdowns below were not published anywhere until now.

**Measured.** 2026-10-17, on `main` at `9aa567f` (boxdawn 0.5.18), over all 66 files in
`data/toolathlon/hf/` (HF `hkust-nlp/Toolathlon-Trajectories`). It calls the adapter's
own `_build_trace_from_entry` on every line. The census script is diagnostic and not
committed. It reproduces a first count taken on 2026-10-13 whose script was not kept,
and every number matched.

**No published figure moves.** Every total below equals the one already in the
amendment.

## Funnel

| Stage | Count |
|---|---:|
| Trajectories scanned (66 files) | 7,116 |
| Adapter built a trace | 6,780 |
| Built, with `llm_calls` (included in the metric) | 6,659 |

## 1. The 336 build failures

The adapter raises rather than skipping silently (`src/clew/ingest/toolathlon.py`), so
each failure has one message.

| Reason (adapter message) | Count | Share |
|---|---:|---:|
| `arguments` JSON parse failure | 127 | 37.8% |
| `request_id` missing or empty | 119 | 35.4% |
| no `tool_calls` at all | 88 | 26.2% |
| duplicate `tool_call` id | 2 | 0.6% |
| **Total** | **336** | 100% |

- No other reason occurred (0 unclassified messages).
- The failures sit in 57 of the 66 files, not in one model's runs.
- Earlier work traced two of these reasons to the source data, on a 320-line sample
  (2026-08-22). A missing `request_id` there was a benchmark run that timed out and
  left an all-null row: 10 of 10. Most `arguments` failures were payloads cut off
  mid-value: 13 of 15. Those are sample findings and have not been re-checked across
  all 336.

## 2. The 121 built traces with no `llm_calls`

The adapter returns no `llm_calls` when `key_stats.input_tokens <= 0` **or**
`key_stats.agent_llm_requests <= 0` (`_reconstruct_llm_calls`). Such a trace is
excluded from the metric with `excluded_reason="no_llm_calls"`.

| | Count |
|---|---:|
| Both conditions hold (`input_tokens <= 0` **and** `agent_llm_requests <= 0`) | 121 |
| Exactly one holds | 0 |

| `key_stats.assistant_turns` | Count |
|---|---:|
| 100 (Toolathlon's turn cap) | 89 |
| 4 to 98 | 32 |
| **Total** | **121** |

The 32 are spread across 18 distinct values. 92 is the most common (6), then 98 (4)
and 94 (3).

### What this corrects

Amendment §10.2 describes the negative-diff rows of its 540-trace probe as
*"`agent_llm_requests=0` while `assistant_turns=100` — Toolathlon max-turns cap (100)
records the field as `0`"*, and §10.4 then labels all 121 exclusions "`no_llm_calls`
anomalies per §10.2". Read together, that implies every exclusion is a turn-cap run.
The full count says **89 of 121** are. The other 32 stopped between 4 and 98 turns
with both token fields still zero. Why they did is not determined here.

The prereg is frozen and is not edited. This note is the correction. The exclusion
count (121) and the metric computed without these traces (`union WR_char` 0.9342 at
the amendment, 6,659 included) are unaffected: the traces are excluded whatever the
cause.

## 3. Two different 121s

Amendment §10.2 also reports `priced (model in cost table) | 121 (1.8%)`. That is a
different set with the same size. Pricing is applied only after the guard in §2 has
passed, so a trace with no `llm_calls` cannot be priced. The two sets are disjoint.
