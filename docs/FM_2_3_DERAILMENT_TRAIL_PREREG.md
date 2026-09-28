# FM-2.3 on a corpus chosen for failures: did the agent drift off the task?

Rule 8: merged before any code or any judge call. Nothing here is implemented.

FM-2.3, verbatim from arXiv 2503.13657 v1 (read 2026-09-03):

> **Task derailment** — "Deviation from the intended objective or focus of a
> given task, potentially resulting in irrelevant or unproductive actions."
> [FC2. Inter-Agent Misalignment]

---

## 0. Why this axis, and why the corpus changed first

`FM_1_1_TURN_ADHERENCE_RESULTS.md` §5 examined three axes on 2026-09-03, found
all three blocked, and separated the reasons. Of the three it named exactly one
as a data shortage:

> | FM-2.3 task derailment | 1 candidate in 40 | **yes**, of a kind: short
> single-task sessions leave nothing to derail from |

and prescribed the route:

> The next attempt should start from a corpus **selected for containing
> failures**, not from one selected for being available. […] That is a separate
> pre-registration and is not started here.

This is that pre-registration. The axis is unchanged; the corpus is the thing
being changed, and it is changed because the previous document said the block
was the corpus and not the axis.

Four axes have been killed on our own sessions (re-read, args-only,
`unverified_edit`, FM-2.2) and two more set aside (FM-1.1, FM-1.5). Five of
those six stopped at a missing positive class rather than at a bad rule. Trying
a seventh on the same sessions is the measurement this project has already run.

---

## 1. Measured before deciding (2026-09-28)

### 1.1 The corpus

`PatronusAI/TRAIL`, revision `b424ce63d5973d5dcd7169b1bc3c07ccdee276d1`.

| | |
|---|---|
| traces | **148** (gaia 117 · swe_bench 31) |
| human-annotated errors | **841** |
| traces with zero errors | **4** |
| licence | **MIT**, with a gate: *"you agree to not reshare this dataset outside of a gated or private repository on the HF hub"* |

🔴 The no-resharing condition binds distribution, not measurement. Extracted
traces stay outside this repository. Figures derived from it may be published;
the traces themselves may not be redistributed.

⚠️ The revision above is a local snapshot and has **not** been compared against
the live dataset. A stale cache has answered "no data" in this repository
before, so the revision is named here and any run must print it.

### 1.2 What the labels are

Each error carries `category`, `location` (a span id), `evidence` (a verbatim
quote), `description`, and `impact` (HIGH / MEDIUM / LOW).

**These are human annotations.** That is the difference from `mcemri/MAST-Data`,
whose own README says its labels come from an LLM judge and which was therefore
used only for stratified sampling. TRAIL's labels can be argued with as labels.
They are still **not our question** — see §3.

🔴 The vocabulary is not closed. `Goal Deviation` and `Goal deviation` both
occur, as do three spellings of another category. The normalisation rule is
frozen in §2 before any count is used.

### 1.3 The target, counted

Under the §2 normalisation, at trace level:

| category | traces | base rate |
|---|---:|---:|
| instruction non-compliance | 78 | 0.5270 |
| formatting errors | 73 | 0.4932 |
| **goal deviation** | **64** | **0.4324** |
| language-only | 50 | 0.3378 |
| resource abuse | 42 | 0.2838 |

Goal deviation by impact, at trace level: **64** traces have any, **62** have at
least one HIGH or MEDIUM. Across its 65 error instances: HIGH 58, MEDIUM 5,
LOW 2.

Two facts follow and both are reasons this axis was chosen over
instruction non-compliance, which has the larger population:

1. **The impact threshold barely moves it** (64 → 62). For instruction
   non-compliance the same choice moves 78 → 51, a 35% swing on a knob, and a
   knob that size invites being turned after the result is seen.
2. **The annotators treated it as consequential** — 58 of 65 instances are
   HIGH.

### 1.4 The view side

Until `boxdawn/boxdawn#228` (merged 2026-09-28, `a5c5c4b`) the judge's view of a
TRAIL trace was empty for 18 of 20 traces, because `llm_calls[].input_text`
arrives wrapped as `{"messages": [...]}` and the readers required a bare list.

After it: 20 of 20 carry content. Measured on those 20 — user texts 126,
assistant texts 170, view size min 9,033 / median 19,387 / max 106,888
characters, none over the frozen 120,000 cap.

🔴 **This pre-registration is void if that merge is reverted.** The measurement
it describes cannot run on an empty view, and an empty view does not announce
itself.

---

## 2. Frozen definitions

