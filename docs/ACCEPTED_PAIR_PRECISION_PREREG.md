# Pre-registration — are the duplicates the cascade accepts avoidable?

Status: **pre-registration.** No outcome has been measured. The frame in §2 was
built on 2026-10-14 from pair keys and the shipped `enrich` categories. No
output text of any pair in it, and no tool call between its two calls, has been
read.

## 0. Why this exists

`BYTE_GATE_FALSE_REJECTION_RESULTS` asked what the byte-identity gate throws
away and found the answer is near zero on Claude Code. This asks the other half:
**of the pairs the gate accepts, how many were avoidable when the second call was
made?**

Two calls with byte-identical output are a duplicate in hindsight. They are
waste only if the agent had no reason, at the time, to expect a different
answer. An agent that edits a file and reads it back, polls a deployment, or
retries after fixing a cause is making a call that happened to return the same
bytes. It is not making a call it could have skipped.

What has been measured before: two Toolathlon `idempotent` sub-buckets,
`no_side_effect` and `payload_dependent`, each **30/30**
(`GREYZONE_EXPANSION_PREREG` §2.1). What has not been measured:
- the **4,249** non-`idempotent` Toolathlon pairs that README calls
  "provable-duplicate";
- any accepted pair on **Claude Code**, where the published 34 and **0.80%** come
  from (`GREYZONE_EXPANSION_PREREG` §4.2 holds a prediction only).

## 1. What is measured, and what is not

**Measured:** the share of accepted pairs whose second call was avoidable given
what the trace shows happened between the two calls.

🔴 **Not measured:**
- **Dollar or token waste.** This counts pairs, not cost.
- **The `idempotent` category on Toolathlon** (3,793 pairs). Two of its
  sub-buckets are already measured; the other two have their own open item.
- **Whether the agent "should" have known.** The coder judges from the trace's
  observable sequence: tool calls, their inputs and outputs, and elapsed time.
  The coder does not judge model reasoning.
- **Byte-differ pairs.** Those were the previous study.

## 2. The frame, frozen

Accepted pair = a tool pair from `find_repeat_candidates(trace, 2)` that passes
the absence and compact guards and is sha256-equal. Category comes from the
shipped `enrich` at `d3d7524`.

| corpus | accepted | reported by `enrich` | skipped (tool-error gate) | categories of the reported |
|---|---:|---:|---:|---|
| CC trace-commons 28 | **34** | 32 | 2 | unclassified 19 · idempotent 8 · side_effect 5 |
| CC mimo-cc-1k, seed-42 sample of 120 | 4 | 4 | 0 | idempotent 4 |
| Toolathlon | 8,042 | 8,042 | 0 | error_repeat 2,439 · side_effect 1,195 · unclassified 615 · idempotent 3,793 |

The Toolathlon non-`idempotent` total is **4,249**, which reproduces the README
figure exactly. The 34 is the published Claude Code count. `enrich` flags 4 of
the 32 reported trace-commons pairs as `modified_in_between`.

**2.1 Coding units**
- **CC: all 38** (32 reported + 2 skipped from trace-commons, 4 from mimo). The
  two skipped pairs are included because the published 34 includes them.
- **Toolathlon: 100** drawn by
  `random.Random(20261015).sample(sorted(headline_keys), 100)` from the 4,249.
  The draw gives error_repeat 57 · side_effect 29 · unclassified 14.

**2.2 Frozen by hash.** Key
`{corpus}|{trace}|{origin_span_id}|{candidate_span_id}|{category}|{between_window}`,
sorted, newline-joined, UTF-8. Keys are kept in the uncommitted
`_accepted_pair_census.KEYS.json`.

| subset | n | sha256 |
|---|---:|---|
| CC, all coding units | 38 | `ae8487783384539d65ac8d92ef317ac2dcdf6aeceb7dddd2fd34fdaa18b58cf4` |
| of which trace-commons reported | 32 | `e739941a6d31cb7fa1108975f47222dc8a899fa208afc3b87278d987ce01e5ba` |
| of which trace-commons skipped | 2 | `dda2a1fbc375672be85c55522e9226e97c45357a67ee4569872aa607fd9ee078` |
| of which mimo | 4 | `fb575549724d593ef34cb0c8174ace3a4e2a72a78dd889da8226e086e859d0a0` |
| Toolathlon headline (full) | 4,249 | `e28f80e632ea60f5556362983dddf67f900d096d7e36026fce034b381158d68a` |
| Toolathlon sample | 100 | `e8b58a0e86884b3c2ad8e49b7e858be6854987e927b560a1c0cec9d4a5977b20` |

