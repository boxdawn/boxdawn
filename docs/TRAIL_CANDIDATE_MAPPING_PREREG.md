# Pre-registration — do TRAIL's two remaining candidate categories count what their names say?

Status: **pre-registration.** Written and merged before any `evidence` or
`description` string of either category was read. No judge call, no cost.

## 0. Why this document exists before an axis is chosen

Two TRAIL category names have been decoded on this snapshot, and **both counted
something other than their name**:

| TRAIL category | traces | what the human rationales actually counted | where |
|---|---:|---|---|
| `Goal Deviation` | 64 | failure to carry out the **agent's own plan**, not redirection away from the given task (F 20 / D 1 / O 0) | `FM_2_3_DERAILMENT_TRAIL_PREREG.md` §15 |
| `Instruction Non-compliance` | 78 | **output-volume rules** (73) and a planning tag (37) = 110 of 156; the task specification itself was **8 of 156**, T = **0.0513** against a `< 0.40` floor | `FM_1_1_TURN_ADHERENCE_PREREG.md` §9 → `FM_1_1_TURN_ADHERENCE_RESULTS.md` §10 |

Both of those studies cost nothing and took a day, and both killed a plan that
would have cost a hand-label campaign. The remaining candidates from the census
are `Resource Abuse` (42 traces) and `Context Handling Failure` (44 traces). This
document fixes the rule for reading **both** before either is opened, for the
same reason, and the axis is chosen **after** the result rather than before it.

🔴 **Both candidates are coded in one pass under this one rule.** They are not
independent: 3 `Resource Abuse` records sit on spans that also carry a
`Context Handling Failure` tag. Coding one category first would mean opening part
of the other category's span text before its rule was tested, so there is a
single committed rule and a single pass.

🔴 These two candidates are **not symmetric in what a pass would buy**:

- `Context Handling Failure` is adjacent to a **MAST-style judgement axis** — a
  pass extends coverage (shipped at 2 of 14, `project_mast_coverage_plan`).
- `Resource Abuse` is adjacent to **the axis this product already ships**: the
  four deterministic waste detectors (`repeat`, `context_resend`,
  `redundant_read`, `duplicate_creation`, per
  `src/clew/metrics/waste_rate.py:4-11`). A pass there would be the first
  **externally human-labelled** pool for the thing the public numbers are about.
  That is a different kind of value from a coverage bump, and §4 keeps the two
  decisions separate instead of ranking them here.

## 1. Structural facts, measured before this rule was written, with no rationale opened

Snapshot pinned at revision `b424ce63d5973d5dcd7169b1bc3c07ccdee276d1`, the same
one used by the two studies above. Normalisation as `FM_1_1` §9.1: case-folded,
whitespace-collapsed, a trailing `Errors?` dropped, a trailing plural on the last
word folded, `complience` → `compliance`.

| | `Resource Abuse` | `Context Handling Failure` |
|---|---:|---:|
| raw spellings folded in | `Resource Abuse` **57** (no variants) | `Context Handling Failures` **42** + `Context Handling Failure` **5** |
| **records (the coding unit)** | **57** | **47** |
| traces | 42 · base rate **0.2838** | 44 · base rate **0.2973** |
| gaia | 39 records / 29 traces = **0.2479** | 24 records / 21 traces = **0.1795** |
| swe_bench | 18 records / 13 traces = **0.4194** | 23 records / 23 traces = **0.7419** |
| traces carrying exactly one | 32 of 42 | 41 of 44 |
| records per positive trace | 1:32 · 2:6 · 3:3 · 4:1 | 1:41 · 2:3 |
| `impact` | MEDIUM **47** · HIGH **8** · LOW **2** | MEDIUM **31** · HIGH **16** · LOW **0** |
| `location` / `evidence` / `description` present | 57 / 57 / **56** | 47 / 47 / 47 |
| `evidence` chars, median / max | 190 / 5,998 | 206 / 3,358 |
| `description` chars, median / max | 190 / 658 (**1 empty**) | 189 / 654 |
| distinct spans | 57 (no two records share a span) | 46 (one span carries two) |
| same-**span** co-tags, top 3 | `formatting` 16 · `tool-related` 9 · `poor information retrieval` 9 | `instruction non-compliance` 10 · `formatting` 9 · `language-only` 7 |
| median labels per trace, positive / negative | **8 / 4** | **8 / 4** |

Excluded neighbour spellings, counted rather than silently dropped:
`resource not found` **7**, `resource exhaustion` **3**. Neither is folded into
`Resource Abuse` — sharing a word is not sharing a construct, and that is the
mistake this whole document exists to avoid. `Incorrect Memory Usage` (2) is
likewise **not** folded into `Context Handling Failure`.

