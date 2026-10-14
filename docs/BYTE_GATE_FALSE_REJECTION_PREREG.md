# Pre-registration — does the byte-identity gate throw away real duplicates?

Status: **pre-registration.** No outcome has been measured. The frame in §2 was
built and hashed on 2026-10-14 from pair keys and sha256 comparisons only; no
output text of any pair in it has been read.

## 0. Why this exists

The cascade's tool branch confirms a candidate pair only when
`sha256(origin.output) == sha256(candidate.output)` (`cascade.py:3-6`, `:76`).
Phi is never invoked on tool pairs. Every published duplicate count rides on this
one comparison: Toolathlon's **8,042** pairs, and the Claude Code **34** waste
spans behind **0.80%**, are exactly the byte-equal pairs (recounted 2026-10-14,
§2).

The gate has one failure direction nobody has measured. Two calls to the same
tool with the same normalised input can return outputs that differ only in a
timestamp, a request id or a duration, which is still a duplicate in every sense
the product means, and the gate rejects it. This study counts how often that
happens.

## 1. What is measured, and what is not

**Measured: the gate's false-rejection rate.** Of the tool pairs that reach the
sha256 comparison and fail it, what share carry the same information?

🔴 **Not measured:**
- **Precision of the pairs the gate accepts.** Whether all 8,042 byte-equal pairs
  are waste (a read repeated after a write, for example) is a different question
  with a different population. README already carves out one known grey area of
  it (`idempotent`, 8,042 → 4,249).
- **Pairs refused before the comparison.** `output_is_absent` pairs (60 on TRAIL
  gaia) and pairs across a compact boundary (29 on trace-commons) are decided by
  other guards and are outside the frame.
- **A replacement rule.** No `src/` change follows from this study directly. §6
  says what a result licenses.

## 2. The frame, frozen

Population = tool candidate pairs from `find_repeat_candidates(trace, 2)` that
pass the absence and compact guards and fail sha256 equality. Census of the
corpora this project already measures on (`_byte_gate_census`, shipped code at
`e4caaa7`):

| corpus | traces | tool pairs | absent | compact | **byte-equal** | **byte-differ** |
|---|---:|---:|---:|---:|---:|---:|
| CC trace-commons (the 28 behind 0.80%) | 28 | 153 | 6 | 29 | **34** | **84** |
| CC mimo-cc-1k, seed-42 sample | 120 | 12 | 0 | 0 | 4 | **8** |
| Toolathlon (Corpus B) | 6,780 | 17,101 | 0 | 0 | **8,042** | **9,059** |
| TRAIL gaia | 117 | 86 | 60 | 0 | 0 | **26** |
| TRAIL swe_bench | 30 | 0 | — | — | — | — |

Byte-equal reproduces both published counts exactly (34, 8,042). Toolathlon's
336 ingest failures are the known 336.

**2.1 Frozen by hash.** Pair key `{corpus}|{trace}|{origin_span_id}|{candidate_span_id}`,
sorted, newline-joined, UTF-8. Keys live in the uncommitted
`_byte_gate_frame.KEYS.json` (TRAIL forbids redistribution).

| subset | n | sha256 |
|---|---:|---|
| `cc_trace_commons_28` | 84 | `077a573423a238356869a1aa3a4186b90c63d64b974e604576dc9d400326391f` |
| `cc_mimo_120` | 8 | `d9fd8ab7e8863327027172958917acbd62e104e0be1b75b99e4d2c85e5fb565b` |
| `toolathlon` (full) | 9,059 | `4f39780fefbfae1c8bf10db2a74cb5bba1e533d42f25d40c28e410c6c7182d2c` |
| `toolathlon_sample` | 100 | `bd0776735c1578ced95e2112dc5f7500316f6c90061474a0966076c4fa2592ea` |
| `trail_gaia` | 26 | `8546f15c0ca77d5024ca30c4f17b00cbb98b60f7d9f02f85f7ce4ab77bcd4189` |

The Toolathlon sample is `random.Random(20261014).sample(sorted(keys), 100)`.
A hash mismatch at run time makes the run invalid, not the frame.

**2.2 What was seen before freezing.** Pair counts and the tool name of each
byte-differ pair. Top tools: trace-commons `Read` 34 · `PowerShell` 21 · `Bash` 19;
Toolathlon `browser_snapshot_navigate_to_next_span` 1,031 ·
`bigquery_run_query` 749 · `list_directory` 725; TRAIL `find_on_page_ctrl_f` 21 ·
`visit_page` 5. No output text.

## 3. Coding

