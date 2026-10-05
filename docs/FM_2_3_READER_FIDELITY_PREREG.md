# FM-2.3 reader fidelity: is the 19 a property of the line, or of the reader?

Pre-registration. Written before any call is made. Follows
`FM_2_3_DEFINITION_AB_RESULTS.md`, whose Q1 produced the question this answers.

**One question.** The definition A/B's arm A handed the labeller's own written line
(§13.2) to a fixed reader and got **19 positives of 39**, where the labeller who wrote
that line had labelled the same 39 at **0–1**. Two readings of that gap are currently
tangled:

- **(i) the reader.** `claude-haiku-4-5` cannot apply an exclusion-laden definition.
  The evidence field supports this: **10 of the 19** arm-A positives rest on
  categories §13.2 explicitly excludes.
- **(ii) the line.** The written sentence genuinely does not encode the standard its
  author applied.

Only (ii) is a finding about the project. This run tests whether (i) accounts for the
19, by holding the prompt fixed and changing the reader.

🔴 **This is not a substitute for the third labeller.** Whichever way it lands, the
human form of reading (b) stays open and §14's seed-59 sheet stays available. What
this run can do is tell us whether the 19 is worth citing at all.

---

## 1. What is held identical, and what is deliberately not

**Byte-identical to the definition A/B's arm A:** the system-prompt scaffold, the
§13.2 definition string, the question stem, the output shape, the view builder
(`render_trace_for_judge`), the tool-output cap (2,000), the view cap (120,000) with
the shipped truncation notice, and the sample (the same 39, `swe_bench_011` excluded).
The runner re-reads the definition out of
`FM_2_3_DERAILMENT_TRAIL_PREREG.md` and refuses to run if it has drifted.

**Deliberately different: the reader.** Two things change together on the test arm —
the model and its native thinking configuration — and that is the manipulated
variable, not a confound to be removed. The question is whether *a competent reader*
applies the exclusions, not whether a specific parameter does. §4 states what that
costs us.

### 1.1 The arms

| arm | model | thinking | `max_tokens` | role |
|---|---|---|---:|---|
| **A** | `claude-haiku-4-5` | none | 256 | **already run.** N_A = 19. No new calls |
| **R0** | `claude-haiku-4-5` | none | 8,192 | isolates the `max_tokens` change alone |
| **R1** | `claude-opus-5-5` | adaptive (native default) | 8,192 | 🔴 **the test** |
| **R2** | `claude-fable-5-1` | adaptive (always on) | 8,192 | **conditional** — fires only on the trigger in §2.3 |

Model ids verified against `GET /v1/models` on 2026-10-05.

**Why `max_tokens` moves at all.** At 256 the evidence strings were cut mid-sentence
and arm B missed Q4 with 3 parse failures. A reader whose JSON is truncated before its
closing brace is not being tested on its reading. 8,192 is chosen to hold adaptive
thinking plus a short JSON object; it is not tuned to a count, and **R0 exists so the
change is measured rather than assumed harmless.**

**Baseline.** R1 is read against **R0**, not against arm A's 19 — same model, same
cap, one variable between them.
🔴 **Amended 2026-10-05 — see §8.4.** Both arms moved to the Batch API, so the baseline
is **R0-batch**; the synchronous R0 becomes an endpoint control (Q0b). Arm A vs R0 is reported separately as the `max_tokens`
effect. Two single-variable comparisons rather than one confounded one.

**No prompt tuning.** The prompt is the one already written and run; it is not revised
here, and will not be revised after a count is seen.

**Nothing from this run ships.** No `src/` change is authorised by this document.

---

## 2. Predictions, with thresholds fixed now

Let **N_R0**, **N_R1**, **N_R2** be positives out of 39.

### 2.1 Q0 — the `max_tokens` control

| | |
|---|---|
| **prediction** | `|N_R0 − 19| ≤ 5` (i.e. 14–24) |
| **if it misses** | the cap alone moved the count by more than the model is being asked to move it. Reported as the finding, and Q1 is read against N_R0 only — arm A's 19 is then not comparable to anything in this run |

### 2.2 Q1 — the test

| N_R1 | reading |
|---|---|
| **≤ 4** | **(i) accounts for the 19.** A competent reader does reproduce the labels from the written line. The "written line ≠ labeller's standard" reading is **weakened**, and arm A's 19 must not be cited as evidence about the line |
| **≥ 10** | **(i) does not account for it.** The written line diverges from its author's labels under a strong reader too. Reading (ii) is **supported** |
| **5–9** | **inconclusive.** Same dead band and same reason as §15.3 of the parent prereg: forcing a call across a single-case boundary is false precision |