## 3. Coding

**3.1 Sheet.** One entry per pair, in an order shuffled by
`random.Random(20261015)`. Each entry shows:
- tool name and input;
- the shared output, truncated to its first 800 characters;
- the elapsed time between the two calls;
- **every tool call between them** (`origin.end_time ≤ start < candidate.start_time`):
  tool name, input (first 200 characters) and output (first 200 characters).

**Category, `between_window` and `modified_in_between` are not shown.** Full
text is available per pair, and every request for it is logged.

**3.2 The question.** *When the second call was made, had anything happened
since the first that could have changed its result?*

| code | meaning |
|---|---|
| **WASTE** | Nothing visible between the calls could have changed the result. This includes repeating an identical failing call with no intervening attempt at the cause. |
| **JUSTIFIED** | Something between the calls could have changed the result: the agent wrote, edited, deleted, moved or created the same resource or a dependency of it; ran a command that could affect it; a user message intervened; or the call checks state that changes on its own (job, pod, deployment, queue), and time had passed. |
| **UNDECIDABLE** | The trace cannot settle it: whether an intervening action touches the resource is unclear, or the relevant span is truncated. |

**Tie rule.** If an intervening action could plausibly have changed the result,
the pair is JUSTIFIED even if the result did not change. A coder unsure between
WASTE and JUSTIFIED codes UNDECIDABLE. UNDECIDABLE is reported separately and
never folded into either side.

**3.3 Blinding, stated honestly.** One coder (the engine session). Categories
are hidden, but tool names largely reveal them. The coder has read none of
these pairs; the previous study's sheet was a different population (byte-differ).

## 4. Metrics

- **Primary:** `P_cc = WASTE / 38`, Clopper–Pearson 95% two-sided, with
  `P_cc_upper = (WASTE + UNDECIDABLE) / 38` always reported beside it.
  Also trace-commons alone (WASTE out of 34), because that is the published
  count.
- **Secondary:** `P_tl = WASTE / 100` with its interval, and per category
  (error_repeat / side_effect / unclassified) as descriptive counts. The implied
  number over 4,249 is an estimate and is never written as a count.

## 5. Decision rule (CC)

| WASTE of 38 | verdict | what follows |
|---|---|---|
| **≥ 27** (≥ 0.71) | the published CC count stands as waste | — |
| **19 – 26** | stands only with a qualifier | a proposed README wording change goes to a product decision |
| **≤ 18** (< 0.50) | the published CC count overstates avoidable waste | the revision is a product decision, not made here |

**Override:** UNDECIDABLE ≥ **8** of 38 ⇒ **not decidable**, published as that.
The same bands are applied to `P_tl` **descriptively**. No action on the
Toolathlon figure follows from this document.

🔴 No published figure is edited by this study. Any change to 34, 0.80%,
8,042 or 4,249 is a product decision taken after the results are public.

## 6. Predictions

Written before any pair in the frame was read.

| # | Prediction |
|---|---|
| **P1** | CC WASTE between **18 and 30** of 38 |
| **P2** | Toolathlon WASTE between **50 and 80** of 100 |
| **P3** | Of the 4 CC pairs `enrich` flags `modified_in_between`, at least **3** are coded JUSTIFIED |
| **P4** | Toolathlon `error_repeat` WASTE share is higher than `side_effect` WASTE share |
| **P5** | CC UNDECIDABLE at most **5** |

No direction of bias is declared, for the reason given in
`BYTE_GATE_FALSE_REJECTION_PREREG` §7. The last two studies missed in both
directions.

## 7. Stop conditions

- A frame hash mismatches: stop. The run is invalid.
- A key cannot be located in its trace: stop and report the count. Do not
  substitute.
- Codes are written to a file whose sha256 is recorded in the results **before**
  categories are joined back. A code changed after that join must be reported
  together with the reason.

Cost: zero. No judge, no API key, no network.
