# Results: FM-2.3's positive class is 0–1 of 39 here, and TRAIL's `Goal Deviation` is not the same question

Scores `FM_2_3_DERAILMENT_TRAIL_PREREG.md`, including its §11–§16 amendments.
Hand labels and P2 were scored 2026-10-01. The 20-trace gap that P2's miss
exposed was then resolved by coding TRAIL's own written justifications, under a
rule committed before they were read, and is reported here because it changes
what the negative result says.

**P2 missed: 0 positives in 39 hand-labelled traces against a floor of 8 — 1 if
the single BORDERLINE is counted as positive. The judge was never called, so
P3–P6 are not scored: not failed, not run. The recorded cost of this axis is
zero.**

**P1 is not reported.** Two independent reasons, both documented before the fact:
its margin gate is arithmetically unreachable at this class balance (§13.5), and
the blind sheet was disclosed before it was graded (§14).

**🔴 TRAIL's `Goal Deviation` and FM-2.3 are not the same target.** TRAIL marks
21 of the same 40. Coding all 21 of its human-written justifications returns
**20 describing failed execution of the stated objective and 1 describing
redirection away from it**. TRAIL's category, as its labellers applied it, asks
whether the agent departed from **its own plan**; this axis asks whether it
departed from **the task's objective**. The mapping claim in §3 is withdrawn.

---

## 0. What was scored

| # | prediction | result | |
|---|---|---|---|
| P1 | hand-label agreement ≥ 0.80 on the blind 15, **and** ≥ 0.10 above a constant answer | **not reported** — gate unreachable (constant answer 1.0000 ⇒ requirement 1.1000) and the sheet was disclosed before grading | — |
| P2 | ≥ **8 of 40** hand-labelled positive | **0** strict / **1** counting the single BORDERLINE, in a frame of **39** | **MISS → stop** |
| P3 | judge precision ≥ 0.70 | not run | — |
| P4 | judge recall ≥ 0.60 | not run | — |
| P5 | 0 findings with evidence absent from the view | not run | — |
| P6 | parse failures ≤ 2 of 40 | not run | — |
| P7 | *observation* — agreement between hand labels and TRAIL's `goal deviation` | **21 against 0–1.** Resolved in §3 below | finding |
| P8 | *observation* — median view length, flagged vs unflagged | **not measurable as written** — nothing was flagged, because the judge never ran. Measured on TRAIL's labels instead: positive **17,953** chars vs negative **30,198** | proxy, see §4 |

**No judge call was made and no key was charged.** §8 puts P2 before the judge
precisely so that an axis with nothing to measure stops before it costs anything.
FM-2.2 and FM-2.3 are the two runs that have had this gate, and it has held on
both.

**The frame is 39, not 40.** `swe_bench_011` does not ingest — `ValidationError:
duplicate span_id 'b14646a5fcac02fd'` — and was excluded before labelling rather
than after (§11.2). It is TRAIL-negative, so excluding it does not inflate the
positive rate.

Provenance. The draw, the labels, the blind sheets and the rationale coding are
diagnostics and stay uncommitted, by the standing rule that diagnostics carry raw
output and not conclusions. TRAIL is MIT-licensed **without redistribution
rights**, so no trace content or label text beyond the fragments quoted in this
document is committed.

| artifact | what it fixes |
|---|---|
| `_fm23_draw40.RESULTS.json` | the sample. seed 23, TRAIL revision `b424ce63d5973d5dcd7169b1bc3c07ccdee276d1`, 40 drawn, 39 ingested |
| `_fm23_label_sheet.md` | the material the labels were made from, regenerated after `#231` restored the lost tool spans |
| `_fm23_my_labels.md` | 39 labels, each with a reason, plus the line in §13.2 |
| `_fm23_blind15.json` / `_fm23_blind15b.json` | the two blind draws, seed 23 and seed 59 |
| `_fm23_trail_rationales.CODING.md` / `.MAP.json` | the 21 justifications, shuffled on seed 7, and the mapping opened after coding |

---

## 1. P2 missed, and the miss is the result

All 39 traces were hand-labelled blind against the line frozen in §13.2, with
TRAIL's answer key unopened.

| | |
|---|---:|
| NEG | **38** |
| BORDERLINE | **1** (`gaia_002`) |
| POS | **0** |

**0 of 39 strict; 1 of 39 counting BORDERLINE as positive. The floor is 8.** No
counting convention closes that distance, and §13 did not invent one.

The line that produced it, frozen in writing after one trace had been read:

> **Failing is not deviating.** A wrong answer, a fabricated answer, a skipped
> verification, a tool error or a format violation is not by itself a deviation —
> MAST counts those separately. POS requires the agent's *actions or output* to
> aim at something other than the stated objective.