🔴 **No expectation is stated for N_R1.** The arm under test does not get a prior from
this document. N_R0's expectation exists precisely because it is the arm that can
falsify the setup.

### 2.3 Q2 — the conditional second reader

**R2 fires if and only if `N_R1 ≥ 5`.** The trigger is fixed here, before any call, so
it is a sequential design rather than a knob: if R1 already lands ≤ 4 the question is
answered and the money is not spent.

| N_R2 | reading |
|---|---|
| **≤ 4** | the strongest available reader applies the exclusions. R1's count is a property of R1, and (i) still accounts for arm A |
| **≥ 10** | **two independent strong readers both diverge from the labeller.** The strongest evidence this instrument can produce for (ii) |
| **5–9** | inconclusive, and the run stops there |

### 2.4 Q3 — hallucinated evidence

**0 findings per arm whose quoted evidence is absent from the view.** Any arm with a
genuine absent quote is voided.

🔴 **Checked by the corrected method, and only by it.** The definition A/B's first
three attempts at this check returned 68 of 68, then 74 of 193, then 19 of 141
"absent", all three wrong for different reasons; the fourth — fragment extraction with
word-boundary guards on the single-quote form, then **hand-reading every candidate** —
returned 0. The instrument is `field_test/diagnostics/_fm23_definition_ab_q3.py`, and
every candidate it flags is read by hand before any arm is called voided. A mechanical
count is not a Q3 result.

### 2.5 Q4 — parse failures

**≤ 2 of 39 per arm.** Reported with the cost. Arm B of the definition A/B missed this
at 3; the raised cap is expected to remove the cause, and that expectation is on the
record here so the run can contradict it.

### 2.6 Q5 — mechanism, descriptive and not a gate

Of each arm's positives, how many rest on a category §13.2 excludes (a wrong answer, a
fabricated answer, a skipped verification, a tool error, a format violation). Frozen
pattern, so the count is mechanical:

```
fabricat | without (any )?(actual )?(verif|evidence|research|search)
| never (actually )?(search|retriev|obtain|verif) | skipped verif
| made.up | hallucin | no evidentiary
```

🔴 **This pattern was written on 2026-10-05 *after* reading arm A's evidence strings,
where it matched 10 of 19.** It is therefore a descriptive instrument carried forward,
not a confirmatory one, and it is frozen here so that at least it cannot be retuned
against R1's output. No threshold attaches to it.

---

## 3. 🔴 Billing guard

- **Exact call budget: 78** (R0 + R1) if R2 does not fire, **117** if it does. The
  runner **aborts above 125**.
  🔴 **Re-baselined 2026-10-05 — see §8.2.** A credit outage consumed 31 calls that were
  rejected before inference and billed $0.00; the abort moves to **above 175** with the
  arithmetic shown there. The $12.00 ceiling and the $0.50 per-request ceiling do not move.
- **Spend ceiling $12.00.** The runner aborts on crossing it.
- **Per-call abort at $0.50.** Adaptive thinking on a 120,000-character view has no
  published worst case for this corpus; a single call that expensive is a runaway, not
  a measurement.
- 🔴 **Before any count is read**, assert **aggregate cost > 0** *and* **per-arm cost >
  0** *and* **per-call cost > 0 for at least 37 of 39 calls in each arm.**
- The **recorded** cost is reported, not the planning figure.

**Planning figure.** Arm A recorded **404,464 input tokens** across its 39 views; the
views are identical here, so input is fixed and only output varies. At the rates
verified 2026-10-05 ($1/$5 haiku · $4/$20 Opus 5.5 · $10/$50 Fable 5.1), and allowing
50,000 output tokens per arm for thinking: R0 ≈ $0.65 · R1 ≈ $2.62 · R2 ≈ $6.54 ⇒
**about $3.3 for the two-arm case and $9.8 for all three.** A planning figure, nothing
more. The definition A/B's planning figure was 9% high.

🔴 `claude-opus-5-5` and `claude-fable-5-1` were priced wrongly by our own table until
`boxdawn/boxdawn#239` — the alias prefix resolved them to the previous release, 25%
high on Opus 5.5 tokens and 300% high on the Fable 5.1 cache-read line, with no
warning. **This run asserts the resolved rates against the figures above before
spending anything**, rather than trusting the table.

---

## 4. Validity threats, stated before the result

- 🔴 **R1 and R2 change model and thinking together.** If N_R1 lands ≤ 4 we will not
  know which of the two did it. That is accepted because the conclusion it licenses —
  *a competent reader reproduces the labels from this line* — does not depend on
  which. It would matter if we wanted to ship a reader; nothing here ships.
- 🔴 **Neither direction settles reading (b).** A reader that reproduces 0–1 shows the
  written line is readable as the labeller read it; it does not show that the
  labeller's line matches **MAST's** wording as a human would apply it. §14's sheet
  remains the only instrument for that, and this document does not touch it.