Four facts follow, and each one changes how the result must be read:

🔴 **The split base rates differ by more than they did on any earlier candidate.**
`Context Handling Failure` is 0.7419 on swe_bench against 0.1795 on gaia — a
factor of **4.13**, on 31 traces against 117. `Instruction Non-compliance` was a
factor of 1.9 and §9.1 already refused to pool it. Every count in §4 is reported
per split and the two are **never summed into one rate**.

🔴 **Positive traces are the error-dense ones, and this is the opposite of the
earlier candidates.** For both candidates the median label count is **8 on
positive traces against 4 on the rest**; for `Instruction Non-compliance` it was
5 and 5. So a candidate record is more likely to sit inside a trace the labellers
found generally bad. Same-span co-tag counts are therefore reported per bucket in
the results, not only in aggregate.

**`Context Handling Failure` has no LOW-impact record at all**, and 16 of 47 are
HIGH (0.34) against 16 of 156 (0.10) for `Instruction Non-compliance`. The
thin-pool failure named in `FM_1_1` §9.6 — a mapping that passes but only on
low-impact wording slips — is structurally less available here. `Resource Abuse`
is the opposite: 47 of 57 are MEDIUM and only 8 are HIGH.

**One `Resource Abuse` record has an empty `description`.** It is coded from
`location` + `evidence` alone, is reported as its own line, and is **not**
dropped.

## 2. What has already been read, so the blinding is checkable

At the commit of this document, **no `evidence` or `description` string of either
candidate category has been displayed or read.** The two probes behind §1 emitted
counts, `impact` values, field presence and string *lengths*; `location` values
were used for span identity and their contents were not inspected. Probe scripts
are diagnostics and are not committed (`feedback_diagnostics_uncommitted`).

🔴 **Partial exposure exists and is measured, not asserted away.** Rationale text
*about the same span* was opened under a different tag in the two earlier
studies, and a co-located record can quote the same sentence:

| | records | on a span that also carries an already-read tag | strictly blind |
|---|---:|---:|---:|
| `Resource Abuse` | 57 | **5** (INC 3 · Goal Deviation 2) | 52 |
| `Context Handling Failure` | 47 | **12** (INC 10 · Goal Deviation 5) | 35 |
| total | 104 | **17** (0.163) | **87** |

(The tag counts exceed the record count because some spans carry both.)

The affected record ids are fixed in the blinding probe's output **before**
coding. The coding script flags each record with that bit, and §4 reports every
quantity **twice**: over all records, and over the 87 strictly blind ones. If the
two readings disagree by more than 0.10 on a primary quantity, the prior leaked
and the strictly-blind number is the one that counts.

🔴 **One prior is declared because it is not neutral for candidate A.** The
`Instruction Non-compliance` coding found **73 of 156** rationales describing the
agent printing far more than the guidance allowed. That is adjacent to
`Resource Abuse` by construct, and it is why §6 predicts the volume bucket to
dominate. The prediction is written down so that the prior is falsifiable instead
of invisible.

## 3. The coding rule, fixed before reading

Every one of the 104 records is coded into **exactly one** bucket of its own
category's scheme, from TRAIL's own `location` + `evidence` + `description`. Code
the span the `evidence` quote is about. Where a trace carries several records,
each is coded separately and traces are **not** summarised.

### 3.1 `Resource Abuse` (n = 57) — hypothesis: this is the waste axis we ship

- **D — repetition of a kind one of the four shipped detectors counts.** Sub-coded
  so the claim cannot be made at the wrong altitude:
  - **D1** the same tool or query invoked again on the same input (`repeat`)
  - **D2** the same message content sent again in a later model call (`context_resend`)
  - **D3** the same resource read again (`redundant_read`)
  - **D4** the same artifact created again (`duplicate_creation`)
- **V — volume without repetition.** More consumed in one go than the record's
  author thought warranted — over-long output, reading or printing far more than
  needed, more steps than necessary — with **no** repeat of the same content.
  🔴 **Nothing we ship counts this.**
- **E — the limit was external.** Rate limit, timeout, context window, quota,
  credits, disk: consumption the agent did not choose through redundant work.
- **X — another construct.** Wrong tool, wrong answer, slow progress, anything
  whose reason is not about consumption.
- **O — not decidable from the three fields.**

Primary quantity: **D = (D1+D2+D3+D4) / 57.** Secondary, named here and reported
separately rather than mixed in: **(D + V) / 57**, "waste as a broad construct".

