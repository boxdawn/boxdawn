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

---

## 13. Amendment (2026-10-01): P2 missed, and the reason it missed is not yet known

§8 step 4 ran. All 39 traces were hand-labelled blind, from
`_fm23_label_sheet.md` regenerated after `#231` so the restored tool spans were
visible. `_fm23_draw40.RESULTS.json` was not opened.

| | |
|---|---:|
| NEG | **38** |
| BORDERLINE | **1** (`gaia_002`) |
| POS | **0** |

**P2 = 0 of 39 strict, 1 of 39 counting BORDERLINE as positive. The floor is 8.
P2 misses, and it misses by a distance that no counting convention closes.**

Per §8 step 5 and §6 P2: **the judge was not called. The recorded cost of this
stage is zero.**

### 13.1 🔴 Why the negative result is not written yet

§7 reads a P2 miss as "trace corpora with human failure labels do not carry
this axis at a measurable rate". That sentence cannot be written from this
number alone, because §1.3 and §11.1 already recorded — before any labelling —
that **TRAIL's own `goal deviation` label marks 21 of the same 40**.

A 20-trace gap has two readings and this measurement does not separate them:

| | reading | what it would mean |
|---|---|---|
| **(a)** | the categories differ | TRAIL's `Goal Deviation` includes *answered without ever reaching the named source*; the labelling below excludes that as FM-3.x. Then §3's mapping claim is withdrawn and §7's last row applies |
| **(b)** | the labeller's line is narrower than the definition | the finding is about the labeller's reading of FM-2.3, not about the corpus |

Writing (a) while (b) is live is the failure this project has already had: the
block was our view twice on 2026-09-28, not the axis.

### 13.2 The labelling line that was actually used, stated because it is load-bearing

Frozen in writing after one trace had been read, and **not given to the second
labeller**:

> **Failing is not deviating.** A wrong answer, a fabricated answer, a skipped
> verification, a tool error or a format violation is not by itself a deviation
> — MAST counts those separately. POS requires the agent's *actions or output*
> to aim at something other than the stated objective.

Two consequences of that line, both recorded at the time:

- **the scaffold rule** — in this corpus a delegation to `search_agent` is
  silently degraded by the harness into a `print`. That alone was scored NEG:
  the agent's stated intent is on task, and scoring it POS would make the label
  describe the harness rather than the agent.
- **the aim rule** — actions aimed at the correct target that fail and end in a
  guess score NEG; actions aimed at a self-invented substitute score
  BORDERLINE or POS. `gaia_002` is the single BORDERLINE under this rule: it
  inserted "T. rex is the only dinosaur FA" as an unverified premise and sent
  all three of its requests at that premise.

### 13.3 🔴 A descriptive count that must not be substituted for P2

Under a looser reading — *submitted an answer without ever obtaining the
content of the source the question names* — **26 of 39** qualify. (The other 13:
five self-contained puzzles, `gaia_106`, and the seven swe_bench traces, all of
which obtained the repository.)

That 26 is the same order of magnitude as TRAIL's 21, which is what makes
reading (a) worth separating from (b).

**It is recorded as a description of the shape and is not a score.** P2 is
counted from the primary labels only. §1.3 named this exact move — a knob
turned after the result is seen — as a reason to prefer this category, and the
rule holds against its author.

### 13.4 The order of §8 is changed: P1 runs now

§8 put P1 (step 6) after P2 (step 5). **P1 is run first, out of order.**

The justification is that **P1 cannot change the positive count.** It measures
whether two people answer the same question the same way; it cannot move P2 off
0–1, and so it is not a route to rescuing the axis. It is the only measurement
that separates (a) from (b), and it costs no money.

Drawn 2026-10-01, seed declared before the draw: **seed 23** (the published
value from §11.1), stratified by split in proportion to the 39 — gaia 12,
swe_bench 3. Drawn on the sorted id list, **not on any label**; neither the
primary labels nor `_fm23_draw40.RESULTS.json` was read by the drawing script.

`gaia_001 003 013 037 045 048 053 056 063 099 106 114`,
`swe_bench_001 018 029`. Raw: `_fm23_blind15.json`.

### 13.5 🔴 P1's gate is arithmetically unreachable at this class balance

§6 writes P1 as *agreement ≥ 0.80 **and** ≥ 0.10 above the score a constant
answer would get on the same sheet*. Measured on the drawn 15:

| | |
|---|---:|
| primary labels on the 15 | **NEG 15 of 15** |
| best constant answer | **15/15 = 1.0000** |
| P1 therefore requires | **1.1000** |