Two derived rules, both recorded during labelling rather than after it:

- **the scaffold rule** — this corpus silently degrades a delegation to
  `search_agent` into a `print`. That alone is NEG: the agent's stated intent is
  on task, and scoring it POS would make the label describe the harness rather
  than the agent.
- **the aim rule** — actions aimed at the correct target that fail and end in a
  guess are NEG; actions aimed at a self-invented substitute are BORDERLINE or
  POS. `gaia_002` is the single BORDERLINE under this rule.

**A descriptive count that is not a score.** Under a looser reading — *submitted
an answer without ever obtaining the content of the source the question names* —
**26 of 39** qualify. It is recorded as a description of the shape. P2 is counted
from the primary labels only, and §1.3 named exactly this move — a knob turned
after the result is visible — as a reason to prefer this corpus in the first
place.

---

## 2. P1 is not reported, for two reasons that do not depend on each other

**The margin gate cannot be met at this class balance.** §6 writes P1 as
agreement ≥ 0.80 **and** ≥ 0.10 above what a constant answer scores on the same
sheet. The blind 15 drawn on seed 23 are NEG 15 of 15 in the primary labels, so
the best constant answer scores **1.0000** and P1 requires **1.1000**. The margin
was added to stop FM-2.2's base-rate trap from recurring, and it does stop it; it
does not survive a sheet where the first labeller's labels are one class. The
margin is correct and the sheet is degenerate.

**The sheet was disclosed before it was graded.** Its fifteen slots were still
empty when the first labeller's own labels for those fifteen — NEG 15 of 15 —
were disclosed on request, after the leak was stated. A disclosed answer and an
independent one produce the same arithmetic, so the sheet can no longer measure
independence. This is recorded as a deviation in §14, not as a result.

A replacement sheet exists: seed **59**, declared and committed before the
drawing script ran, drawn from the full 39 on the same stratification. It has not
been graded, because it requires a labeller who has read none of the primary
labels, the line in §13.2, or §13.5–§16. **That dependency is on a person and is
recorded as a dependency.**

---

## 3. 🔴 The gap between 21 and 0–1, resolved by reading TRAIL's own reasons

§1.3 and §11.1 recorded, before any labelling, that TRAIL's own
`goal deviation` label marks **21 of the same 40**. That left two readings and
P2's number alone did not separate them: **(a)** the categories differ, or
**(b)** the first labeller's line is narrower than FM-2.3's own wording.

TRAIL's labels carry human-written justifications — a span `location`, an
`evidence` quote, a free-text `description`, an `impact`. Reading those needs no
second labeller and re-judges no trace; it reads what the other side wrote down
about what it was counting. **The coding rule, the procedure and the thresholds
were committed and pushed before any justification was opened** (§15,
`0f1a71a`), because the gap was already known to be 20 traces and the convenient
answer was already known.

### 3.1 The coding

Each of the 21 justifications was coded into exactly one bucket from TRAIL's own
text, presented shuffled with the trace identity hidden:

| bucket | | |
|---|---:|---|
| **F** — failed execution of the stated objective | **20** | |
| **D** — redirection away from the stated objective | **1** | `gaia_037` |
| **O** — not codable | **0** | |

**D = 1.** §15.3 fixed D ≤ 3 as reading (a) before the coding, and no threshold
moved afterwards.

The single D is the trace **§14.1 named in advance** as the most plausible point
of divergence — 31 actions, 5 of them off-target — and TRAIL's justification for
it is the one that describes action rather than omission.

### 3.2 What the other 20 describe

| over the 21 justifications | |
|---|---:|
| mention a *plan* | **18** |
| mention skipping it (`skip` / `bypass` / `jump` / `without`) | **10** |

The recurring form is one sentence:

> *"deviated from its own established plan by skipping steps 2 through 6"* ·
> *"bypassed these steps by directly presenting a count based on internal
> knowledge"* · *"simulate that our search_agent has returned verified sale
> prices"* · *"shifted its goal from extracting the numbers to fabricating a
> plausible output"*

Under §13.2 those are FM-3.x: verification skipped, a delegation that never
happened, a result fabricated after a tool failed. **TRAIL files them under
`Goal Deviation` because the agent departed from its own plan.** §2 asks whether
the agent departed from the task's objective. Both sentences contain the word
*deviation*; they are not the same predicate.

`gaia_002`, the single BORDERLINE in the primary labels, is coded F from TRAIL's
own words: *"That makes it a hallucination."* The one trace where this labelling
leaned positive is one TRAIL describes as fabrication.