### 3.2 `Context Handling Failure` (n = 47) — two rival hypotheses, both named now

- **R — context carried or sent again.** The reason is that the same context was
  re-sent, re-included, or kept when it no longer needed to be. This is what
  `find_context_resend` counts (`src/clew/detect/context_resend.py:321`).
- **L — context lost.** Information already present earlier in the trace was
  forgotten, dropped or ignored, and the agent acted without it. We ship nothing
  that counts this; it is the MAST-style axis candidate.
- **W — window or truncation.** The context window overflowed, was truncated, or
  the harness dropped history.
- **X — another construct.**
- **O — not decidable from the three fields.**

R and L are **mutually exclusive buckets**, so the two hypotheses cannot both
pass by counting the same record twice.

### 3.3 Tie-breaks, fixed now, and none of them can manufacture a pass

- `D | V` → **V** · `D | E` → **E** · `D | X` → **X**
  (lowers D; the secondary `(D + V)` contains both sides of the first tie and is
  unaffected by it, which is stated so the secondary is not read as a lower bound)
- `R | L` → **O.** Either resolution would favour one of the two hypotheses, so
  this tie is **not** absorbed into a bucket.
- `R | W` → **W** · `L | W` → **W** · any `| X` → **X** · any `| O` → **O**

🔴 **Every tie-break invocation is counted and reported.** This is the defect
`FM_1_1_TURN_ADHERENCE_RESULTS.md` §10.3 found after the fact: there, 82 of 156
records were decided by a tie-break that routed undecidability into a bucket, so
the `O ≥ 0.30` guard read `0.0000` and could not fire
(`feedback_guard_blind_to_absorbed_undecidability`). Here the guard is on
**`(O + tie-break invocations)`**, and the upper bound obtained by resolving
every tie toward the hypothesis is reported next to the point estimate.

### 3.4 The second instrument, committed in advance

`FM_1_1` §10.3 recorded what it should have read and deliberately did not: the
field that would have broken its ties. This document reads it up front. One extra
column per record, **counted separately and never folded into the bucket**:

- `Resource Abuse` — **BASIS**: who set the standard that was exceeded —
  `task` (the task prompt states a budget or limit) / `harness` (operating
  guidance states it) / `labeller` (neither states it; the record's author judged
  it excessive) / `unclear`.
- `Context Handling Failure` — **LOCUS**: which side the record is about —
  `input` (what was sent to the model) / `act` (what the agent did or failed to
  do with it) / `both` / `unclear`. `find_context_resend` lives on the `input`
  side only.

## 4. The decision, fixed before reading

n = 57 and n = 47, both coded in full. No sampling, so there is no draw and no
seed. Counts are reported per split, by `impact`, and over the strictly-blind
subset.

### 4.1 `Resource Abuse`

| D | what follows |
|---|---|
| **D ≥ 0.40 and D ≥ 23 records** | TRAIL's `Resource Abuse` is an external, human-labelled pool for the axis we already ship. Next step is **not** a judge study: it is a separate pre-registration asking whether our four detectors fire on those spans, with its own precision gate |
| **0.20 ≤ D < 0.40**, or D ≥ 0.40 with fewer than 23 records | mixed category. The D subset is usable only if it reaches **20 records**, and any claim must name the subset and its size — never the category |
| **D < 0.20** | the category counts something else. Published as a negative result, as FM-2.3's and FM-1.1's were |

Both conditions are required because a share without a pool is what
`FM_1_1` §10.4 ran into: a category can clear a ratio and still leave 7 usable
records against a gate of 30–40. 0.40 × 57 = 22.8, hence 23.

### 4.2 `Context Handling Failure`

| | what follows |
|---|---|
| **R ≥ 0.40** | the tag is an external pool for `context_resend` — the first human-labelled evidence bearing on a **shipped** detector. Next step is a detector-firing pre-registration, not a judge one |
| **L ≥ 0.40** | a real pool for a context-loss axis. Next step is an axis pre-registration, written before any labelling, and it must carry a name of its own rather than inheriting a MAST number by analogy |
| **both < 0.40** | the name counts something else. 🔴 **Third strike: the route "pick a TRAIL category by its name" is closed**, and §5 of the results names what replaces it |

A pass on R and a pass on L lead to **different** next steps and are reported
separately. If both clear 0.40 the larger is reported first and neither is
described as "the" construct behind the tag.

### 4.3 Guards

- **`(O + tie-breaks) ≥ 0.30`** on either category → the three fields do not carry
  enough to decide. Report that, publish the counts, and **do not force a
  verdict**. A check that fails almost everything is first evidence about the
  check (`feedback_check_that_fails_everything`).
