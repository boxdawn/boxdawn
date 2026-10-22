# Boxdawn

<div align="center">

**AI agent observability, on the axis that shows up on your bill.**

[![PyPI](https://img.shields.io/pypi/v/boxdawn)](https://pypi.org/project/boxdawn/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.12-blue)](https://www.python.org/)
[![CI](https://github.com/boxdawn/boxdawn/actions/workflows/ci.yml/badge.svg)](https://github.com/boxdawn/boxdawn/actions/workflows/ci.yml)
[![Corpora](https://img.shields.io/badge/corpora-4%20%C2%B7%2017%2C881%20traces-blueviolet)](#-where-it-stands--measured-not-marketed)

</div>

Boxdawn watches what your agents do and finds **the work they already paid for** — the context resent every turn, the file read again, the tool call that returned an answer you already had. Four deterministic detectors plus an opt-in semantic check, run against the trace files your agents already write. **Monitor, detect, alert, then fix** — the detection layer runs today. Measured across 17,881 traces in four public corpora.

**Try it on one trace** — no install, no account: **[boxdawn.com/analyze](https://boxdawn.com/analyze)**

Or run it on your own machine, offline:

```bash
pip install boxdawn
boxdawn analyze <trace>.jsonl --out report.md
```

> PyPI package is `boxdawn`. Python still imports as `import clew` (internal namespace, kept for backward compatibility with existing configs).

---

## ✨ Core Features

- **Deterministic waste detectors (4)** — `repeat` (tool-call cascade), `context_resend` (input-side chunk resend), `redundant_read` (Read-tool duplicates with interval gating), `duplicate_creation` (creation-tool ID-bridge on 26 mapped tools).
- **Cross-corpus waste-rate metric** — `WR_char` (byte ratio), `WR_cost` (dollar ratio with cache-tier-aware pricing), `SDR@10` (share of sessions with meaningful waste). Union across detectors. See §Where it stands.
- **Opt-in LLM-as-Judge semantic duplicate** — Claude Haiku 4.5 judges chunk pairs the deterministic gate cannot separate (paraphrased re-sends, non-byte-identical tool responses). Hard cost cap per session.
- **Zero-instrumentation ingest** — reads Claude Code JSONL, OpenTelemetry SDK JSON, OpenInference (Phoenix / TRAIL), Toolathlon trajectories, RedundancyBench, and Exgentic Agent LLM Traces v2. No SDK, no code change in your agent.
- **Cost attribution with source-URL-pinned pricing** — per-model rates for Sonnet 4.5 / 4.6, Opus 4.7, Haiku 4.5, GPT-4o family, GPT-5 / 5.2 / mini / o-series, Gemini 1.5 / 2.5 / 3-pro-preview, Grok 4 / fast / code-fast, DeepSeek v3.2, GLM 4.6, Kimi K2-0905 / K2.5, MiniMax M2, Qwen 3 Coder. Every entry carries `Source: URL (verified YYYY-MM-DD)`.
- **Reproducible by anyone** — every number we publish names its corpus and the date it was measured, and the report on our product page comes from a public trace you can run yourself. See §How we keep ourselves honest.

**Boxdawn runs as a service and as a library.** [boxdawn.com](https://boxdawn.com) runs these same detectors in a browser — upload without an account, or sign in and keep measurements per project over time. This repo is the analyzer underneath it, and it runs offline. See §Roadmap for what is running today and what is next.

**No instrumentation. No SDK. No code changes.** Boxdawn reads trace files your agent already writes.

Ran on 6,780 public benchmark trajectories. One Toolathlon Canvas session (`grok-4_2`, task `canvas-art-manager`) shows the shape of what falls out:

```
## Result

- **Waste detection**: no waste detected (wasteful=False).
- **Duplicate creation check**: 27 candidate pair(s) — 13 with differing entity IDs, 0 with the same entity ID, 14 without extractable entity ID. Detection, not confirmed impact. See section below.

- **Tool mapping coverage for this trace**: 11 of 15 tools recognized (73.3%).
- **Unrecognized tools in this trace (top 4)**: canvas-canvas_get_user_profile, canvas-canvas_health_check, canvas-canvas_list_sub_accounts, emails-download_attachment

## Duplicate creation check

The waste detector above requires both responses to be byte-identical. That is the right test for reads — a re-read that returns the same content is a redundant call. For creation tools it is reversed: if a document really was created twice, the two responses carry different entity IDs, so the waste detector excludes them by construction. This section scans that excluded pool separately.

- **candidates**: 27 pairs total
  - 13 with different entity IDs
  - 0 with the same entity ID
  - 14 without extractable entity ID

### 1. canvas-canvas_upload_file_from_path

- origin span `call_79190340` → candidate span `call_52801306`
- Both calls returned entity IDs, and they differ: 5 / 35.

### 2. canvas-canvas_upload_file_from_path

- origin span `call_94789037` → candidate span `call_89334053`
- Both calls returned entity IDs, and they differ: 7 / 32.
```

All 13 differing-ID pairs in this trace are the same tool, `canvas-canvas_upload_file_from_path`. The agent uploaded the same file 13 times, and each call created a distinct Canvas entity. The waste detector correctly did not flag them (the responses were not byte-identical, because each returned a different ID). The `Duplicate creation check` section catches exactly this reverse case.

Reproduce:

```bash
pip install boxdawn
# Toolathlon corpus (CC-BY-4.0): huggingface.co/datasets/hkust-nlp/Toolathlon-Trajectories
boxdawn analyze grok-4_2.jsonl --out report.md
```

*(Yes, agents legitimately re-read files. That is why the cascade below has two gates: the structural group only becomes a flag when the state check confirms nothing changed between the two calls, and the tool output is byte-identical.)*

---

## Why the waste axis

Agents re-send the whole conversation every turn, re-read files they already have, and call tools that return an answer they already got. On full-length agent sessions, most of the input bill is that: **0.92 to 0.99 of input bytes are content the run had already paid for once.** It is the largest line item your bill does not break out. The share tracks session length — on a fourth corpus whose median session is four tool calls it is **0.80**, and it climbs monotonically with turns.

Boxdawn itemises it. It sits on top of the trace layer rather than replacing it — feed it a trace your existing tools already collect, from Langfuse, Arize, LangSmith, Phoenix or a raw Claude Code session, and get back a bill breakdown they do not compute.

Detection is deterministic first: four detectors carry the waste-rate metric (`repeat` / `requery`, `context_resend`, `redundant_read`, `duplicate_creation`), with an opt-in LLM-as-judge pass for the semantic duplicates a byte comparison cannot catch. Each one is specified and frozen before its results are measured, so the numbers below are predictions that held rather than findings that were tuned.

This repo is the analyzer you install with pip. The service at [boxdawn.com](https://boxdawn.com) — browser upload, accounts, stored measurements, dashboard — runs this repo's detectors and waste-rate metric from a separate repo. §Roadmap says which links of the chain run today.

---

## How it works

A two-stage cascade, fully deterministic. Every parameter is pinned to a git tag with a manifest sha256.

**Stage 1: structural gate.** Group steps by `(node, normalized input)`. A group with `N ≥ 2` occurrences is a candidate.

**Stage 2: identity gate.** Compare the two outputs.

- **Tool spans**: require `sha256(output_A) == sha256(output_B)`. Byte-identical. This is the precision-carrying gate.
- **Non-tool spans**: require cosine similarity `≥ φ` against a frozen embedding (`paraphrase-multilingual-MiniLM-L12-v2`).

**Why sha256 for tools.** We cannot see inside a tool. We do not know whether `Bash: ls` had side effects, or whether `send_email` actually reached anyone. So we judge by result. Same input, same byte output, no state change in the interval: the second call was redundant. If outputs differ (a retry succeeded where one failed, an in-memory counter advanced), the pair is **not** flagged.

**Reverse case: duplicate creation.** If two `notion-API-post-page` calls really did create two pages, the responses carry different entity IDs, so byte-identity fails and the waste detector correctly excludes them. The `Duplicate creation check` section scans that excluded pool separately, using per-tool entity-ID extraction (26 tools currently mapped, see [`docs/ID_BRIDGE_PRODUCTION_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/ID_BRIDGE_PRODUCTION_PREREG.md) §1.1). This is what surfaced the 13 Canvas uploads above.

**Frozen parameters** (never hand-tuned): `φ = 0.514345`, `N = 2`. `N = 2` began as an arbitrary default; a later grid on `N ∈ {2, 3, 5, ∞}` on RedundancyBench found F1 decreases monotonically as `N` grows. F1-optimal, not tuned.

**State check.** For tool-repeat pairs the report says either "no modification of this file in between" or "**File was modified in between**, may be a legitimate re-read". Tool-error responses (`is_error: true` in Anthropic `tool_result`) are excluded with an explicit count.

**Report categories** (labels only; detection is unchanged):

- **`error_repeat`**: same call after a failure, same arguments as before.
- **`side_effect`**: state-changing tool invoked twice with the same arguments.
- **`idempotent`**: read-only or declarative tool called repeatedly. Sub-classified into a 5-value evidence tier; see [`docs/GREYZONE_EXPANSION_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/GREYZONE_EXPANSION_PREREG.md).
- **`unclassified`**: payload-dependent tools (`Bash`, `PowerShell`, `bigquery_run_query`). Tool name alone cannot classify.

Mapping is by exact tool name, never by substring.

---

## Reads your existing traces

Auto-detected input formats:

| Source | Detected by |
|---|---|
| Claude Code session logs (`.jsonl`) | `sessionId` |
| OpenTelemetry SDK JSON | `context` |
| OpenInference (Phoenix / TRAIL) | `span_id` + nested `child_spans` |
| Boxdawn native trace JSON | `trace_id` + `spans` |
| Toolathlon trajectories | `modelname_run` + `task_status` |
| RedundancyBench | `tasks` + `simulations` |

*Exgentic Agent LLM Traces v2 is read through the library (`clew.ingest.exgentic`), not by `boxdawn analyze` — it is Parquet, so there is no first-line marker to detect.*

*Cursor and Codex sessions are not supported yet.*

*OTLP protobuf-JSON is not yet supported; the error message points at the SDK-JSON conversion.*

### OpenInference framework coverage

Measured PASS on Tier 1 and Tier 2:

| Framework | Fixture | Notes |
|---|---|---|
| LangChain / LangGraph | ✔ `tests/fixtures/openinference_langchain.json` | JSON-wrapped `TOOL` output unwrapped by adapter. |
| CrewAI | ✔ `tests/fixtures/openinference_crewai.json` | `.run` / `._execute_core` suffixes stripped. |
| LlamaIndex | schema-shared | SDK wraps returns in `{"blocks":[...], "raw_output":<orig>, ...}`; `entity_id` path needs `raw_output.` prefix. |
| OpenAI Agents SDK | schema-shared | No envelope. |
| AutoGen | schema-shared | `entity_id` not extractable (Python `str(dict)` is not valid JSON). |
| Smolagents | schema-shared | `Tool.__call__` wrap; end-to-end cascade verified. |

Full results and per-instrumentor path table: [`docs/OPENINFERENCE_FRAMEWORK_EXPANSION_RESULTS.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/OPENINFERENCE_FRAMEWORK_EXPANSION_RESULTS.md), [`docs/OPENINFERENCE_FRAMEWORK_EXPANSION_TIER2_RESULTS.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/OPENINFERENCE_FRAMEWORK_EXPANSION_TIER2_RESULTS.md).

### Framework real-workload validation (Task #9 Phase B)

Beyond fixture coverage above, the full pipeline (ingest → 4 deterministic detectors + opt-in LLM-judge) was executed against real workloads of 4 Tier 1 frameworks under a fixed FizzBuzz retry-loop scenario, all using `claude-sonnet-4-5`:

| Framework | Instrumentation | CR events | CR % of input | Verdict |
|---|---|---|---|---|
| Anthropic SDK (direct wrap) | Helper wrap | 9 | **43.9%** | ✅ PASS |
| LlamaIndex FunctionAgent | Official OI | 6 | **40.9%** | ✅ PASS |
| OpenAI Agents SDK | Official OI (LiteLLM → Claude) | 4 | **35.5%** | ✅ PASS |
| AutoGen AssistantAgent | Official OI v0.1.10 | 0 | — | ❌ EMPTY |

Pre-registered §3 threshold ≥ 3/4 PASS → **GO**. AutoGen's instrumentor emits agent/tool spans but not the underlying LLM span (framework limitation, not a detector defect — see §12.4 of the prereg). The `repeat` detector, Redundant Read, and LLM-judge returned 0 across all four frameworks — the FizzBuzz scenario (3-6 turns, no realized retries, no Read tool) does not stimulate those detectors by construction (§12.7). Total API cost: ~$0.099 of a $10 budget cap.

Pre-registration + results: [`docs/TASK9_FRAMEWORK_REAL_WORKLOAD_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/TASK9_FRAMEWORK_REAL_WORKLOAD_PREREG.md).

### Registering your own tools

LangChain / CrewAI apps typically name their tools inside application code (`search_web`, `create_ticket`). Register them so waste is not stuck in `unclassified`:

```yaml
version: 1
tools:
  search_web:    { category: read_only }
  create_ticket: { category: side_effect, entity_id: response.ticket.id }
  run_python:    { category: payload_dependent }
  finalize:      { category: declarative }
```

Four categories, fail-fast validation, guardrails against advertising unmeasured paths. Details in [`docs/OPENINFERENCE_ADAPTER_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/OPENINFERENCE_ADAPTER_PREREG.md).

---

## Where it stands

### RedundancyBench (labeled ground truth)

Human-labeled benchmark ([arXiv:2605.29893](https://arxiv.org/abs/2605.29893)). Same `evaluate.py` imported directly from the paper's repo, all four redundancy categories:

| | Boxdawn (deterministic) | Best method in the paper (LLM-as-judge) |
|---|---|---|
| Step-level F1 | **0.2642** | 0.2488 |
| Precision | 0.826 | n/a |
| Recall | 0.157 | n/a |

F1 0.2642 vs the paper's best LLM-as-judge 0.2488, with zero model calls. Recall 0.157 is by design: one pattern (`repeat` / `requery`), precisely. The rest is deliberately out of scope; see *What Boxdawn doesn't do*.

Precision 0.826 may be a lower bound on Boxdawn's file-level precision: of the 22 false-positive spans against the human labels, 21 were exact input-and-output repeats that no annotator labeled under any category, and 6 had zero state change in between. We do not claim all 22 are true waste; the label is genuinely ambiguous there.

### trace-commons (28 Claude Code sessions)

Public dataset ([HF: trace-commons/agent-traces](https://huggingface.co/datasets/trace-commons/agent-traces)), full scan on 2026-07-19. **28 / 28** processed, **0 crashes**. **10 / 28** flagged (34 byte-identical repeated tool calls in the cascade output; 32 after the tool-error gate). **A repeat is not the same as avoidable.** We hand-coded all 34 against what happened between the two calls ([`ACCEPTED_PAIR_PRECISION_RESULTS`](https://github.com/boxdawn/boxdawn/blob/main/docs/ACCEPTED_PAIR_PRECISION_RESULTS.md), pre-registered): **9** were avoidable when the second call was made, **23** were a build, test or generated-file write re-run after an edit (only running it could show the edit had not changed the result), and 2 could not be settled. The amplification cost of all 34, re-measured against 0.5.14 on 2026-10-13, is **$12.71 to $127.14** (cache-hit lower to cache-miss upper; 42,380,000 amplified tokens). It prices the 23 re-checks too, so it is **not a saving available**. It is also not spread across the ten: a single 18-repeat session is **98.15%** of the total ($12.48 to $124.79), and in that session 3 of the 18 were avoidable. No single-session figure from this corpus should be read as typical.

*Cost estimation is Claude Code only. It is an estimate of what the repeated calls' output cost to carry forward, not measured cost, and not a saving: it does not separate avoidable repeats from re-checks.* The formula is `amp_tokens_i = waste_tokens_i × turns_after_i`, with `lower_i = amp_tokens × cache_read_price` and `upper_i = amp_tokens × base_input_price`. The repeated output is re-consumed as input on every subsequent turn; that is where the number comes from. Other adapters (OTel, OpenInference, Toolathlon) still detect waste but do not populate the cache-token fields the amplification calculator needs.

### Toolathlon (6,780 trajectories, cross-model scale)

Boxdawn ran unmodified over Toolathlon (22 frontier models × 3 runs, [arXiv:2510.25726](https://arxiv.org/abs/2510.25726), CC-BY-4.0). 176,270 tool spans, 8,042 duplicate pairs. Excluding the `idempotent` grey area leaves **4,249 pairs (2.41% of tool spans)**, roughly **3× the rate seen on Claude Code sessions (0.80%)**. The Canvas hero above is one of these. Both rates count byte-identical repeats, and the two corpora repeat for opposite reasons: on a hand-coded sample of 100 of the 4,249, **75** were avoidable at call time, mostly agents looping on the same failing call; on Claude Code it was **9 of 34**, mostly edit-then-recheck ([`ACCEPTED_PAIR_PRECISION_RESULTS`](https://github.com/boxdawn/boxdawn/blob/main/docs/ACCEPTED_PAIR_PRECISION_RESULTS.md)).

Duplicate creation check across the same corpus: **3,432 same-input side-effect pairs** scanned, **159 (4.63%) with differing entity IDs**, **76 (2.21%) with the same ID**, **3,197 (93.15%) without an extractable entity ID** (audit blind spot, not a verdict).

Toolathlon ships pass/fail labels, not step-level ground truth. Per-model rates vary 54× (0.157 to 8.463 candidate density per trajectory). "Model X wastes N× more than model Y" is not a claim we make; task-mix and success-rate confounds are uncontrolled.

### Context Resend Detector — coding agent workloads

New in Tier 1. Measures the input-side cost of chunks (message-array elements) resent byte-exact across LLM calls within one trace. Deterministic (sha256 chunk hash + provider-reported input token counts).

Aggregate over the same trace-commons corpus (28 CC sessions, `data/hf_recon/trace_commons_paths.txt`, `random.Random(seed=42)` order):

- **`resent_cost / total_input_cost = 0.8876`** (88.8%) on the billed basis, over all 28 sessions (`304.6921 / 343.2929`); per-session median 0.7742. Until the [2026-10-21 correction](#correction-2026-10-21--corpus-a-wr_cost-was-08986) this read 0.8985 (89.9%); until the [2026-10-19 one](#correction-2026-10-19--corpus-a-wr_cost-was-08449) this read 0.8448 (84.5%) over 23 sessions
- **95% bootstrap CI [0.8214, 0.9111]** (`n_boot=1000, seed=42`, over the 28 sessions; this line showed [0.8102, 0.8730], the 23-session interval, until 2026-10-21, see the [correction](#correction-2026-10-21--corpus-a-wr_cost-was-08986))
- By tokens rather than dollars, resent / input over all 28 sessions is 0.9854 (0.9851 before 0.5.23)
- Pre-registered §7 threshold `≥ 0.20` → **GO** on either basis

Until 0.5.16 the first line read **0.9851** on a no-cache basis: every input token priced at the base rate. The detector has priced by cache tier since 0.5.13, so that basis is retired. The token ratio rounded to the same four digits until 0.5.23, which moved it to 0.9854; it is a different quantity. See the [2026-10-15 correction](#correction-2026-10-15--corpus-a-wr_cost-was-09731).

**Caching caveat — the estimate in this paragraph was wrong, and the measurement it asked for now exists.** It read: *"Anthropic `cache_read_input_tokens` bills at ~10% of the input rate. The 98.5% structural resend corresponds to roughly 8-15% of effective billed input cost … requires a v2 cache-tier split to measure directly."* The cache-tier split was built, and on the billed basis the same corpus measures **88.8%** (89.9% before the [2026-10-21 correction](#correction-2026-10-21--corpus-a-wr_cost-was-08986), 84.5% before the [2026-10-19 one](#correction-2026-10-19--corpus-a-wr_cost-was-08449), 97.3% before the [2026-10-15 one](#correction-2026-10-15--corpus-a-wr_cost-was-09731)), not 8-15%.

The estimate assumed the cache discount applies to the resent tokens and not to the total. It applies to both. When most of a session's input is a cache read, the numerator and the denominator are discounted together and the **ratio barely moves** — that is what a ratio does. The no-cache 0.9851 this paragraph was written against has since been retired (see above); what this paragraph corrected is the guess about what the billed basis would show. See the correction note below, which is the same arithmetic error found in the same corpus from the other direction.

Pre-registration + honesty preface: [`docs/CONTEXT_RESEND_DETECTOR_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/CONTEXT_RESEND_DETECTOR_PREREG.md).

### Waste-rate metric — cross-corpus (Tier 1)

Union of the four deterministic detectors (`repeat`, `context_resend`, `redundant_read`, `duplicate_creation`) into three per-corpus metrics: `WR_char` (UTF-8 byte ratio), `WR_cost` (dollar ratio via existing cost attribution), `SDR@10` (share of sessions with `WR_char ≥ 0.10`). Spec: [`docs/WASTE_RATE_METRIC_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/WASTE_RATE_METRIC_PREREG.md). Toolathlon adapter amendment (2026-08-11): [`docs/WASTE_RATE_TOOLATHLON_ADAPTER_AMENDMENT_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/WASTE_RATE_TOOLATHLON_ADAPTER_AMENDMENT_PREREG.md).

| Corpus | Included | `union_wr_char` | `union_wr_cost` | `union_sdr_at_10` | 95% bootstrap CI on `wr_char` |
|---|---:|---:|---:|---:|---|
| A · trace-commons (28 CC sessions) | 28 / 28 · cost 28 / 28 ([corrected](#correction-2026-10-19--corpus-a-wr_cost-was-08449), was 23 / 28) | **0.9916** ([corrected](#correction-2026-10-15--corpus-a-wr_cost-was-09731), was 0.9930) | **0.8876** ([corrected](#correction-2026-10-21--corpus-a-wr_cost-was-08986), was 0.8986; [before that](#correction-2026-10-19--corpus-a-wr_cost-was-08449) 0.8449; [and before that](#correction-2026-10-15--corpus-a-wr_cost-was-09731) 0.9731 and [0.2903](#correction-2026-09-01--corpus-a-wr_cost-was-02903)) | **0.9643** | [0.9839, 0.9939] |
| B · Toolathlon (6,780 non-coding trajectories, 22 frontier models) | 6,659 / 6,780 | **0.9342** | **0.9202** | **0.9908** | [0.9314, 0.9368] |
| C · Exgentic Agent LLM Traces v2 (10,056 sessions, 5 frontier models × 6 benchmarks, up to 3.7M tokens / session) | 10,056 / 10,056 | **0.9233** | **0.9397** | **0.9332** | per-session mean [0.7827, 0.7920] — union CI not computed, see [amendment §10.2](https://github.com/boxdawn/boxdawn/blob/main/docs/WASTE_RATE_EXGENTIC_ADAPTER_AMENDMENT_PREREG.md#102-aggregate-post-adapter) |
| D · MIMO Claude Code traces (1,017 generated sessions, single model `mimo-v2.5-pro`, median 4 tool calls) | 859 / 1,017 | **0.7993** | — (model absent from the pricing table, [prereg §3](https://github.com/boxdawn/boxdawn/blob/main/docs/WASTE_RATE_CORPUS_D_MIMO_CC_PREREG.md#3-pricing-this-corpus-cannot-carry-a-wr_cost-figure)) | **0.9441** | [0.7776, 0.8168] |

Corpus B `WR_cost = 0.9202` — the [Cost Table Toolathlon Expansion](https://github.com/boxdawn/boxdawn/blob/main/docs/COST_TABLE_TOOLATHLON_EXPANSION_PREREG.md) (2026-08-11) closed the 98.2% pricing gap first (bringing the raw scan to 0.9189), and the [union arithmetic amendment §14](https://github.com/boxdawn/boxdawn/blob/main/docs/WASTE_RATE_METRIC_PREREG.md#14-amendment--union_wr_cost-per-span-attribution-2026-08-15) (2026-08-15) restored `redundant_read`'s +0.0013 previously dropped by a span-metadata recomputation shortcut. 6,780 / 6,780 (100%) built trajectories priced, median `cost_ratio = 1.000` against Toolathlon's own provider-billed totals. Corpus B fidelity: 5,445 / 6,659 (81.8%) exact count-match against `agent_llm_requests`; the remaining 18.2% differ by exactly `+1` due to trajectories ending on a `role=tool` message (root-caused in amendment §10.2). Token sum invariant preserved on 100% of built traces.

**Amendment prediction verdict.** P1 `union_wr_char ∈ [0.85, 0.999]`: pass (0.9342). P2 `union_sdr_at_10 ∈ [0.85, 1.00]`: pass (0.9908). P3 `union_wr_cost ∈ [0.10, 0.50]`: **miss** (0.9189). ⚠️ **The explanation published with this miss is superseded.** It read: *"the band was calibrated on Corpus A's cache-tier-aware billing; Toolathlon's adapter §1.4 encodes uncached-only billing by pre-commitment, so `WR_cost` collapses toward `WR_char`. Category error in the prediction, not a metric defect."* Both halves are now known to be wrong. The band was calibrated on Corpus A's **0.2903**, which the correction below shows was an artifact of two defects — so there *was* a metric defect, and Corpus A's denominator was not cache-tier-aware. On one basis the two corpora are **0.9731** and **0.9202** (Corpus A is now **0.8876**, [2026-10-21 correction](#correction-2026-10-21--corpus-a-wr_cost-was-08986)): they never differed by much, and the band was low for both. The miss stands as published; only its reason changes. Original: [Cost Table Expansion §8.7](https://github.com/boxdawn/boxdawn/blob/main/docs/COST_TABLE_TOOLATHLON_EXPANSION_PREREG.md); band and adapter unchanged. P4 `context_resend ≥ 95%` of union numerator: pass (99.76%). No prediction band was adjusted post-hoc.

**Corpus D and what its prediction missed.** Corpus D was pre-registered before it was scanned, and one of its five predictions failed: P1 named `union_wr_char ∈ [0.80, 0.95]` and the scan returned **0.7993** — outside it, low, by 0.0007. The bootstrap CI [0.7776, 0.8168] straddles the boundary, but P1 was written about the point estimate and is reported as a miss. P2–P5 passed, P5 exactly (859 included, 158 excluded, zero ingest failures across 1,017 files). What the miss corrects is reach, not mechanism: split by session length the rate climbs monotonically — **0.3487** at 1–2 tool calls, **0.6453** at 3–5, **0.7767** at 6–10, **0.8802** at 11+ — so a corpus whose median session is four tool calls lands below a range estimated from corpora made of long ones. The per-session spread is wide by the same mechanism (p10 0.1722, p50 0.6297, p90 0.8104), which is why no single-session figure from this corpus may be cited. `WR_cost` is absent rather than suppressed: `mimo-v2.5-pro` is not in the pricing table, and the summed input cost across all 859 traces is 0.0. Full result: [`docs/WASTE_RATE_CORPUS_D_MIMO_CC_RESULTS.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/WASTE_RATE_CORPUS_D_MIMO_CC_RESULTS.md).

**Reading the numbers honestly.** LLM APIs are stateless — every call must include the full conversation. Some resend is mechanically required. `WR_char` measures the total resend footprint in bytes; `WR_cost` measures **the share of what was actually billed for input that went to sending the same thing again**.

Corpus A **88.8%** (89.9% before the [2026-10-21 correction](#correction-2026-10-21--corpus-a-wr_cost-was-08986), 84.5% before the [2026-10-19 one](#correction-2026-10-19--corpus-a-wr_cost-was-08449), 97.3% before the [2026-10-15 one](#correction-2026-10-15--corpus-a-wr_cost-was-09731)) and Corpus B **92.0%** are now on the same basis and in the same range, which is the finding. The earlier version of this paragraph read the gap between them (29% vs 92%) as "the caching lever's leverage" — **that reading was an artifact.** The two figures were never on the same footing: Corpus A's denominator was priced as though no caching existed while its numerator was priced as billed, and Corpus B's adapter pre-commits to uncached-only billing (§1.4) so both of its sides were already consistent. Corpus A was the only one mixed.

What the corrected figures say instead: **caching changes what you pay, not what fraction of it is resend.** Both sides of the ratio get the discount. A session that caches well pays less in absolute dollars — Corpus A's 23 then-priced sessions billed $149.47 against a no-cache counterfactual of $1,130.76 when both were last computed (2026-09-01) — and still spends about the same *share* of that bill on context it had already sent. The absolute saving is real and large; the ratio is not where it shows up.

<a id="correction-2026-09-01--corpus-a-wr_cost-was-02903"></a>

**Correction, 2026-09-01: Corpus A `union_wr_cost` was published as 0.2903 and is 0.9731.** Two defects, in opposite directions, and each one hid the other.

1. **Mixed price bases.** The numerator priced a resent token at the rate it was billed (cache reads at 10%); the denominator priced every input token at the base rate, which is what the session *would* have cost with no caching. Median inflation of the denominator across the 23 sessions that have one: **7.71×** ($149.47 billed against a $1,130.76 counterfactual, 7.56× in aggregate).
2. **An unpaired numerator.** Five of the 28 sessions use models absent from the pricing table. Their cost denominator was 0 and they were dropped from it — but their waste cost stayed in the numerator. That is **$182.79 of $328.24, or 55.7%**, divided by nothing.

The first pushed the ratio down, the second pushed it up, and 0.2903 is what they left. Fixing only one would have produced 0.1286 or 2.1960; **2.1960 is the value that exposed both**, because a waste ratio above 1 is not a number.

Corrected: **145.4490 / 149.4728 = 0.9731** over the 23 sessions priced on both sides. Per-session spread p10 **0.5286**, median **0.9585**, p90 **0.9859**.

Scope, checked rather than assumed: **`WR_char` did not move** — bit-identical on all 28 sessions, aggregate `0.9930314441223987` unchanged. **Corpus B and Corpus C are unaffected**, verified by re-running both: zero rows with a numerator and no denominator in either (B prices 100% of its models; C computes both sides through one function). **Corpus D never had a `WR_cost` figure.** No stored figure changed, because no ratio is stored — only numerators and denominators, separately. A user running `analyze` on an unpriced trace has always seen no cost ratio rather than a wrong one; the defect was in the corpus aggregation that produced this table.

Pre-registrations, results and the rejected predictions: [`WR_COST_PRICE_BASIS_AMENDMENT_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/WR_COST_PRICE_BASIS_AMENDMENT_PREREG.md) · [`_RESULTS.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/WR_COST_PRICE_BASIS_AMENDMENT_RESULTS.md) · [`_2_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/WR_COST_PRICE_BASIS_AMENDMENT_2_PREREG.md) · [`_2_RESULTS.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/WR_COST_PRICE_BASIS_AMENDMENT_2_RESULTS.md).

**This correction moves our own headline figure up by 3.35×.** That is the direction a reader should be most suspicious of, which is why the arithmetic, the old number and the two rejected predictions are all above rather than summarized away.

<a id="correction-2026-10-15--corpus-a-wr_cost-was-09731"></a>

**Correction, 2026-10-15: Corpus A `union_wr_cost` was published as 0.9731 and is 0.8449.** Two causes, both pushing the same way.

1. **Later pricing fixes were never carried into this table.** Between 2026-09-01 and 0.5.15, releases changed how Claude Code calls are counted and how resent tokens are priced (`#247`, `#249`, `#250` among them). The cited trace's figures were re-measured and republished each time; this table was not. On code with those fixes and without the next one, the 23 priced sessions give **129.6614 / 147.6331 = 0.8783**. The numerator fell 10.9%, the denominator 1.2%, and 22 of the 23 sessions moved down. We did not split the drop between the individual fixes. Re-running the 2026-09-01 artifact by the same method reproduces 0.9731 exactly, so the gap comes from the code, not the method.
2. **The Claude Code adapter ignored context compaction.** Fixed in 0.5.16 (`#278`). After an auto-compaction, Claude Code sends a summary in place of the history. The adapter kept the history, so the resend detector counted unsent context as resent. 7 of the 28 sessions compact. With the fix the figure is **124.7402 / 147.6331 = 0.8449**. All 7 move down, the largest from 0.8549 to 0.7557, and the other 21 are byte-identical.

| | `union_wr_char` (28) | `union_wr_cost` (23 priced) | `union_sdr_at_10` |
|---|---:|---:|---:|
| published 2026-09-01 | 0.9930 | 0.9731 | 0.9643 |
| with later pricing fixes, before 0.5.16 | 0.9925 | 0.8783 | 0.9643 |
| 0.5.16 | **0.9916** | **0.8449** | 0.9643 |

Verified on 0.5.16, 2026-10-15: the per-session `wr_cost` spread is p10 **0.3122**, median **0.7815** and p90 **0.9190**, against 0.5286, 0.9585 and 0.9859 on 2026-09-01.

Scope, checked rather than assumed:

- The cited trace behind the home page's 88.7% has no compaction, and its published figures are identical on 0.5.16.
- Corpus D (MIMO, 1,017 sessions) has no compaction entry and does not move.
- Corpus B and C use other adapters, which the compaction fix does not touch. **They have not been re-measured against the later pricing fixes**, so their `WR_cost` figures stand as published until they are.
  *Update, 2026-10-21:* both have since been re-measured, B on `10ac2ab` (2026-10-20) and C on `ed3a27e`, both 0.5.22 in `src/clew/ingest/toolathlon.py`, `exgentic.py` and `metrics/`. The figures in the table above are bit-identical: B `union_wr_char` 0.9342, `union_wr_cost` 0.9202, `union_sdr_at_10` 0.9908 and the `wr_char` CI; C `union_wr_char` 0.9233, `union_wr_cost` 0.9397, `sdr_at_10` 0.9332 and the per-session `wr_char` CI. C's aggregate sums are bit-identical too. Per session, 2,760 of 6,780 B rows and 1,995 of 10,056 C rows differ only in the last bits (at most 7.1e-15 and 5.7e-14), and B's single-detector `context_resend` ratio, published as 0.9189, moved in its last bit only.
- Still open: in 1,557 trace-commons calls the reconstructed input measures more tokens than were billed. The causes, identified on 2026-10-17, are images (710 calls) and thinking-block signatures (839). Both are base64 that the tokenizer counts by length. The other 8 are `<synthetic>` entries with no usage ([`CC_INPUT_OVERFLOW_CAUSES_RESULTS`](https://github.com/boxdawn/boxdawn/blob/main/docs/CC_INPUT_OVERFLOW_CAUSES_RESULTS.md)). Counting chunks with images and signatures removed moves Corpus A `union_wr_cost` from 0.8449 to 0.8457 and leaves `union_wr_char` bit-identical (measured 2026-10-18). That removal counts images as zero tokens, which they are not, so it is a bound and not a corrected figure. The figures above are unchanged, and no release fixes this yet.
  *Update, 2026-10-21:* the last sentence of this bullet held until 0.5.23. From 0.5.23 images are weighted as billed, and the figures above have moved ([correction](#correction-2026-10-21--corpus-a-wr_cost-was-08986)). Of the 1,557 calls, 848 still measure more than their bill with images weighted; removing signatures as well leaves only the 8 `<synthetic>` entries. Signatures are still counted by length.

Details are in [`docs/CONTEXT_RESEND_DECOMPOSITION_RESULTS.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/CONTEXT_RESEND_DECOMPOSITION_RESULTS.md) §6.

**This correction moves our headline figure down, by 0.128.** We found both causes ourselves: the first by re-running a published figure against shipped code, the second while checking a result of our own.

<a id="correction-2026-10-19--corpus-a-wr_cost-was-08449"></a>

**Correction, 2026-10-19: Corpus A `union_wr_cost` was published as 0.8449 over 23 sessions and is 0.8986 over all 28.** The five sessions left out were not unpriceable. All five run `claude-opus-4-8`, and the script that builds this table prices only the model names on a fixed list, which did not include it. `boxdawn analyze` has priced them all along, at Opus 4.7's rates; Anthropic's pricing page lists the two models at the same five rates (read 2026-10-19). The sentence in the 2026-09-01 correction above, that a user on an unpriced trace sees no ratio rather than a wrong one, still holds for unpriced traces. These five were not that: they were priced for every user and missing from this table only.

| | priced | `union_wr_cost` | `resent_cost / total_input_cost` | per-session `wr_cost` p10 / median / p90 |
|---|---:|---:|---:|---|
| before | 23 / 28 | 124.7402 / 147.6331 = **0.8449** | 0.8448 | 0.3122 / 0.7815 / 0.9190 |
| after | 28 / 28 | 308.4824 / 343.2929 = **0.8986** | 0.8985 | 0.2648 / 0.7743 / 0.9239 |

- The five sessions are $195.66 of the $343.29 denominator (57%). One of them is $118.44 (34.5%), with its own `wr_cost` 0.9628. The figure now leans on that one session more than on any other.
- `union_wr_char` 0.9916 and `union_sdr_at_10` 0.9643 do not move, and the 23 sessions already priced are bit-identical.
- Corpus B and D share the script's rate tables and do not move: neither contains an Opus 4.8 model string (0 in 66 Toolathlon files, 0 in 1,017 MIMO sessions).

Pre-registration and results: [`docs/CORPUS_A_OPUS48_PRICING_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/CORPUS_A_OPUS48_PRICING_PREREG.md).

**This correction moves our headline figure up, by 0.0537.** We found it by comparing the table against what `boxdawn analyze` prints for the same sessions.

<a id="correction-2026-10-21--corpus-a-wr_cost-was-08986"></a>

**Correction, 2026-10-21: Corpus A `union_wr_cost` was published as 0.8986 and is 0.8876.** The resend detector splits each call's billed input across the call's messages by their token length. A message that carries a screenshot was measured by the length of its base64 text, which has nothing to do with what the image is billed. From 0.5.23, an image in a Claude call weighs the visual tokens it is billed (`⌈width/28⌉ × ⌈height/28⌉` after Anthropic's documented resize, by model tier). Each call's bill is unchanged, so the denominator does not move; what changes is how much of each bill lands on resent messages.

| | `union_wr_cost` | `resent_cost / total_input_cost` | per-session `wr_cost` p10 / median / p90 |
|---|---:|---:|---|
| before (0.5.22) | 308.4824 / 343.2929 = **0.8986** | 0.8985 | 0.2648 / 0.7743 / 0.9239 |
| after (0.5.23) | 304.7158 / 343.2929 = **0.8876** | **0.8876** | 0.2648 / 0.7743 / **0.9176** |

- 7 of the 28 sessions carry screenshots. 5 fall and 2 rise; the largest moves are 0.9013 → 0.8391 and 0.8448 → 0.8718. In every one of them the resent messages are the same, event for event; only the tokens and dollars attached to each change.
- $3.47 of the $3.77 fall is one session, the one that is 34.5% of the denominator (see the 2026-10-19 correction above).
- `union_wr_char` 0.9916 and `union_sdr_at_10` 0.9643 are bit-identical, and so are the 21 sessions without screenshots.
- Corpus B, C and D do not move: none of their Claude calls carries an image block (B 27,365 Claude calls, C 55,789, D none).
- The cited trace behind the home page's 88.7% has no screenshot. Its report is identical on 0.5.23 apart from the time it was generated.
- Thinking-block signatures are still counted by length. What they are billed (the original thinking tokens) is not in a Claude Code transcript.
- Also corrected here: the bootstrap interval under the `Context Resend Detector` heading had not been recomputed when the 2026-10-19 correction moved its point estimate from 23 sessions to 28. It still showed the 23-session interval [0.8102, 0.8730], which does not contain 0.8985. Over the 28 sessions it was [0.8211, 0.9293] on 0.5.22 and is [0.8214, 0.9111] on 0.5.23. The by-tokens ratio moves from 0.9851 to 0.9854.

Pre-registration and results, including the prediction this missed (we expected a move under 0.005): [`docs/CC_IMAGE_TOKEN_SHARE_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/CC_IMAGE_TOKEN_SHARE_PREREG.md).

**This correction moves our headline figure down, by 0.0110.**

**Note on `union_wr_char` vs `Context Resend Detector 88.8%` above.** These are two different measurements. `Context Resend Detector 88.8%` is `resent_cost / total_input_cost` on the 28 priced CC sessions, single-detector. `union_wr_char` is the union across all four Tier 1 detectors on the same 28 CC sessions (`0.9916`), plus the 6,780-trajectory Corpus B extension. Both numbers are correct for their respective definitions; they are not interchangeable.

### Redundant Read Detector — standalone

New in Tier 1, distinct from the retired v0.3.0 reread cascade integration (see *What Boxdawn doesn't do* below). Emits its own `RedundantReadResult` with per-event tokens/dollars, contributes a distinct entry in the unified cost summary, and works cross-adapter (Claude Code, OpenInference, Toolathlon). Gate: both spans are read-nature tools on the same normalized target, the interval contains no write to that target and no payload-opaque shell tool, and (when the parent structure is known) both spans share the same nearest-AGENT ancestor. Output-identity is a strengthening flag, not a requirement — the pair is `confirmed=True` when outputs are byte-identical.

Pre-registration: [`docs/REDUNDANT_READ_DETECTOR_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/REDUNDANT_READ_DETECTOR_PREREG.md).

### LLM-as-Judge Semantic Duplicate (opt-in)

Semantic-equivalence check on chunk pairs that already pass a Jaccard pre-filter (threshold `0.30`, max 50 judged pairs per session). Uses `claude-haiku-4-5` as judge. **Default OFF**; requires explicit opt-in per session with a hard cost cap.

Two data points from Go/No-go measurement on 5 CC sessions (`seed=42`, `data/hf_recon/trace_commons_paths.txt`), both retained:

| Measurement | Matches / Pairs | Ratio | Cost | Verdict |
|---|---|---|---|---|
| Pre-amendment (base spec) | 4 / 159 | 0.0252 | $0.131 | SHIP-AS-IS |
| Post-amendment v1 (n=5 CC) | 83 / 159 | **0.5220** | $0.133 | **GO** |

Amendment v1 changes: (1) response parser strips markdown code fences (all 159 base responses were fence-wrapped); (2) rubric explicitly ignores randomly-generated per-invocation identifiers (`tool_use_id`, etc.) as non-semantic. Both changes were made **after** seeing the 2.52% baseline; the amendment document's honesty preface acknowledges the p-hacking risk and retains both data points as a joint record.

**Scale expansion (Amendment v2 · 2026-08-11 → 2026-08-12).** The n=5 v1 headline was recomputed on **n=48 sessions** (28 CC + 20 Toolathlon, `seed=42`, ~12h, $2.58):

| Corpus | n | Matches / Pairs | Precision |
|---|---:|---|---:|
| CC | 28 | 571 / 1,178 | **0.4847** |
| Toolathlon | 20 | 96 / 924 | **0.1039** |
| Unified | 48 | 667 / 2,102 | **0.3173** |

Bootstrap 95% CI on unified precision: **[0.2311, 0.4103]** (`n_boot=1000, seed=42`).

**Headline correction.** The 52.20% figure was measured on n=5 CC and did not survive scale. The corrected number for pitch material is **31.7% unified** (n=48, CI [23.1%, 41.0%]) — or **48.5% CC-only** for the same-corpus comparison. The v1 GO judgment stands (0.317 remains well above the base prereg 5% GO threshold); v1 and v2 data points are retained together per the honesty preface.

**These are detector precision figures** — of judge-evaluated candidate pairs, how many were confirmed equivalent. They are **not** trace-level waste rates. A separate metric would be needed to answer "what fraction of input tokens are wasted by semantic duplicates".

Pre-registration: [`docs/LLM_JUDGE_SEMANTIC_DUPLICATE_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/LLM_JUDGE_SEMANTIC_DUPLICATE_PREREG.md); amendment v1: [`docs/LLM_JUDGE_AMENDMENT_v1.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/LLM_JUDGE_AMENDMENT_v1.md); scale expansion (v2): [`docs/LLM_JUDGE_SCALE_EXPANSION_AMENDMENT_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/LLM_JUDGE_SCALE_EXPANSION_AMENDMENT_PREREG.md).

### Cost attribution (Tier 1 · unified summary)

Prior versions priced only Claude Sonnet 4.5. As of the Cost Attribution Completion prereg, pricing tables now cover Sonnet 4.5 / 4.6, Opus 4.7, Haiku 4.5, GPT-4o and GPT-4o mini, Gemini 1.5 Pro and 1.5 Flash — with 4-tier cache-aware rates where the provider exposes them. The report emits a unified `Total analyzed / Total waste / Waste ratio` block at the top, plus per-detector breakdown in dollars. Each pricing entry carries a source URL and ISO-8601 verification date.

Pre-registration: [`docs/COST_ATTRIBUTION_COMPLETION_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/COST_ATTRIBUTION_COMPLETION_PREREG.md).

---

## 🚀 Roadmap · running today, building next

Boxdawn is a chain: **monitor → detect → alert → auto-fix → auto-optimize + govern.**
Detection is the link that runs today, as a service and as a library. The rest is
being built in that order, because each link needs the one before it to be
trustworthy first.

**Running today**

- **Hosted analyzer, no account.** Drop a trace file at [boxdawn.com/analyze](https://boxdawn.com/analyze) and get the report the CLI prints. The file is processed in a temporary directory that is destroyed when the response finishes; it is not stored.
- **Four deterministic detectors** — `repeat`, `context_resend`, `redundant_read`, `duplicate_creation`. Same code, same frozen parameters, in the browser and on your machine.
- **Cost from real usage fields**, with per-model rates pinned to source URLs. Where a vendor's usage block is missing, the report says `estimated` rather than guessing quietly.
- **Accounts and per-project history.** A signed-in upload records derived numbers — counts, sizes, costs, and salted hashes of targets. The trace file itself is still not kept.
- **Daily waste rate, by session date.** The series is keyed on when your sessions ran, not on when we analyzed them, so a backfill of old traces lands on the days they happened.
- **API keys for CI and scripts.** Issue and revoke per project, so a trace can be sent with no browser in the loop.
- **Open-source CLI that runs offline.** No account, no upload, no network. The hosted layer is a convenience, not the product boundary.
- **Opt-in semantic pass.** LLM-as-judge on the pairs the deterministic gate cannot separate, off by default, with a hard cost cap per session.
- **Budget guard for Claude Code** (`0.5.18`). A local hook that stops a session once it has spent a dollar cap you set. No waste judgment, nothing sent. See §Use.

**Building next**

- **Baseline alerts** — "this project's waste rate moved more than its own normal variation". Pre-registered before implementation, including the thresholds and the bar for turning notification on: [`docs/BASELINE_REGRESSION_ALERT_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/BASELINE_REGRESSION_ALERT_PREREG.md).
- **Real-time monitoring** — the measurement arriving continuously rather than per upload.
- **Loop detection** — repetition that is going nowhere, distinguished from repetition that is working. The reasoning-level code path exists and has fired only on synthetic traces so far; see §What Boxdawn doesn't do.
- **Visual session flow** — the shape of a run, with the waste marked on it.
- **Latency alongside cost** — the same axis applied to time.
- **Auto-fix**, then **auto-optimize**, then **policy and governance.** In that order.

**Deliberately not on either list: blocking waste in real time, before the call is
made.** We built it, measured it against a threshold frozen beforehand, and it came in
under — so neither automatic blocking nor a confirmation prompt shipped, and neither is
planned until that changes. The measurement and its provenance are in
§What Boxdawn doesn't do, one entry down; they are not repeated here, because a number
with two homes is a number that will disagree with itself. Monitoring and alerting are a
different claim, and they are on the list above. The budget guard below (`0.5.18`) is not
this either: it stops a session at a dollar cap you set and makes no judgment about
whether any call was waste.

**Shipped since `0.5.4`:** `boxdawn submit` sends finished sessions to your project on a
pre-registered close rule ([`docs/SESSION_CLOSE_RULE_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/SESSION_CLOSE_RULE_PREREG.md)),
and it works end to end against live key issuance. Verified in a clean virtualenv on
`0.5.10`, 2026-09-04: `boxdawn submit --help` answers.

**Stack:** Vercel Next.js · Modal serverless Python (the detector runtime is this repo's code) · Supabase (Postgres + Auth) · Resend (email).

---

## How we keep ourselves honest

- **Pre-registration.** Every detection change is committed *before* results are run; predictions and stop-conditions are written first and not edited after.
- **Frozen parameters.** `φ`, `N`, and the embedding model are pinned to a git tag; changing them requires a documented recalibration, never a post-hoc nudge.
- **Published corrections.** Small-sample numbers that did not survive larger samples were retracted in the open (Toolathlon `1,343 → 1,195`, `4,251 → 4,249`; `"90% CI"` label corrected to `"95% two-sided"`; Corpus B `union_wr_cost 0.9189 → 0.9202` per [WASTE_RATE_METRIC_PREREG §14](https://github.com/boxdawn/boxdawn/blob/main/docs/WASTE_RATE_METRIC_PREREG.md#14-amendment--union_wr_cost-per-span-attribution-2026-08-15)). Two more were corrected on 2026-10-13. The trace-commons amplification range `$1.01–$10.12 → $12.71–$127.14`: it was measured on a release whose turn counter counted JSONL lines, which both inflated the per-event multiplier and silently dropped waste events; `#252` fixed the counter, and on this corpus the restored events outweigh the smaller multiplier. The Toolathlon `no_id` share `93.16% → 93.15%`: `3,197 / 3,432` is 93.1527%, and the three shares were rounded to sum to 100. The counts never moved, and the pre-registration documents still print `93.16%` because they are frozen. On 2026-10-14 the trace-commons wording was narrowed: the 34 spans were called "waste" and the dollar range "saving potential", and a pre-registered hand-coding then found 9 of the 34 avoidable at call time. The counts and the range did not move; what they are called did. A pre-registered prediction has also been published as failed rather than quietly widened: Corpus D's P1 named `union_wr_char ∈ [0.80, 0.95]` and the scan returned 0.7993. See [CHANGELOG.md](CHANGELOG.md).
- **Fixes driven by real data.** The trace-commons scan surfaced two adapter issues no synthetic test caught: session mid-run abort (3 / 28 crashes, recovered with `skip + warn`) and Anthropic `is_error: true` tool_result being sha256-identical (2 false positives across 269 error responses, gated at the report layer). See [`docs/CC_TRANSCRIPT.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/CC_TRANSCRIPT.md) §29.

700+ tests run on every pull request, with the frozen parameters enforced as failing ones. The count is given as a floor rather than a figure: this file is the PyPI page, it is published at release and not edited between releases, and an exact number is wrong the day after someone adds a test. The badge above reports the current run.

---

## Scope, stated plainly

The list below is what a serious evaluation would surface anyway, so it is here rather than in a footnote. Nothing in it is news to us.

- **No fixes**, only diagnosis. The output is a report you read. Prompt changes, context caching, and tool routing are yours to make.
- **No real-time interception.** The `args-only` real-time gate was retired at precision **0.6333** — 19 of 30 hand-annotated pairs, sampled from a pool of 3,432, measured 2026-07-25 against a threshold of 0.70 frozen beforehand. Below that bar neither auto-block nor a confirm-prompt is defensible, so neither shipped. The detectors read finished trace files, after the run. The one thing that acts during a run is the budget guard, which stops on a dollar cap you set, not on a waste judgment (§Use).
- **The v0.3.0 in-cascade `reread` gate was retired** at 3.3% precision on a 30-pair sample — `random.Random(42)` over a pool of 209 same-path Read pairs from the trace-commons corpus (28 Claude Code sessions), reproduced 2026-07-24 against a threshold of 0.70 frozen beforehand: 29 of 30 pairs were legitimate chunked reads at different `offset` / `limit` values. See [`docs/REREAD_DETECTOR_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/REREAD_DETECTOR_PREREG.md) §11. The current standalone **Redundant Read Detector** (see *Where it stands* above) is a different approach: it requires interval-clean gating (no intervening write to the same target, no payload-opaque shell tool in the interval) before flagging, and emits per-event tokens/dollars rather than bundling into the cascade waste-cost line.
- **No reasoning-level `pingpong`.** Code path exists but has fired only on synthetic traces. Blocked pending an external corpus that surfaces it, not killed.
- **Tool coverage is 26.4% on Toolathlon** (138 of 523 unique tool names). Unmapped tools drop into `unclassified` and reduce interval-scan tier precision. The banner shows coverage on your specific trace; `clew.yaml` closes the gap (config file name kept for backward compatibility).
- **A repeated call is not proven avoidable, and cost is not a saving.** On Claude Code, 9 of the 34 byte-identical repeats were avoidable at call time; most were re-checks after an edit ([`ACCEPTED_PAIR_PRECISION_RESULTS`](https://github.com/boxdawn/boxdawn/blob/main/docs/ACCEPTED_PAIR_PRECISION_RESULTS.md)). Cost is estimated, not measured: the amplification formula assumes repeated output is re-consumed each subsequent turn (structural upper bound). Cache-hit lower to cache-miss upper; the exact split is not observable from vendor usage. Sonnet pricing assumed.
- **Toolathlon numbers are benchmark trajectories, not production sessions.** Scale evidence, not user data.
- **459 same-argument `emails-send_email` pairs on Toolathlon are not proven duplicates.** The tool does not return an entity ID, so `Duplicate creation check` cannot resolve them. They sit in the 3,197 `no_id` blind spot, surfaced but not claimed as a finding.
- **Semantic embedding does not carry the precision.** Same-topic real-world outputs do not cleanly separate in embedding space; the sha256 structural gate carries the precision result. We say so rather than imply the model is doing the work.

---

## Install

**`pip install boxdawn` is the whole install** (lightweight; no torch): the sha256 structural gate, the four deterministic detectors, cost attribution and the waste-rate metric. Covers Claude Code, Toolathlon, RedundancyBench, and any OTel / OpenInference trace whose duplicated work sits at the tool layer. This is where every empirically validated detection so far comes from.

> Earlier docs said `pip install "boxdawn[detect]"`. That extra resolves to zero additional packages — the two installs are byte-identical — so it is no longer printed anywhere. It still resolves, so an older command keeps working.

`[semantic]` (optional, ~2 GB with CUDA torch): adds the cosine gate for non-tool spans. Required for LangGraph chain-node paraphrase duplication.

```bash
pip install "boxdawn[semantic]"
```

CPU-only torch on Linux:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install "boxdawn[semantic]"
```

From source:

```bash
pip install "boxdawn @ git+https://github.com/boxdawn/boxdawn.git"
```

Requires Python `≥ 3.12`.

## Use

```bash
boxdawn analyze path/to/trace.jsonl --out report.md
```

- Input: any auto-detected format from the table above.
- `--out` writes Markdown; `--json` writes structured output; `--no-snippets` omits output excerpts.
- Exit `0` whether or not waste is found; `1` on missing file, schema error, or missing detect dependencies.

Your Claude Code transcripts are at `~/.claude/projects/<slug>/<uuid>.jsonl`. Sub-agent traces sit one level deeper, in `<uuid>/subagents/agent-*.jsonl`. Since `0.5.19`, analyzing `<uuid>.jsonl` also reads those files, so the report's cost includes what the sub-agents spent, the same total the budget guard uses. Their tool calls are not yet checked for repeats. Since `0.5.21`, `boxdawn submit` sends a session's sub-agent files in the same request as the session, so the cloud report counts them too, as `analyze` does. The upload size limit applies to the session and its sub-agent files together, and `--dry-run` lists each sub-agent file under its session. A sub-agent file is never sent on its own: it carries its parent's session id, and the server would store it in place of the parent.

### Sending sessions automatically

```bash
boxdawn submit --dry-run    # list what would be sent, send nothing
boxdawn submit              # send it
```

Finds sessions that have gone quiet long enough to call finished, uploads each once, and never sends the same session twice. What counts as "finished" is preregistered rather than chosen here: [`docs/SESSION_CLOSE_RULE_PREREG.md`](https://github.com/boxdawn/boxdawn/blob/main/docs/SESSION_CLOSE_RULE_PREREG.md).

Needs a project key in `BOXDAWN_API_KEY` or `~/.clew/credentials.yaml`; sign in at [boxdawn.com](https://boxdawn.com) to issue one. `--dry-run` needs no key.

Start with `--dry-run`. A first run is a backfill of every session on the machine, not a trickle: 81 of 84 on the machine the rule was measured on.

### Stopping a Claude Code session at a dollar cap

```bash
boxdawn guard install --cap-usd 5 --warn-at 0.8   # in the project directory
boxdawn guard status
boxdawn guard uninstall
```

Adds one `PreToolUse` hook to the project's `.claude/settings.local.json` and leaves every other entry alone. Before each tool call, in the main agent and in subagents, it prices the session so far from the transcript, with the same price table the report uses. At or over the cap it denies that tool call and stops the session. `--warn-at` shows one warning per session at that fraction of the cap. Blocks and warnings are written to `~/.clew/guard_events.jsonl`; nothing is sent.

What it cannot do, stated up front:

- The total runs **up to the previous call**, because the call that asked for the tool is not in the transcript yet. A session can end past the cap by a call or two.
- When a subagent is stopped, the main agent is not told why. Its next tool call is denied, and that is when the reason appears on screen.
- A model call that uses no tool never triggers the hook, so it is not stopped.
- A model the price table does not know is priced at the default and still counted. The message then calls the total a lower bound.
- A subscription (Pro/Max) login is not billed per token, so a dollar cap means most with an API key.

Checked on Claude Code 2.1.299, 2026-10-17: on the trace behind the product page the guard's total is $1.9723945 over 27 calls, equal to the report's `total_analyzed_cost`. A tool call was denied at the cap and allowed under it, and in an interactive session a person confirmed that the warning and the stop reason both appear on screen.

---

## License

MIT. Built by **Boxdawn**.

External datasets referenced here (Toolathlon CC-BY-4.0, RedundancyBench MIT, trace-commons per its HF card) are analyzed locally and never redistributed.