### 3.3 How much the unit aggregation cost

§2 declared the aggregation and called it lossy: *"TRAIL localises each error to a
span, and our judge answers about a session. Aggregating up is the lossy
direction but it is the one that matches what ships."* The loss was declared. Its
size was not, and it is this:

| | |
|---|---:|
| `Goal Deviation` labels in TRAIL | **65** over **64** traces of 148 |
| positive traces carrying **exactly one** such label | **63 of 64** |
| in the 40-sample: positives carrying exactly one | **21 of 21** |
| median labels per trace, positives / negatives in the 40 | **5 / 5** |

So *"carries at least one error of that category"* resolves, in practice, to **one
tagged span among about five tagged errors on the same trace**, on traces that are
no more error-dense than the negatives. A trace-level verdict built on that is
built on a thin reed — not because §2 chose wrongly, but because the category's
own granularity is finer than the unit that ships.

### 3.4 Label quality, recorded without being used

- The category strings were free-typed: roughly **31 surface forms** over about
  14 categories, including `Goal deviation` beside `Goal Deviation`,
  `Instruction non complience`, and a leading-space variant. §2's normalisation
  handles the casing; it does not handle the typos, and nothing here depends on
  them.
- One record is internally inconsistent: `gaia_079`'s `description` describes
  abandoning a plan *"to analyze the report"* and relying on *"external
  analyses"*, while its `evidence` is an agent substituting a generic
  strawberry-pie recipe after `inspect_file_as_text` could not read an mp3. It was
  coded on the evidence and **the count was not moved.**

Neither observation is used to discount TRAIL's labels. They bound how much
weight a single tag can carry, which is the same point as §3.3.

---

## 4. The validity threats, and the two this measurement has

Checked and holding:

- **Length.** P8 as written compares judge-flagged against unflagged traces, and
  **nothing was flagged** — the judge never ran, so P8 is not measurable on this
  run. The substitute, stated as a substitute: on **TRAIL's** labels the positives
  have a *shorter* median view (17,953 chars) than the negatives (30,198). That
  tells us the §4.2 length confound does not favour TRAIL's positives, and it says
  nothing about how a judge would behave here. It is reported because it is the
  only length evidence this run produced.
- **Material parity.** The blind sheets carry the same reduced view the primary
  labels were made from. Handing a second labeller the full harness template would
  give them more material than the first labeller had, and a disagreement would
  then be unreadable.
- **Tool visibility.** The label sheet was regenerated after `#231` restored tool
  spans that an earlier view had dropped — tool spans 79 → 159, traces with zero
  tool calls 30 → 1. The labels were made from the restored view.

🔴 Two weaknesses this document carries rather than mentions once:

- **The rationale coding is one person's reading, and the blinding is weaker than
  §15.2 promised.** Trace identities were hidden and the mapping was opened only
  after all 21 were coded, but the coder had the primary labels for 15 of the 39
  in working memory from the session in which §14's disclosure happened. *Did not
  consult* is true; *could not know* is false. The mitigation that does hold:
  every one of the 21 is recorded with the fragment it was coded from, so the
  coding is checkable against TRAIL's text rather than against the coder.
- **§7's route to withdrawing §3's mapping was not the route taken.** §7 wrote
  that a strong P7 disagreement *while P1 and P3 pass* withdraws the mapping.
  P1 is unreportable and P3 was never run. The withdrawal here rests on §15–§16's
  coding of TRAIL's justifications, not on §7's condition, and that substitution
  is a judgement rather than a pre-registered step.

---

## 5. What this does and does not say

**It says:**

- **TRAIL's `Goal Deviation` and FM-2.3 as defined in §2 are not the same
  target**, at the unit and at the behaviour. TRAIL's tag marks a span where the
  agent departed from its own plan — most often by skipping its own verification
  or fabricating a result after a tool failed. §2 asks whether the agent's actions
  or output aimed at something other than the task's objective.
- **§3's mapping claim is withdrawn.** TRAIL's 21 is not cited as a count
  comparable to ours, in this document or elsewhere.
- **Under the line in §13.2, this corpus carries 0–1 positives in 39.** The axis
  stops here. No judge was called and the cost is zero.
- The gate that stopped it is the one FM-1.1 did not have. That run reached
  labelling, produced 0 positives in 40, and its predictions would have accepted
  both a judge that flagged nothing and a judge that flagged everything.

**🔴 It does not say:**

- *that this corpus contains no FM-2.3 failures.* The measurement is 0–1 of 39
  **under one labeller's line**, and that is a statement about the labels.