**Unit: the trace.** TRAIL localises each error to a span, and our judge answers
about a session. Aggregating up is the lossy direction but it is the one that
matches what ships. A trace is a TRAIL-positive for a category when it carries
**at least one** error of that category, at **any** impact.

**Normalisation:** casefold, then remove whitespace and hyphens. `Goal
Deviation`, `Goal deviation` and `goal-deviation` become one key. Nothing
smarter: deciding that two differently-named categories are the same one is a
judgement, and it would belong in this text where it can be argued with, not
inside a helper.

**Sample: 40 traces**, drawn from all 148 with a fixed seed, stratified by split
in proportion to the corpus (gaia 32, swe_bench 8). **Not** drawn on the label,
and **not** the longest or the most eventful. The rule that killed three
detectors is the one being kept: the sample must be able to come back empty.

**Model, prompt shape, view builder, and the 120,000-character cap are the
shipped ones and are not tuned here.**

---

## 3. 🔴 The mapping is a claim, not a fact

Nothing establishes that TRAIL's `Goal Deviation` is MAST's FM-2.3. The names
are close and the definitions read compatibly. That is all.

So the design does not assume it. **I hand-label the 40 on our own question,
blind to TRAIL's labels**, and the comparison to TRAIL happens afterwards as an
observation (P7) rather than as a source of truth. If the two disagree badly,
that is a finding about the mapping and it is reported as one — it does not
retroactively change what was labelled.

This ordering is the whole reason the axis can be measured on somebody else's
corpus without inheriting somebody else's taxonomy.

---

## 4. Validity threats, stated before the result

**4.1 The base rate is the trap that took FM-2.2.** There, P1 cleared 0.80
while a labeller answering NEG to everything would have scored the same. Here
the TRAIL base rate is 0.4324, so a constant answer scores about 0.57 — but
the floor that matters is **my draft's own class balance**, which is not known
until the 40 are labelled. P1 is therefore written in §6 as a **margin over the
constant-answer score on the same sheet**, not as a bare threshold.

**4.2 Length confound.** The 2026-09-03 dry-run flagged sessions whose requests
were 2–2.7× the median length. If derailment findings here concentrate in the
longest traces, "drifted" and "had room to drift" are the same string. §6 P8
reports the length distribution of flagged versus unflagged and it is read
before the precision number is believed.

**4.3 The `user` role is a harness, not a person.** TRAIL's user turns are
scaffold text (*"Below I will present you a task…"*). For this axis that is
workable — the objective to deviate from is stated in it — but **no output from
this work may describe those turns as a person's request.** HAL was rejected for
FM-2.2 on exactly this distinction.

**4.4 Goal deviation is nearly a GAIA-only phenomenon.** Counted per split:
**gaia 62 of 117 (0.5299)**, **swe_bench 2 of 31 (0.0645)** — an eightfold gap
in rate. A proportional sample therefore carries roughly **one** swe_bench
positive, and this measurement cannot say whether the axis generalises beyond
web-research agents. Stated now so the result is not read wider than it is.

An alternative design would oversample swe_bench to answer the generalisation
question. It is rejected here: with 2 positives in that split there is nothing
to oversample, and drawing on the label is the trap §2 exists to avoid.

**4.5 Our own sessions are not this corpus.** GAIA and SWE-bench agents are not
Claude Code. A precision measured here does not transfer to shipped traces, and
shipping is a separate decision with its own gate.

---

## 5. What is explicitly NOT changed

- No detector is added, removed, or rewired. No default flips.
- The shipped axes (FM-1.3, FM-3.2) are untouched.
- No published figure is restated. The waste-rate metric is not involved.
- The judge model stays frozen at the shipped one; no prompt search, no
  threshold search, no F1 grid.
- TRAIL traces are not committed to this repository.

---

## 6. Predictions (written before any labelling and before any judge call)

| # | prediction | if it misses |
|---|---|---|
| **P1** | my draft labels and the blind set agree on **≥ 0.80**, **and** that agreement exceeds the score a constant answer would get on the same sheet by **≥ 0.10** | relabel is not permitted; the disagreement is reported and the axis stops |
| **P2** | 🔴 **≥ 8 of the 40** hand-labelled positive | below 8: **stop. No judge call.** The axis is unmeasurable on this corpus even with a perfect judge |
| **P3** | judge precision **≥ 0.70** on the hand labels | the rule is reported as killed, as re-read, args-only and `unverified_edit` were |
| **P4** | judge recall **≥ 0.60** | reported; a low-recall high-precision result is a narrower claim, not a failure |
| **P5** | **0** findings whose quoted evidence is absent from the view | any hallucinated evidence voids P3 for that run |
| **P6** | parse failures **≤ 2 of 40** | reported with the cost, as in the FM-3.2 run |
| **P7** | *observation, not a gate* — agreement between my hand labels and TRAIL's `goal deviation` label | reported either way; disagreement is a finding about §3's mapping |
| **P8** | *observation, not a gate* — median view length of flagged vs unflagged traces | a large gap is read as §4.2 and weakens P3 |