- **The reader is being graded against labels it cannot be independent of.** The 0–1
  is one person's. If those labels are themselves wrong, an arm that reproduces them
  scores well for the wrong reason. This run cannot detect that; the human sheet can.
- **Truncation is unchanged.** The same three views exceed the 120,000 cap
  (`gaia_037`, `gaia_048`, `gaia_080`; measured 2026-10-05 at 237,465 / 306,948 /
  250,781 characters). All arms understate by the same unknown amount, and `gaia_037`
  remains the one trace the §16 coding returned as a genuine redirection with only
  about half of it visible.
- **Order and state.** Calls are independent, no conversation carried between traces
  or arms. Arm order is R0, R1, then R2 if triggered, and is fixed for reproducibility.
- **A stronger reader is not a neutral reader.** A model with adaptive thinking may
  reason itself toward or away from the exclusions in ways a human applying the same
  sentence would not. Q5 is reported for exactly this reason, and it is descriptive.

---

## 5. What each outcome licenses

**N_R1 ≤ 4 (and R2 does not fire).** Arm A's 19 is withdrawn as evidence about the
line — in a documented amendment to `FM_2_3_DEFINITION_AB_RESULTS.md`, with this run
named. §2.2's Q1 "miss" there stands as recorded, but its *interpretation* narrows to
a statement about `claude-haiku-4-5`. 🔴 The published counts do not change, and §4 of
that document — which says the licensed narrowing is smaller than §5's sentence —
would then be **re-opened in the direction it closed**, because the objection it raised
rested on arm A's 19.

**N_R1 ≥ 10, or N_R2 ≥ 10.** Reading (ii) is supported: the written line does not
encode its author's standard. The licensed next step is **not** a relabel; it is to
state in the same amendment that the four axes stopped for want of a positive class
were stopped under lines whose written form has been shown, once, not to reproduce the
labels made under them. Re-examining those axes needs its own pre-registration and the
human sheet.

**Inconclusive, or Q0 misses.** Reported as such. Arm A's 19 stays as published, with
both readings (i) and (ii) explicitly open, and the human sheet becomes the only route.

**In every case:** P2 stands at 0–1 of 39. FM-2.3 ships nothing. §14's seed-59 sheet
is not withdrawn and the target category in §2 is unchanged.

---

## 6. Order of work

1. This document is committed and pushed **before the runner is modified**.
2. The runner is extended to take a model, a `max_tokens` and one arm — no new prompt
   is written, because the prompt is the one arm A already used.
3. The resolved rate for each arm's model is asserted against §3's figures **before
   any call**.
4. A dry-run on **2 traces of R1** (2 calls) checks the parse shape, the cost, and that
   thinking does not overrun the per-call abort. Its counts are **not** read.
5. R0, then R1. Costs recorded per arm.
6. The billing guard in §3 is checked **before** any count is looked at.
7. Q0 first, then Q1. R2 fires only if §2.3's trigger is met.
8. Q3 candidates are hand-read before any arm is called voided.
9. Results to `docs/FM_2_3_READER_FIDELITY_RESULTS.md`, and the amendment §5 licenses
   to `FM_2_3_DEFINITION_AB_RESULTS.md` in the same PR.

---

## 7. What is explicitly NOT changed

- **No `src/` change**, and the shipped verification axis is untouched.
- **P2 stands at 0–1 of 39**; the definition A/B's counts (N_A 19 · N_B 20 · N_C 29)
  are final and are not re-run.
- **§14's seed-59 sheet is not withdrawn**, and no outcome here replaces it.
- The target category, the unit, the sample, the view builder and the
  120,000-character cap are the shipped ones and are not tuned here.
- TRAIL's no-redistribution gate holds: no trace content is committed.

---

## 8. Amendment (2026-10-05): the run stopped on a credit outage, and resumes on the Batch API

Written **before any count from R1 has been read**, and that is the whole reason it can
be written at all. §2's thresholds are untouched; what changes is the call budget and
the endpoint.

### 8.1 What happened

R0 completed and its guard passed. R1 then failed §3's guard: **31 of its 39 calls
returned `400 invalid_request_error: "Your credit balance is too low to access the
Anthropic API."`** Per-call cost was non-zero for **8 of 39** against a floor of 37.

🔴 **R1's verdicts were not read and are not counted.** §3 exists for exactly this
case, and the eight that succeeded are the first eight in sorted id order — a prefix,
not a sample, so they are uninterpretable twice over. The attempt is preserved as
`field_test/diagnostics/_fm23_reader_fidelity.R1_VOID_credit_outage.json` because the
results document has to report the outage, and a re-run overwrites the arm's rows.