- *that TRAIL is wrong.* TRAIL counted plan-adherence failures and said so in its
  own justifications. That is a real category; it is a different one, and it is
  one this project counts elsewhere.
- *that the labelling was right.* **Reading (b) is untested.** D = 1 establishes
  that TRAIL was counting something else; it establishes nothing about whether the
  line in §13.2 is narrower than FM-2.3's own wording. The 20-trace gap is
  explained and *the first labeller's line may still be narrow.* Those are
  independent findings and only the first was measured.
  🔴 **Amended 2026-10-05 — see §7.** (b) has since been tested in its
  model-reader form and this clause narrows by exactly that much. The
  *"statement about the labels"* half above stands, and the run strengthened it.
- *that the axis is dead.* It is unmeasurable **on this corpus**. Three rules were
  killed on their own merits at the judge-precision gate — re-read, args-only,
  `unverified_edit` (§6 P3). FM-2.2 and FM-2.3 did not reach that gate: both
  stopped for want of a positive class, which is a statement about the corpora
  available rather than about either rule.

---

## 6. What happens next

- **Nothing is scheduled on this axis.** P3–P6 remain unrun, and running them
  would require a corpus with a positive class rather than a looser rule.
- **The replacement blind sheet stays available** (seed 59, built, ungraded). It
  is the only instrument for reading (b) and it needs an eligible labeller. The
  axis is not blocked on it; the open question is.
- **The definition A/B named in §15.5 is not authorised.** Judging the same traces
  twice under the two definitions would localise the gap further, but it costs
  money and needs its own pre-registration with a billing guard.
  🔴 **Spent 2026-10-05 — see §7.3.** It was pre-registered separately, with the
  billing guard, and run. This bullet is the only one of the four that is spent.
- **The FM-2.3 target category stands unchanged.** This document withdraws a
  mapping between two label sets, not a definition.

---

## 7. Amendment (2026-10-05): reading (b) is no longer untested, and the clause narrows by exactly that much

§5 said *"Reading (b) is untested"*. It has now been tested in one of its two
forms, and this section narrows that clause rather than rewriting it. The run:
`FM_2_3_DEFINITION_AB_RESULTS.md`, pre-registered as
`FM_2_3_DEFINITION_AB_PREREG.md` and merged before any call, 117 calls, recorded
spend **$1.320141**.

🔴 **No count in this document changes.** P2 stands at 0–1 of 39, the coding in
§3.1 stands, and §3's withdrawn mapping stays withdrawn.

### 7.1 What narrows

The same 39 traces were judged three times by one fixed reader, changing only the
definition sentence: our §13.2 line, MAST FM-2.3 verbatim, and §13.3's
operational line as a control.

| arm | definition | positives / 39 |
|---|---|---:|
| A | our §13.2 line | 19 |
| B | MAST FM-2.3 verbatim | 20 |
| C | §13.3 operational line (control) | 29 |

`N_B − N_A = 1`, against a pre-registered support threshold of ≥ 7 and a
weakening threshold of ≤ 3. The control cleared its floor of 18 and landed beside
the human count of 26 on the same line, so the instrument does respond to
definition text on this corpus.

**So the specific worry narrows:** the exclusions in §13.2 do **not** suppress the
count relative to MAST's own wording *for this reader*. The two wordings agree on
17 of the 22 traces either one flags.

### 7.2 🔴 What does not narrow — and what the run strengthened instead

§5's clause *"the measurement is 0–1 of 39 under one labeller's line, and that is
a statement about the labels"* **stands, and the run made it sharper rather than
weaker.**

The fidelity check missed: arm A — the labeller's own written line, handed to the
fixed reader — returned **19** where the labeller returned 0–1. In 10 of those 19
the reader's stated grounds are categories §13.2 explicitly excludes. So the
divergence this run exhibits is not between the two written definitions; it is
between a written definition and the person who wrote it.

**Therefore the following are NOT licensed and are not claimed:**

- that the 0–1 of 39 is a statement about MAST FM-2.3 on this corpus rather than
  about one labeller's strictness. Arm A points the other way.
- that a human reading MAST's wording would mark 0–1. The reader here is a model,
  which the A/B pre-registration named as its first validity threat.

### 7.3 Consequence for §6

**§6's third bullet is spent**, and only that one: the definition A/B it declined
to authorise has now been pre-registered separately, run, and reported.

**§6's second bullet is reaffirmed.** The seed-59 blind sheet is **not**
withdrawn and still needs an eligible labeller. It is the only instrument for the
human form of (b), and the fidelity miss above makes that form the more
interesting question rather than the less: a written sentence and its author
disagree by 19 of 39, and no run so far separates "the line is narrow" from "the
line is not what the labeller applied".