P2 exists because `FM_1_1_TURN_ADHERENCE_PREREG.md` did not have it. That run
reached the labelling stage, produced **0 positives in 40**, and its six
predictions would have accepted both a judge that flagged nothing and a judge
that flagged everything. The floor is 8 for the same reason FM-2.2 used 8.

**Expected before running, so the dry-run can contradict it:** a proportional
draw of 40 (gaia 32, swe_bench 8) against TRAIL's own labels is expected to
carry **about 17** goal-deviation positives — gaia 32 × 0.5299 ≈ 17.0,
swe_bench 8 × 0.0645 ≈ 0.5. P2's floor of 8 is therefore expected to pass with
margin, and P2 is a floor against my own hand labels rather than against
TRAIL's, so the margin is not a guarantee. **If the dry-run returns a
materially smaller number, the sampling frame is wrong and is fixed before
labelling, not after.**

---

## 7. What would make this fail, and what each failure means

- **P2 misses** → the corpus swap did not work either, and the honest reading
  is that trace corpora with human failure labels do not carry this axis at a
  measurable rate. That is publishable and it is the end of the axis, not the
  start of a search for a looser candidate rule.
- **P3 misses** → the judge cannot tell derailment from length or from
  difficulty. Report it beside the three rules already killed at this gate.
- **P1 misses** → the question is not crisp enough for two people to answer the
  same way, which is a defect in the question, not in either labeller.
- **P7 disagrees strongly while P1 and P3 pass** → our axis is measurable but is
  not TRAIL's category. The mapping claim in §3 is withdrawn and the result is
  reported under our own definition only.

---

## 8. Order of work

1. Merge this document. Nothing below starts before that.
2. Draw the 40 with the fixed seed; record the seed and the trace ids.
3. **Dry-run the counts only** — how many of the 40 are TRAIL-positive, and the
   length distribution. No judge, no cost. Compare against §6's expected 17.
4. I hand-label the 40 on our question, blind to TRAIL's labels.
5. Score P2. **If it misses, stop here and write the negative result.**
6. Blind set: 15 of the 40 to the second labeller; score P1.
7. Only then, judge the 40. Score P3–P6. Report P7 and P8 alongside.

🔴 A billing guard is set before step 7 and the run's cost is recorded. A dead
key scores like a perfect result and its only signal is a cost of zero.

---

## 9. Cost, for planning rather than as a claim

From the 20 measured views: mean 30,274 characters ≈ 8,600 input tokens. At the
shipped model's published rates (input $1.00/Mtok, output $5.00/Mtok) and one
call per trace, 40 traces is roughly **$0.40**, a few minutes of wall time.

That is about twice the FM-3.2 run's $0.1815 for the same count, because TRAIL
views are larger than Claude Code sessions. It is a planning figure. The
recorded cost of the actual run is the number that gets reported.

---

## 10. Provenance

Counts in §1.3 come from `_trail_target_census.py`; view sizes in §1.4 from
`_trail_judge_view_probe.py`; the wrapper measurement from
`_trail_view_shape_probe.py`. All three are uncommitted diagnostics under
`field_test/diagnostics/`, per the rule that raw probes stay out of the
repository while the documents that cite them do not.

---

## 11. Amendment (2026-09-28): what the dry-run moved, before any labelling

§8 step 3 ran. No judge was called and no cost was incurred. Seed **23**, quota
as written (gaia 32, swe_bench 8), drawn on the trace index before any label was
read. Raw: `_fm23_draw40.RESULTS.json`.

### 11.1 The expectation held

**21 of the 40 are TRAIL-positive** against §6's stated expectation of about 17
(gaia 20 of 32, swe_bench 1 of 8). For n=40 at the corpus rate the standard
deviation is about 3.1, so 21 sits near one deviation above and is not a
material departure. **The sampling frame is not changed.**

Recording the direction matters: the number came back *larger* than predicted.
§8 step 3 only authorised fixing the frame if it came back materially smaller,
and it did not, so nothing is touched.

### 11.2 🔴 The frame is 39, not 40 — one trace does not ingest

`swe_bench_011` fails with `duplicate span_id: b14646a5fcac02fd`. This install
cannot read it, so it cannot be judged and it is not hand-labelled.