**P1 as written cannot pass.** §4.1 built that margin to stop FM-2.2's base-rate
trap from recurring, and it does stop it — but it does not survive the case
where the first labeller's own labels are a single class. The margin is correct
and the sheet is degenerate.

So **P1 is not reported as a score for this run.** What is read from the 15 is
the raw disagreement count, and the two readings are fixed here, before the
second labeller sees the sheet:

| second labeller's 15 | reading |
|---|---|
| POS 0–2 | (a) — the question is answerable and this corpus does not carry it under our definition. §3's mapping to TRAIL's `Goal Deviation` is withdrawn and the negative result is written under our own definition only |
| POS 3+ | (b) — the line in §13.2 is narrower than FM-2.3. The finding is about the labelling, the 39 primary labels are reported as what they are, and a relabel is a new pre-registration rather than an edit to this one |

🔴 Either way **P2 stands at 0–1 of 39 and the judge is not called on this
corpus.** No threshold here is moved after the fact.

### 13.6 The blind sheet carries the reduced view, deliberately

`_fm23_blind15.md` collapses THE TASK to its code fences, keeping the agent
narration and the tool calls in full. The reason is not length: **the primary
labels were made from that same reduced view.** Handing the second labeller the
full harness template would give them more material than the first labeller
had, and a disagreement would then be unreadable — "we judged differently" and
"we read different things" produce the same number.

The sheet carries the question and a `?` option as a first-class answer (the
FM-2.2 precedent). It withholds three things by design: the primary labels, the
line in §13.2, and **the class balance of the primary labels** — a sheet that
says "mine were nearly all one class" anchors the second labeller toward that
class and costs the same independence the 15 exist to measure. For the same
reason the two readings in §13.5 live here rather than on the sheet: fixing them
before the sheet is handed over is what stops an interpretation from being
chosen after the count is known.

### What is explicitly NOT changed

- **No judge call. No cost.** P3–P6 are not run on this corpus.
- P2's result is final as measured; relabelling the 39 is not permitted here.
- Target category, normalisation, unit, seed, sample, model, prompt, and the
  120,000-character cap are untouched.
- The negative result document is not written until the 15 come back.

## 14. Amendment (2026-10-01): the blind sheet was opened before it was graded

`_fm23_blind15.md` was never graded. Its fifteen label slots were still empty
(`_____` x 15, file unmodified since it was written). Asked what the first
labeller's own judgement on those fifteen was, the first labeller stated the
leak and offered the alternatives; **the disclosure was requested and the
fifteen primary labels were handed over in full, with reasons.**

They are **NEG 15 of 15 — POS 0, BORDERLINE 0.** The single BORDERLINE
(`gaia_002`) was not in the draw, which is why §13.5's constant answer is
1.0000.

**This is a deviation from §13.4–13.6 and it is recorded as one.** The second
labeller can still fill the sheet in, but the number would no longer measure
what §13.5 reads from it: the count is now anchored on a disclosed answer, and a
disclosed answer and an independent one produce the same arithmetic.

Consequences, stated without softening:

- **§13.5's two readings cannot be applied to `_fm23_blind15.md`.** POS 0–2 from
  this sheet would not distinguish (a) from (b); it would distinguish nothing.
- **§13.4's out-of-order P1 run is void** on this sheet.
- The 20-trace gap between TRAIL's 21 and the primary labels' 0–1 is, as of this
  amendment, **unseparated**.

Nothing else moves. No judge was called, no money was spent, and the 39 primary
labels are untouched.

### 14.1 What the disclosed fifteen show about where the line is load-bearing

Two of the fifteen are the only ones on which §13.2's line did any work:

- **`gaia_037`** — 31 actions, of which **26** query `site:montereybayaquarium.org`
  directly and **5 leave the target** (an Invariant Labs GAIA trace explorer, a
  GitHub `benchmark_gaia.ipynb`). Scored NEG because the narration treats both
  as candidate pages that might carry the aquarium's figure and records "this is
  not the official site, it must be checked" — a bad search result followed, not
  a substitute objective adopted.