- **Splits are never pooled.** If the splits disagree across a decision boundary,
  the usable pool is **the split that passes**, not the union. With
  `Context Handling Failure` at 0.7419 / 0.1795 this is the expected case, not a
  remote one.
- **Strictly-blind subset disagreeing by more than 0.10** on a primary quantity →
  the strictly-blind number is the one that counts, and the gap is reported.
- **The upper bound is reported with the point estimate** for every primary
  quantity: every tie resolved toward the hypothesis. A verdict is only stated
  when the point estimate and the upper bound fall on the same side of the
  boundary; otherwise the result is "undetermined with bound X".

## 5. What this cannot settle

- **Whether our detectors are right.** Coding reads what TRAIL's labellers wrote.
  A pass on D means the humans described the same *kind* of event; whether our
  code fires on those spans is the next pre-registration, and TRAIL's tool-span
  density is low — **159 tool spans over a 40-trace sample** after the `#231` fix
  (`FM_2_3_DERAILMENT_TRAIL_PREREG.md:404`) — which that study must size for.
- **Recall.** Waste or context loss the labellers did not tag is not bounded
  here, in either direction.
- **Whether TRAIL's labellers applied their own categories consistently.** The
  reading reports what they wrote, not whether they were right to write it.
- **Anything about our own corpus.** The public waste figures are measured on our
  traces; nothing here re-measures them, and a pass does not transfer a rate.
- **The MAST coverage count.** It stays at 2 of 14 until an axis study passes its
  own gate, not when a mapping passes.

## 6. Predictions, written before the first rationale is opened

### `Resource Abuse`

| | prediction |
|---|---|
| **D** (primary) | **0.15 – 0.35**, point **0.25** |
| **V** | **0.40 – 0.65**, point **0.50** |
| E | ≤ 0.15 |
| X | ≤ 0.10 |
| O | ≤ 0.10 |
| D in records, against the 23 needed | **predicted to fail** (point 0.25 × 57 ≈ 14) |
| D among the 8 HIGH-impact records | ≥ 2 |
| BASIS = `labeller` | ≥ 0.50 |
| which of D1–D4 leads | **D1 (`repeat`)**, and D2 (`context_resend`) ≤ 3 records |

### `Context Handling Failure`

| | prediction |
|---|---|
| **R** | **0.10 – 0.30**, point **0.20** |
| **L** (rival) | **0.40 – 0.65**, point **0.50** |
| W | 0.05 – 0.20 |
| X | ≤ 0.10 |
| O | ≤ 0.15 |
| LOCUS = `input` | ≤ 0.35 |
| swe_bench concentration | one recurring pattern covers ≥ **0.40** of the 23 swe_bench records, as `print_limit` covered 73 of 156 |

### Named in advance

🔴 **The prior is on candidate A's side.** Having read that 73 of 156
`Instruction Non-compliance` rationales were about printing too much, I expect V
to dominate `Resource Abuse`. If D instead clears 0.40, the prior was wrong in
the direction that *helps* us, and the result section says so in those words
rather than presenting it as a confirmation.

🔴 **A pass on D is the most consequential outcome in this document**, because it
touches the shipped product rather than the coverage count. It therefore gets the
strictest reading: the pool condition (23 records), the strictly-blind subset, and
the tie-resolved upper bound must *all* fall on the pass side before the words
"external human-labelled pool" are used anywhere, including in a message to
another session.

🔴 **Both failing is a real outcome and the plan for it is written now**, not
improvised afterwards: the TRAIL-category-name route is closed after three
strikes, and the next axis is chosen by reading rationales **first** across the
whole corpus (a construct census, cost 0) instead of by picking a name and
testing it. That is the opposite order from the last three attempts and it is
what their failures point at.

## 7. Order of work

1. This document, merged, before any rationale is read. (rule 8)
2. Read and code all **104** records in a diagnostic script (uncommitted): one
   bucket each, the second instrument's column, the tie-break flag, the
   strictly-blind flag.
3. A results document in `docs/`: raw counts per split, per `impact`, per
   strictly-blind subset; every tie-break counted; the upper bound next to each
   point estimate; and **every prediction in §6 scored, including the ones that
   fail**.
4. Only then, the next pre-registration — detector-firing, axis, or the construct
   census of §6's third note — chosen by what the result says.

**No judge call. No cost.** The corpus is on disk and the reading is local. TRAIL
traces and derived sheets are **not** committed: the diagnostics convention plus
TRAIL's own no-redistribution gate (`project_trail_corpus_reachable` §1).