**R1 is re-run whole, not resumed.** A partial arm stitched to a later batch is not the
single-pass instrument §1.1 describes.

### 8.2 🔴 A defect in §3 that the outage exposed

§3 set an **exact budget of 78 calls (117 with R2) and an abort above 125**. 31 of the
calls that consumed that budget were **rejected before inference and billed $0.00.** The
abort was written as a runaway and overspend guard; it is now the only thing blocking a
re-run, while the control that actually protects money — the **$12.00 spend ceiling** —
stands at **$1.029316** and has never been close.

So the call cap is re-baselined with its arithmetic shown rather than reinterpreted:

| | calls |
|---|---:|
| billed so far (2 dry + 39 R0 + 8 R1) | 49 |
| planned: batch dry-run | 2 |
| planned: R0 batch + R1 batch | 78 |
| planned: R2 batch, if §2.3's trigger fires | 39 |
| **total** | **168** |
| **new abort** | **above 175** |

🔴 **The $12.00 spend ceiling does not move, and neither does the $0.50 per-request
ceiling.** The money guard is unchanged; only the proxy for a runaway loop is.

### 8.3 The endpoint changes to the Message Batches API

**Why:** 50% off both input and output. Measured from the fixed 404,464 input tokens
and R0's measured 7,416 output tokens, at the batch rates verified 2026-10-05
(haiku 4.5 $0.50/$2.50 · Opus 5.5 $2/$10 · Fable 5.1 $5/$25):

| arm | sync | **batch** |
|---|---:|---:|
| R0 | $0.442 | **$0.221** |
| R1 | $1.766 | **$0.883** |
| R2 | $4.415 | **$2.208** |
| all three | $6.62 | **$3.31** |

Worst single request, R2 in batch: **$0.163**, against the unchanged $0.50 ceiling.

**What the endpoint does not change.** Verified against the live documentation on
2026-10-05: *"the Message Batches API supports nearly all features available in the
Messages API… A small number of parameters (`stream`, `speed`, and `max_tokens: 0`) are
not supported"*, and **extended thinking is on the supported list**. So the model, the
prompt, the view, `max_tokens` 8,192 and adaptive thinking all carry over unchanged.

**What it does change, mechanically:**

- `stream` is dropped. It was there only to avoid an HTTP timeout on a large
  non-streaming request; a batch has no such request.
- Results come back **in any order** and are keyed by `custom_id`. Trace ids are used
  as `custom_id` (they satisfy `^[a-zA-Z0-9_-]{1,64}$`), and results are joined on that
  key, never on position.
- Cost is computed at the **batch** rate. `get_pricing` returns base rates, so the
  runner applies the 0.5 multiplier; the figure reported is the billed figure.
- A batch is capped at 100,000 requests or 256 MB. Ours is 39 requests and about
  1.6 MB. Most batches finish within an hour; one that has not finished in 24 hours
  expires, and an expiry is reported as a guard failure rather than as a result.

### 8.4 🔴 R0 is re-run in batch too, and this is required rather than extra

R1 is read against R0 (§1.1). Running R1 in batch while R0 stays synchronous would put
the endpoint between them, on top of the two differences §1.1 already names. So **R0 is
re-run in batch** at $0.221, and **R0-batch becomes the baseline Q1 is read against.**

The synchronous R0 is not discarded. It becomes a free control:

| | prediction | if it misses |
|---|---|---|
| **Q0b** endpoint | `|N_R0batch − N_R0sync| ≤ 5` | the endpoint moves the count, and that is reported as the finding; Q1 is then read against R0-batch alone |

Same band and same reason as Q0. For the record before the re-run: **N_R0sync = 21**,
and Q0 passed at `|21 − 19| = 2`. The move from arm A's 19 to 21 was accounted for
exactly — the two traces that were parse failures in arm A are the two that R0 calls
positive, and **no other verdict changed across the 37 that parsed in both**.

### 8.5 What is still not changed

- **§2's thresholds.** Q1 stays ≤ 4 / ≥ 10 / 5–9, Q2's trigger stays `N_R1 ≥ 5`, Q3
  stays 0 per arm hand-read, Q4 stays ≤ 2, Q5 stays descriptive. No count from R1 has
  been read, so none of these could have been steered.
- **The prompt.** Still imported from the arm-A runner rather than restated.
- **§4's validity threats**, with one added by this amendment: the batch endpoint is a
  fourth difference between arm A and R1, and Q0b is what measures it.
- **$12.00 spend ceiling · $0.50 per-request ceiling · cost asserted non-zero before
  any count is read.**
- No `src/` change. P2 stands at 0–1 of 39. §14's seed-59 sheet is not withdrawn.