- **`gaia_048`** — 9 actions, of which **1** leaves the target (a HuggingFace
  dataset whose rows contain the question's own text, surfaced by the search)
  plus one wrong PDF. Both are single events with an immediate return to the
  thesis. Scored NEG as not a sustained shift of focus.

The other thirteen were NEG on the uncontested part of the line: twelve aimed
at the named source throughout and failed, and one was self-contained.

**This is where our reading and TRAIL's most plausibly diverge**, and it is
recorded here so that the replacement measurement is not read as if the
divergence point were unknown. It is still not a decision between (a) and (b):
a divergence point identified by the labeller whose line is in question is a
hypothesis about that line, not a test of it.

### 14.2 The replacement: a third labeller, a new seed, a fresh draw

The measurement that separates (a) from (b) is unchanged in kind — one
independent human reading fifteen of the same 39. What changes is who, and
which fifteen.

**Eligibility of the third labeller.** The sheet may be given to a person who
has read none of: `_fm23_my_labels.md`, the labelled `_fm23_label_sheet.md`,
`_fm23_blind15.md`, §13.2, §13.5, §14 of this document. 🔴 **The second labeller
is no longer eligible**, by the disclosure above.

**Handover constraint, stated because the channel is now contaminated.** The
person handing the sheet over knows the primary labels and their class balance.
They may hand it over and answer procedural questions. They may not supply: the
primary labels, the line in §13.2, the class balance, an expected count, or a
characterisation of any individual trace. §13.6 withholds three things by
design — labels, line, balance — and that withholding now has to hold in a
conversation rather than only in a file.

**Pool: all 39.** The fifteen disclosed ids are not excluded. Contamination
attaches to the person, not to the trace: a labeller who has never seen the
primary labels is uncontaminated on all 39. Excluding them would also cut
swe_bench to four remaining and make a quota of three nearly exhaustive, which
costs stratification for no gain in independence. The residual risk is that
overlap raises the chance of inadvertent commentary on a trace the handover
channel remembers; the constraint above is the control, and it is a constraint
on a person rather than a property of the design.

**Draw.** Seed **59**, declared here and committed before the drawing script is
run; the script is run once and on no other seed, and the commit order in git is
the evidence. Stratified by split in the same proportion as §13.4 — **gaia 12,
swe_bench 3** — drawn on the sorted id list, **not on any label**. Neither the
primary labels nor `_fm23_draw40.RESULTS.json` is read by the drawing script.

Expected before running, so that the dry-run can falsify it:

| | expected |
|---|---:|
| pool | 39 (gaia 32, swe_bench 7) |
| drawn | 15 (gaia 12, swe_bench 3) |
| ids overlapping the disclosed fifteen | ~6 (15 x 15/39 = 5.77) |
| traces TRAIL marks `goal deviation` within the draw | ~8 (15 x 21/40 = 7.88) |

**The sheet is built to §13.6 unchanged**: the same reduced view the primary
labels were made from, the question, and `?` as a first-class answer.

### 14.3 The read rule is carried over unchanged, and its power is reported with it

§13.5's thresholds are **not moved**. The replacement sheet has the same size,
the same pool and the same quota, so the same rule applies:

| third labeller's 15 | reading |
|---|---|
| POS 0–2 | (a) — this corpus does not carry the axis under our definition. §3's mapping to TRAIL's `Goal Deviation` is withdrawn and the negative result is written under our own definition only |
| POS 3+ | (b) — the line in §13.2 is narrower than FM-2.3. The finding is about the labelling, and a relabel is a new pre-registration rather than an edit to this one |

One quantity is added to the report, and it is a disclosure rather than a gate:
**how many of the drawn fifteen TRAIL itself marks positive.** A labeller who
answers NEG to everything and a labeller who agrees with the primary labels
produce the same count, and that count is only evidence for (a) if the sheet
actually contained traces the other side calls positive. The number is reported
beside the result for that reason.

🔴 **It does not decide whether the sheet is accepted.** An unfavourable draw is
not grounds for a redraw; a redraw conditioned on the draw's contents is the
knob §1.3 names. If the count comes back low, the sheet is reported with its
weakness stated.

### 14.4 P1 is still not reported as a score

§13.5's degeneracy is a property of the primary labels, not of the draw: 38 NEG
and 1 BORDERLINE means any fifteen drawn from the 39 is at or near a single
class, and the constant answer scores at or near 1.0000. **P1 is read as a raw
disagreement count on the replacement sheet as well**, and the margin gate in §6
is not applied to it.

### 14.5 The axis is parked until the third labeller exists

The draw and the sheet are prepared so that the handover costs nothing once a
person is available. **No further engine work on FM-2.3 is scheduled**, and the
negative result document stays unwritten. This is a dependency on a person, and
it is recorded as a dependency rather than as work in progress.

### 14.6 The draw ran, and the overlap landed where it costs most

Run after §14.2 was committed, on seed 59 and on no other seed
(`_fm23_blind15b.py`, derived from `_fm23_blind15.py` by substitution of the
seed, the output names and the addressee only, so the reduced view is the same
code path §13.6 requires).

| | expected in §14.2 | measured |
|---|---:|---:|
| pool | 39 (gaia 32, swe_bench 7) | **39 (32, 7)** |
| drawn | 15 (gaia 12, swe_bench 3) | **15 (12, 3)** |
| ids overlapping the disclosed fifteen | ~6 | **7** |
| traces TRAIL marks `goal deviation` | ~8 | **7** |

`gaia_001 003 013 037 054 065 067 075 079 099 111 114`,
`swe_bench_001 006 021`. Raw: `_fm23_blind15b.json`.

Both expectations hold within the noise of a 15-draw, and the sheet has the
contrast §14.3 asks for: **7 traces TRAIL calls positive against 8 it calls
negative.** A labeller who answers NEG to everything is therefore separable from
one who agrees with the primary labels, which was the defect §14.3 was added to
cover.

🔴 **One quantity was not predicted and is worse than the expectation implies.
Of the 7 traces TRAIL calls positive, 4 are in the overlap with the disclosed
fifteen** — `gaia_001 013 037` and `swe_bench_001`. The overlap did not land
uniformly; it landed on the traces that carry the test. The handover constraint
in §14.2 is therefore load-bearing rather than precautionary, and the cleanest
form of it is that the third labeller receives the sheet without the disclosed
fifteen being discussed at all.

**This is not grounds for a redraw.** §14.3 fixed before the draw that an
unfavourable draw is reported with its weakness stated rather than replaced, and
a redraw conditioned on where the overlap fell is the knob §1.3 names. The seed
stands, the sheet stands, and this paragraph is the disclosure.

Two further facts from the answer key, recorded because they bound what any
result here can mean:

- TRAIL's positives are **almost entirely gaia**: 20 of 32 gaia against **1 of 7
  swe_bench**. The three swe_bench traces in the sheet carry close to none of
  the contrast; the twelve gaia traces carry it.
- The sheet is **226,945 characters** against the disclosed sheet's 262,470, and
  64 tool calls against 159. Neither number is a threshold; they are recorded so
  that "the second sheet was easier" is checkable rather than arguable.

### 14.7 What is now blocked, and on what

The sheet exists and the handover costs nothing. **FM-2.3 is blocked on one
thing: a person who satisfies §14.2's eligibility.** No engine work is
scheduled, no judge is called, and the negative result document stays unwritten
until the fifteen come back.

Neither the sheet nor the drawing script is committed — the diagnostics
convention, and TRAIL's no-redistribution gate. This document and the raw
counts in it are the committed record.

### What is explicitly NOT changed

- **No judge call. No cost.** P3–P6 are not run on this corpus.
- **P2 stands at 0–1 of 39 and is final as measured.** Relabelling the 39 is not
  permitted here.
- §13.1's two readings (a) and (b), §13.2's line, and §13.3's status as a
  description rather than a score all stand as written.
- Target category, normalisation, unit, the 40-trace sample, the model, the
  prompt, and the 120,000-character cap are untouched.
- The negative result document is not written until the replacement fifteen come
  back.

## 15. Amendment (2026-10-01): TRAIL's own written reasons, under a rule fixed before they were read

§14.7 leaves the axis blocked on a person. There is one instrument that does not
need one: **TRAIL's labels carry human-written justifications.** Each error record
holds a span `location`, an `evidence` quote, a free-text `description` and an
`impact`. Reading those does not re-judge any trace and does not need a second
labeller — it reads what the other side wrote down about what it was counting.

What that can settle is §3's mapping claim, which §13.1 reading (a) turns on. What
it cannot settle is §13.1 reading (b); §15.3 states that limit rather than eliding
it.

Measured before this rule was written, from label structure only and with no
`Goal Deviation` justification opened:

| | |
|---|---:|
| TRAIL labels, all categories | 841 over 148 traces |
| `Goal Deviation` labels | **65** over **64** traces (base rate 0.4324) |
| positive traces carrying **exactly one** GD label | **63 of 64** |
| in the 40-sample: positives carrying exactly one | **21 of 21** |
| median labels per trace, positives / negatives in the 40 | **5 / 5** |

Two structural facts follow, and both bear on §3:

🔴 **The unit does not match.** TRAIL's 21 means *one span carries a Goal
Deviation tag among about five tagged errors on the same trace*. The FM-2.3
primary label is a **trace-level verdict**. §3 compared a span-level event tag
against a trace verdict and called the two the same target. This is the shape
[[feedback-measured-target-identity]] names, and it is recorded here as the first
finding rather than as a conclusion: **a span tag can still mark genuine
redirection**, so the unit mismatch alone does not decide (a).

**The category strings were free-typed.** About 31 surface forms cover roughly 14
categories, including `Goal deviation` beside `Goal Deviation` and
`Instruction non complience`. Positives are also not more error-dense than
negatives (5 against 5), so the tag is not a severity marker. Neither fact is a
threshold; both bound how much weight a single tag can carry.

### 15.1 What has already been read, stated so the blinding is checkable

One label record was printed while establishing the schema: gaia parquet row 0,
`trace_id 041b7f9c8c76c2ca1a8e67c6769267c3`. **It is not in the 40-sample and
carries no `Goal Deviation` label.** At the commit of this section, no
`Goal Deviation` `evidence` or `description` has been read.

The 21 are addressed by `(split, parquet row index)`, not by `trace_id` —
`gaia_024`, `gaia_037` and `gaia_065` carry `trace_id: null` in the answer key.
All 21 resolve, all parse, and each carries exactly one GD label.

### 15.2 The coding rule, fixed before reading

Each of the 21 justifications is coded into **exactly one** bucket, from TRAIL's
own `evidence` + `description` + `location`:

- **F — failed execution of the stated objective.** Hallucinated tool output; an
  unverified assumption asserted as fact; a wrong answer; verification skipped; a
  tool error; a delegation that never happened; an answer submitted without ever
  reaching the named source. Under §13.2 these are FM-3.x and not deviation.
- **D — redirection away from the stated objective.** Worked a different question;
  adopted a self-invented substitute target; continued actions that cannot
  advance the stated goal.
- **O — not codable.** Describes the harness rather than the agent; restates the
  category without naming a behaviour; names a behaviour fitting neither bucket.

**Procedure, against the author's own bias.** Each justification is coded **from
its text alone** — the trace is not opened and the primary label for that trace is
not consulted while coding. The mapping back to the primary labels happens only
after all 21 are coded. Each of the 21 is recorded with its bucket and a quoted
fragment, so the coding is auditable rather than asserted.

🔴 The author knows the gap is 20 traces and knows which answer would be
convenient. That is the reason the rule is written here and not after the reading.

### 15.3 The read rule

| coded over the 21 | reading |
|---|---|
| **D ≤ 3** | **(a)** — the categories differ. §3's mapping to TRAIL's `Goal Deviation` is withdrawn, and the negative result is written under our own definition only, carrying the unit mismatch above |
| **D ≥ 7** | **(b)** — the line in §13.2 is narrower than FM-2.3. The traces are named, the 39 primary labels are reported as what they are, and a relabel is a new pre-registration rather than an edit to this one |
| **D 4–6, or O ≥ 8** | **inconclusive** — the justifications do not carry the decision. The definition A/B described in §15.5 becomes the next step and the negative result stays unwritten |

The dead band at 4–6 is deliberate. This instrument is one person's coding of
another person's prose, which is noisier than a verdict, and forcing a call across
a single-case boundary would be false precision. **No threshold here moves after
the coding.**

🔴 **What a clean (a) still does not buy.** It tests whether TRAIL's category
differs from ours. It does **not** test whether the first labeller's line is
narrower than FM-2.3's own wording — the question §13.5's sheet existed to answer.
Even D = 0 leaves (b) open, and the negative result must say so in those words.
§14 is not withdrawn: seed 59 and `_fm23_blind15b.md` remain the only instrument
for (b) and stay available if an eligible labeller appears.

### 15.4 What a result here is allowed to change

- **(a)** permits one sentence that was not permitted before: *TRAIL's
  `Goal Deviation` and FM-2.3 as defined in §2 are not the same target, at the
  unit and at the behaviour.* It does not permit *this corpus contains no FM-2.3
  failures*, which remains a claim about our own labels at 0–1 of 39.
- **(b)** permits naming the specific traces the primary labelling missed, and
  nothing more; the relabel is a new pre-registration.

### 15.5 The fallback, declared now so it is not chosen after the fact

If §15.3 returns inconclusive, the next step is a **definition A/B on one model**:
the same traces judged twice, once under §2's wording and once under TRAIL's own
wording for `Goal Deviation`, with model, prompt scaffold, view and cap identical
and **only the definition text differing**. A split in the two counts localises the
gap to the definition; two low counts localise it to the human labels.

That run costs money and is therefore **not authorised by this amendment**. It
requires its own pre-registration with a billing guard
([[reference-dead-key-scores-like-a-result]]), and it is named here only so that
the choice of fallback is fixed before the coding rather than after it.

### What is explicitly NOT changed

- **No judge call. No cost.** P3–P6 are not run on this corpus.
- **P2 stands at 0–1 of 39 and is final as measured.**
- §14 stands in full. Seed 59, the sheet, the eligibility rule and the handover
  constraint are untouched.
- The 39 primary labels are not relabelled.
- The negative result document is not written until the coding is done.