**3.1 Unit and order.** Every pair in `cc_trace_commons_28`, `cc_mimo_120` and
`trail_gaia`, plus `toolathlon_sample`: **218 pairs**. Coded in one order
shuffled by `random.Random(20261014)`. The sheet shows, per pair: tool name,
normalised input, and a unified diff of origin vs candidate output with three
lines of context. Full outputs are available on request per pair, and each
request is logged.

**3.2 The question.** *If the agent had been handed the origin's output instead
of making the second call, would it have been missing anything the second
output told it?*

| code | meaning |
|---|---|
| **SAME** | Nothing missing. The differences are confined to values that change on every call and carry no task information: timestamps, durations, request/job/trace ids, temp names, ordering of an unordered listing, whitespace, ANSI codes. |
| **CHANGED** | Something missing. The second output reports a different state: file contents, directory entries, query rows, page or chunk, process result, or any value the agent could act on. |
| **ERROR** | Exactly one side is an error, or the two error messages differ in substance. Counted as not-SAME. |
| **UNDECIDABLE** | The diff cannot be judged: truncation hides the relevant part, or whether the differing value matters to the task cannot be determined. |

Tie rule: a pair with **both** a volatile difference and a substantive one is
CHANGED. A coder unsure between SAME and CHANGED codes UNDECIDABLE, not either
side. UNDECIDABLE is reported separately (§4.2), never folded.

**3.3 Blinding, stated honestly.** One coder (the engine session). The coder
cannot be blind to the corpus because tool names reveal it, and is not blind to
the tool-name distribution in §2.2. The coder has not read any output in the
frame. The mechanical ladder in §5 is computed **after** all 218 codes are
committed to a file whose sha256 is recorded in the results document.

## 4. Metrics

**4.1 Primary.** `F_cc = SAME / 92` over the two CC subsets combined, with a
Clopper–Pearson 95% two-sided interval. CC is primary because the 0.80% figure
and every per-trace dollar the product shows come from Claude Code traces.

**4.2 Bound.** `F_cc_upper = (SAME + UNDECIDABLE) / 92`, reported next to
`F_cc` every time. Also the number of tie-rule applications.

**4.3 Secondary, descriptive.**
- `F_toolathlon = SAME / 100` with interval, and the implied range over 9,059.
  This is an estimate, not a count, and is never written as one.
- `F_trail = SAME / 26`.
- Per-tool SAME counts for every tool with 5 or more pairs coded.
- `cc_trace_commons_28` alone: SAME out of 84. These are the pairs that would
  join the published 34 if the gate accepted them.

## 5. Mechanical ladder (descriptive, after coding)

| level | outputs considered equal when |
|---|---|
| L0 | sha256 equal (the shipped gate; 0 of the frame by construction) |
| L1 | equal after collapsing whitespace and stripping ANSI escapes |
| L2 | L1, then masking ISO-8601 timestamps, UUIDs, hex runs of 8+ and digit runs |

Reported as a 2×2 against the codes (L2-equal × SAME) per subset. This tells a
later study what a candidate rule would catch. **It is not adopted here.**

## 6. Decision rule

| `F_cc` SAME count (of 92) | verdict | what follows |
|---|---|---|
| **≥ 19** (≈ 20%) | the gate materially under-reports on CC | a **separate** pre-registration for a relaxed tool rule; published figures stay until that one passes |
| **10 – 18** | reported, no action | — |
| **≤ 9** (< 10%) | the gate stands on CC | negative result published |

**Override:** if UNDECIDABLE is **10 or more** of 92, the verdict is **not
decidable**, whatever SAME is, and the result is published as that.

🔴 Any later relaxation moves published figures (34, 0.80%, 8,042, 4,249). That
is a product decision and is not made by this document.

## 7. Predictions

Written before any output in the frame was read.

| # | Prediction |
|---|---|
| **P1** | CC SAME between **3 and 15** of 92 |
| **P2** | Toolathlon sample SAME between **10 and 35** of 100 |
| **P3** | TRAIL gaia SAME at most **5** of 26 |
| **P4** | CC UNDECIDABLE at most **5** of 92 |
| **P5** | Of pairs that are L2-equal, at least **90%** are coded SAME |
| **P6** | CC `Read` pairs: SAME at most **3** of the 39 (34 trace-commons + 5 mimo) |

No direction of bias is declared. The last study's declared bias was the wrong
one (`TRAIL_REPEAT_RECALL_RESULTS` §3), so declaring one here would only look
like protection.

## 8. Stop conditions

- A frame hash mismatches (§2.1): stop. The run is invalid.
- A key in the frame cannot be found in its trace: stop and report the count.
  Do not code a substitute.
- The coding file is changed after the §5 ladder is computed: the results must
  say so, and say which codes changed.

Cost: zero. No judge, no API key, no network.