- It is **TRAIL-negative**, so the positive class is not reduced by its loss.
- **P2's floor stays at 8.** It is an absolute count of positives, not a rate,
  and 8 of 39 is the same evidential bar as 8 of 40.
- P3/P4 are scored over the 39 that ingest. The denominator is written here so
  it is not quietly chosen later.

The failure is recorded rather than routed around. A corpus that silently loses
rows to a parser reports a smaller positive class than it has, and that is the
direction that kills an axis by accident.

### 11.3 🔴 Three views exceed the cap and will be truncated

§1.4 said none of the measured views passed the frozen 120,000-character cap.
That was true of the 20 traces measured then and is **false at 40**:

| trace | view chars | TRAIL-positive |
|---|---:|---|
| `gaia_037` | 234,928 | **yes** |
| `gaia_048` | 306,539 | no |
| `gaia_080` | 249,099 | no |

The cap is applied in `verification_prompts.py:61`, at prompt assembly, not in
`render_trace_for_judge`. So the judge sees the first 120,000 characters plus a
truncation notice — **which is exactly what ships**, and the three stay in.

Removing them would measure a judge that does not exist. But a derailment whose
evidence sits past the cut cannot be found, so:

**P9 (observation, not a gate):** report the judge's verdict on those three
separately, and whether any hand-labelled positive among them has its evidence
beyond the cut. If it does, P4's recall is read as a floor rather than an
estimate.

### 11.4 The length confound runs the other way

§4.2 was written against the risk that flagged traces are simply the longest.
On TRAIL's own labels the opposite holds: **positive median 17,801 characters,
negative median 28,926 — negatives are 1.62× longer.**

This does not retire §4.2, which is about *our judge's* flags and cannot be
scored until the judge runs. It does mean a judge that flags long traces would
score *against* the labels here, so length-chasing is not a way to pass by
accident on this corpus. P8 is still reported.

### 11.5 Cost revised

With truncation applied, the 39 sum to roughly 424,000 input tokens: about
**$0.48** at the shipped rates, against §9's $0.40 planning figure. §9 said the
recorded cost of the actual run is the number that gets reported; this is still
a planning figure.

### What is explicitly NOT changed

Predictions P1–P8 stand as written, including P2's floor of 8 and P1's margin
requirement. The target category, the normalisation rule, the unit, the seed,
the model and the prompt are untouched. No hand label has been made yet.

---

## 12. Amendment (2026-09-28): the draw was re-run, and it did not move

§8 step 4 stopped before the first label. Building the sheet showed **30 of the
39 traces with no tool calls at all**, and the raw data said only 2 of them
were genuinely tool-less: the adapter dropped every OpenInference span without
`output.value`, which for this sample was **80 of 159 TOOL spans**, all of them
carrying `input.value`.

That is fixed in `boxdawn/boxdawn#231` (merged, `87514b2`): a TOOL span with no
recorded result is kept and marked `output_is_absent`; CHAIN and LLM spans are
still skipped. The reason it had to be fixed before labelling rather than noted
beside the result: **TRAIL's annotators labelled from the complete trace.** With
half the actions invisible, a disagreement between their labels and ours could
not be read — "our judgement differs" and "we could not see it" produce the
same number.

### 12.1 The draw was re-run on the same seed, and the frame did not move

| | before `#231` | after |
|---|---:|---:|
| drawn | 40 | **40** (identical trace ids) |
| ingest failures | 1 (`swe_bench_011`) | **1, the same one** |
| TRAIL-positive | 21 | **21, the same traces** |
| views over the 120,000 cap | 3 | **3, the same three** |

**§11 stands as written.** P2's floor, the 39-trace denominator, the three
truncated traces named in §11.3, and the cost figure in §11.5 are all unchanged.

🔴 This contradicts what was said when the fix was proposed — that restoring 80
tool calls would grow the views and push more of them past the cap. It did not.
The restored spans carry short inputs (median 70 characters, 17,428 across the
whole sample), so the views grew by a few hundred characters each. Recorded
because the prediction was made out loud and was wrong.

### 12.2 What did move is the only thing that mattered

| | before | after |
|---|---:|---:|
| tool spans in the sample | 79 | **159** |
| traces with any visible action | **9 of 39** | **38 of 39** |

The one remaining trace has no tool calls in the raw data either.

§11.4's direction also holds: positive median 17,953 characters against
negative 30,198, so TRAIL-positive traces remain the shorter ones.

### What is explicitly NOT changed

P1–P9 stand. Target category, normalisation, unit, seed, sample, model and
prompt are untouched. **No hand label has been made.**
