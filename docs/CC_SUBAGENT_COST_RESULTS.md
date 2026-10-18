# Claude Code Subagent Cost — Results

Pre-registration: `docs/CC_SUBAGENT_COST_PREREG.md` (merged `#291`, `47974aa`).
Code: `1a13efe` on `feat/cc-subagent-cost`.
**Measured.** 2026-10-18. "Before" is a worktree of `main` at `47974aa`;
"after" is the branch. Both run the shipped CLI (`python -m clew analyze
--json --no-snippets`) with `PYTHONHASHSEED=0` over the same 35 traces: the
28 trace-commons sessions, the cited trace `agent-race/claude-code.jsonl`,
and the six local sessions that have a `subagents/` directory. Scripts are
diagnostic and not committed.

## Predictions scored

| | Prediction | Result |
|---|---|---|
| P1 | Bit-identical where there is no `subagents/` directory; Corpus A stays 0.844933 / 0.991595 | ✅ 29/29 analyze JSONs identical except the `analyzed` timestamp. Corpus A `union_wr_cost` 0.8449333451365042, `union_wr_char` 0.991595182355781, `union_sdr_at_10` 0.9643: the same values as before the change |
| P2 | Report total = `guard.session_cost` within 1e-6 on the six local sessions | ✅ 6/6, largest difference 5.0e-09 (the JSON rounds to 8 decimals) |
| P3 | 0 `context_resend` events crossing conversations | ✅ 0 of 29,506 events across the six sessions |
| P4 | `a508a7ac` session: \|Δ `waste_ratio`\| < 0.001 | ✅ 0.726149 → 0.725794 (−0.000355) |
| P5 | Suite passes, only the §2 invariant restated | ✅ 1196 passed, 1 xfailed |

**P1 as first checked failed 0/29, and the checker was wrong.** The first
comparison was byte-for-byte, and every file differed. The only differing
field was `analyzed`, the time the report was written. With that field
excluded, 29/29 are equal. The prediction said "bit-identical analyze JSON",
which a timestamped report cannot be; what it meant, and what was measured,
is every computed field.

## The six sessions

| Session | Before | After | `waste_ratio` before → after |
|---|---:|---:|---|
| `ee41edd2` (`a508a7ac`) | $42.966238 | $42.987367 | 0.726149 → 0.725794 |
| `86d2d89f` | $0.007224 | $0.012915 | 0.065292 → 0.041841 |
| `6f45b92c` | $0.004700 | $0.009150 | 0.003398 → 0.033267 |
| `083ffa23` | $0.005260 | $0.009461 | 0.038866 → 0.050470 |
| `b7995abe` | $0.005285 | $0.007225 | 0.036992 → 0.027059 |
| `14de1ba6` | $0.004865 | $0.006794 | 0.003102 → 0.002221 |

The five small sessions are budget-guard test sessions. Their parents are
tiny, so the subagent is a large share of the total and `waste_ratio` moves
in both directions, up to +0.030. That direction depends on how much the
subagent resent compared with its parent. These sessions are not
representative of real use.

## What this does not establish

- **How much real users' reports were missing.** The one real-sized session
  was missing 0.05%. Public corpora publish no subagent files.
- **Cloud reports.** Unchanged. The server receives one file and never the
  sibling directory (prereg §2). `submit.discover` still uploads subagent
  files as standalone traces.
- **Attribution.** Subagent tool calls are not spans yet, so
  `cross_agent_repeat` still cannot fire on Claude Code.
