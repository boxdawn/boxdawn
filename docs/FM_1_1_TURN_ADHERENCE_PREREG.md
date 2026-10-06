# FM-1.1 on real sessions: did the agent do what the turn asked?

Rule 8: merged before any code. Nothing here is implemented.

FM-1.1, verbatim from arXiv 2503.13657 v1 (read 2026-09-03):

> **Disobey task specification** — "Failure to adhere to the specified
> constraints or requirements of a given task, leading to suboptimal or
> incorrect outcomes."  [FC1. Specification and System Design Failures]

---

## 0. Why this is not the axis that was rejected this morning

FM-1.1 was measured on Corpus D (`mimo-cc-1k`) on 2026-09-03 and set aside.
Five of forty sessions flagged, and **two of the five were wrong on
inspection**:

> the request: *"Write a JavaScript function called `debounce` that converts
> Roman numerals to integers and vice versa."*
>
> the judge: *"'debounce' is a well-established JavaScript term referring to
> rate-limiting function calls. Using this name for a Roman numeral converter
> violates…"*

The agent did exactly what was asked. The judge graded **the request** instead
of adherence to it, because that corpus pairs an arbitrary function name with
an unrelated task, over and over. On such a corpus "constraint" and "oddity"
are the same string and cannot be told apart.

Real sessions have neither problem. Their requests were typed by a person who
meant them, and their constraints are the kind a person actually states.

## 1. Measured before deciding (2026-09-03)

84 real Claude Code sessions across 10 projects (this session excluded, since
it is the one writing the document).

**★ The first measurement was wrong and is reported rather than discarded.**
It counted constraint markers over `_user_texts(trace)`, which returns *every*
user turn in the session joined together — a median of **12,807 characters**.
Any long conversation contains the word "하지 마" somewhere, so it reported
74 of 84 sessions "carry a constraint" while the sample rows underneath it were
requests like *"현재 진행상황 좀 알려줘"*. The number was an artifact of the
unit, and finding that is what produced §2.

Re-measured at the turn level:

| | |
|---|---|
| user turns, total | **2,237** |
| turns per session | median 16.5, max 91 |
| turn text | median **66 chars** (against 12,807 for a whole session) |
| tool calls per turn | median **3**, mean 7.0 |
| turns with ≥3 tool calls | **1,238** (55%) |
| of those, tripping a constraint marker | **397** (32%) |

For contrast, Corpus D: one request at the top, median 136 characters, median
~4 tool calls, no second turn. **These are different objects and the axis has
to say which one it judges.**

Constraints of a kind Corpus D does not contain, quoted from the turns:

- *"너의 범위는 현재 웹 및 디텍터 세션이 하는 코딩작업은 **건들지마**"*
- *"아니 지자체 사업은 **조사 안 해도 돼**"*
- *"**다른 세션에게 물어보지말고**"*
- *"**로컬 커밋만** 하자"*
- *"Task #10 부터 **먼저** 진행하자"*

## 2. The unit is the turn, and that is the substantive decision

`JUDGE_VIEW_USER_TURN_AMENDMENT_PREREG` §7 left this open in as many words:
*"Whether 'the request' is the first block or the last one is a question each
following axis answers for itself."* This is the answer.

**A judged unit is one user turn plus every tool call until the next user
turn.** Not the session. A 91-turn session has no single "task specification",
and a judge asked whether a session obeyed its request would be asked to pick
one of 91 requests without being told which.

Consequences, stated so they are not discovered later:

- A turn that states no constraint cannot disobey one, and is **out of
  population**, not a passing case. Scoring it as "obeyed" would inflate
  accuracy with sessions the axis never looked at.
- Constraints carry forward. *"건들지마"* in turn 4 still binds in turn 9. The
  judged view for a turn therefore includes **earlier user turns as context**,
  and the frozen renderer already emits every user turn in order, so this
  needs no new plumbing — only a marker for which turn is under judgement.
- One session yields many judged units. **Sampling is per turn, not per
  session**, and the sample must not draw many turns from one session, or the
  measurement becomes a statement about one conversation.

## 3. The marker list is a candidate generator, not the definition

Prohibition / restriction / obligation strings select 397 turns. They
over-select, visibly:

> *"지금 진행상황과 해야할 일 말해줘"* trips `해야` and is a **question**, not
> a constraint on the agent.

So the markers only decide **what gets read**. Whether a turn states a
checkable constraint is a label, applied by a person, and a turn the markers
missed is a false negative this document does not claim to bound. Recall of
the generator is explicitly out of scope; §7 names it as a limit.

## 4. 🔴 The corpus is our own conversations, and that is a validity threat

These sessions are the user working with Claude. The label *"did the agent
obey"* is therefore **a judgement about Claude's work, drafted by Claude, and
scored by a Claude judge.** FM-3.2 did not have this problem: "did a test run"
is a mechanical fact visible in the trace.

Named because it cannot be removed, only measured:

1. **Labels are drafted by this session and reviewed by the user.** The user
   chose this over labelling from scratch, with the fallback of finding an
   external corpus if it proves unworkable.
2. **The user independently labels a random 15 of the sampled turns**, blind to
   the drafted label. Agreement is computed and published.
3. **P1 below gates on that agreement**, not only on judge precision. Labels
   the two parties disagree about are not usable ground truth, and a judge
   scored against them measures nothing.
4. The judge model and the judged agent are the **same model family**. This is
   already true of FM-3.2 and is stated as a limit in both places rather than
   claimed to be controlled.

## 5. What is explicitly NOT changed

- **The judge's view.** The renderer shipped in 0.5.9 already emits user turns;
  this axis marks which turn is under judgement and adds nothing to what is
  transmitted. **No `/privacy` change is required by this document**, and if
  that stops being true the disclosure comes first, as in the amendment.
- **FM-3.2.** Its prompt, its view, its 40 labels and its published figures are
  untouched. This axis is a separate call.
- **No cost or waste-rate field.** `wasteful == (waste_span_count > 0)` stays an
  identity.
- **No alert.** Whether this should ever page anyone is a separate question.
- **Corpus D stays the corpus for FM-3.2.** Nothing is re-scored there.

## 6. Predictions (written before any labelling or judging)

Sample: **40 turns**, drawn at random from the 397 marker-selected turns, with
**at most 3 turns from any one session**.

| # | Prediction | What rejects it |
|---|---|---|
| **P1** | user–draft label agreement on the blind 15 ≥ **0.80** | below 0.80: the labels are not usable and the run stops before the judge is called |
| **P2** | at least **12 of 40** sampled turns carry a genuinely checkable constraint | fewer than 12: the marker list selects mostly questions and the population is not there |
| **P3** | judge precision on the finding ≥ **0.70** | below 0.70, the gate that killed `unverified_edit` (0.3250), args-only (0.633) and re-read (0.033) |
| **P4** | judge recall ≥ **0.60** | below 0.60 |
| **P5** | **0** verdicts cite evidence absent from the turn's view | any hallucinated quote (checked with escaping normalised — the check that produced two false alarms on 2026-09-03) |
| **P6** | parse failures ≤ **2 of 40** | 3 or more |

P1 and P2 are gates **before** the judge runs, and are the point of this
document. An axis measured against labels nobody else agrees with, or over a
population that turns out to be questions, produces a number that looks like
the others in this repository and means less.

**Written expectation, not a prediction:** P2 is the one at risk. The marker
sample above suggests the obligation category is mostly questions; if P2 fails
it is likely to fail on that category alone, in which case the honest move is a
prohibition-only population in a follow-up document, not a re-drawn sample
here.

## 7. What would make this fail

- **P1 misses** — labels are not ground truth. Stop, and go to the external
  corpus the user named as the fallback. Do not relabel until agreement
  improves; that is fitting the labels to the answer.
- **P2 misses** — the population is questions, not constraints. Publish as a
  negative result about the generator, not about FM-1.1.
- **P3 or P4 misses** — published beside `unverified_edit` (0.3250), args-only
  (0.633) and re-read (0.000–0.033), in the same place and the same words.
- **P5 misses** — immediate stop.
- **The prompt is not re-written after seeing any of these numbers.** The
  original judge pre-registration says the next move after a miss is a
  different corpus, not a different prompt, and today's rejected axes were
  rejected under that rule rather than tuned into passing.

## 8. Order of work

1. This document, merged, before any code. (rule 8)
2. Turn segmentation and the marker generator as a diagnostic script
   (uncommitted). Sample 40, record the draw so it is reproducible.
3. Drafted labels, then the user's blind 15. **P1 and P2 scored here.** Stop if
   either misses.
4. The judge prompt and the per-turn view, beside the existing axis.
5. Score P3–P6 on the 40. Results document with every prediction scored,
   including those that fail.
6. Only on a pass: wiring, and a decision about whether this ships behind the
   same plan gate and the same per-project switch as FM-3.2.

## 9. Amendment (2026-10-06): whether TRAIL's `Instruction Non-compliance` counts FM-1.1, under a rule fixed before the reasons were read

`FM_1_1_TURN_ADHERENCE_RESULTS.md` closed this axis with zero violations in forty
labelled turns. Its own title says where that zero was measured: **on our own
sessions.** A zero on one corpus leaves open whether a corpus that carries the
failure would make the axis measurable, and §4 of this document already recorded
our own conversations as a validity threat.

TRAIL is local, human-labelled at span level, and carries a category whose name
matches this axis. That name match is the whole question, and this project has
already paid once for assuming it was a construct match: `FM_2_3_*` §15 coded
TRAIL's `Goal Deviation` justifications and found the category counts **failure
to carry out the agent's own plan**, not redirection away from the given task.
The mapping is therefore tested before the axis is re-opened, not after.

### 9.1 Structural facts, measured before this rule was written, with no justification opened

| | |
|---|---:|
| TRAIL labels, all categories | 841 over 148 traces |
| `Instruction Non-compliance` labels, normalised | **156** over **78** traces · base rate **0.5270** |
| by split | gaia **52 / 117** = 0.4444 · swe_bench **26 / 31** = **0.8387** |
| positive traces carrying **exactly one** INC label | **45 of 78** (`Goal Deviation`'s figure was 63 of 64) |
| INC labels per positive trace | 1:45 · 2:16 · 3:5 · 4:4 · 5:3 · 6:3 · 7:1 · 8:1 |
| median labels per trace, INC-positive / INC-negative | **5 / 5** |
| `impact` over the 156 | MEDIUM **94** · LOW **46** · HIGH **16** |
| `location`, `evidence`, `description` present | **156 / 156** each |
| rationale size | `evidence` median **146** chars (max 1,842) · `description` median **296** (max 537) |
| distinct INC spans | **154** |
| INC spans also carrying a `formatting` tag on the **same span** | **18 of 154** |
| co-occurrence on INC traces | `formatting` 36 (46%) · `goal deviation` 34 (44%) · `language-only` 28 (36%) |

Revision pinned at `b424ce63d5973d5dcd7169b1bc3c07ccdee276d1`, the same snapshot
§15 used. The 156 are after normalisation: case-folded, whitespace-collapsed,
`non-compliance` and `non complience` folded to one form, a trailing `Errors?`
dropped. The category strings were free-typed, which §15 already recorded. Probe
scripts are diagnostics and are not committed.

Three facts follow, and all three bear on the mapping:

🔴 **The unit mismatches, and differently than it did for FM-2.3.** §2 fixes the
judged unit as one user turn plus every tool call until the next user turn.
TRAIL's INC is a **span tag**, and unlike `Goal Deviation` it repeats: **33 of 78**
positive traces carry two or more, up to eight. A trace-level reading of this tag
discards what the labeller recorded; a turn-level reading needs a span-to-turn
map that does not exist yet. Recorded here as the first finding rather than as a
conclusion — a repeated span tag can still mark genuine disobedience.

**The tag is mostly not severe.** 140 of 156 are MEDIUM or LOW. A mapping that
holds can still leave a thin pool of the cases a detector would have to be right
about, so §9.4 reports the coding by `impact` as well as in total.

**The split base rates differ by about two.** 0.8387 on swe_bench against 0.4444
on gaia, over 31 traces against 117. A pooled rate hides that, so every count in
§9.4 is reported per split and the two are never summed into one rate.

### 9.2 What has already been read, so the blinding is checkable

At the commit of this section, **no INC `evidence` or `description` string has
been displayed or read.** The probes above computed counts, string *lengths* and
`impact` values; `location` values were compared for span collision and their
contents were not inspected.

One label record was printed in full on 2026-10-01 while establishing the schema
for §15: gaia parquet row 0, `trace_id 041b7f9c8c76c2ca1a8e67c6769267c3`. It
carries five labels and **none of them is `Instruction Non-compliance`**, so it
contributes nothing to the 156.

### 9.3 The coding rule, fixed before reading

Each of the 156 labels is coded into **exactly one** bucket, from TRAIL's own
`location` + `evidence` + `description`:

- **T — a constraint stated in the task prompt was violated.** Content or form,
  as long as the request itself states it: an answer-format instruction in the
  task text, a named prohibition, a required source. Under §2's line this is
  FM-1.1.
- **S — the agent's own stated plan or promise was not carried out.** This is the
  construct §15 found behind `Goal Deviation`. Not FM-1.1.
- **H — a harness or system convention was violated that the task prompt does not
  state.** Tool-call schema, the harness answer wrapper, reply language where the
  harness fixed it, framework role rules. Not FM-1.1 under §2, which requires the
  constraint to be in the request.
- **O — not decidable from the three fields.**

Code the span the `evidence` quote is about. Where a trace carries several INC
labels, each is coded separately and traces are not summarised.

Tie-breaks, fixed now and **in the direction that lowers T**:

- T or H undecided → **H**
- T or S undecided → **S**
- any bucket or O undecided → **O**

The reported T is therefore a lower bound, and a pass cannot be produced by
resolving ambiguity toward the hypothesis.

### 9.4 The decision, fixed before reading

n = **156**, coded in full. No sampling, so there is no draw to report and no
seed to choose. Counts are reported per split and by `impact`.

| T, share of 156 | what follows |
|---|---|
| **≥ 0.70** | TRAIL's INC is a usable FM-1.1 positive pool. Proceed to an axis amendment: sample, drafted labels, judge, the 0.70 precision gate, and the **minimum-positive prediction** that §1 of the results document records as the hole in the original six |
| **0.40 – 0.70** | usable only under a definition widened to include H. That widening is a separate amendment written **before** any labelling, and the widened axis is no longer §2's line — it must carry a different name |
| **< 0.40** | the category counts something else. FM-1.1 stays parked on this corpus and the negative result is published as FM-2.3's was |

Three guards:

- **O ≥ 0.30** → the three fields do not carry enough to decide. Report that and
  do not force a verdict. A check that fails almost everything is first evidence
  about the check.
- **The splits disagreeing across a boundary** → the usable pool is the split
  that passes, not the union.
- **The 18 spans tagged both INC and `formatting`** are reported as their own
  line. They are the T/H boundary by construction.

### 9.5 What this cannot settle

- **The 0/40 on our own sessions stands.** Nothing here re-labels those turns or
  says anything about prevalence in production sessions.
- Whether a judge can score the axis. That needs the axis amendment and its own
  gate.
- Whether TRAIL's labellers applied their own category consistently. The coding
  reads what they wrote, not whether they were right to write it.
- Recall of TRAIL's INC tag. Disobedience the labellers did not tag is not
  bounded here.

### 9.6 Predictions, written before the first rationale is opened

| | prediction |
|---|---|
| T | **0.55 – 0.75**, point **0.65** |
| S | ≤ 0.15 |
| H | 0.15 – 0.35 |
| O | ≤ 0.10 |
| T among the 16 HIGH-impact labels | **≥ 8** |
| T on swe_bench minus T on gaia | within **0.20** |

🔴 Named in advance — **a pass with a thin pool.** 140 of 156 are MEDIUM or LOW.
A rule that fires on a low-impact wording slip is the shape `unverified_edit` had
at 0.3250. If T ≥ 0.70 while HIGH-impact T < 8, the axis amendment states the
thin-pool limit in its own predictions instead of inheriting this pass.

🔴 Named in advance — **a large S changes more than this axis.** If S is large,
TRAIL encodes *self-adherence* under at least two category names, which bears on
what this corpus can support on every axis, not only FM-1.1.

### 9.7 Order of work

1. This section, merged, before any rationale is read. (rule 8)
2. Read and code all 156 in a diagnostic script (uncommitted), one bucket each,
   tie-breaks as §9.3.
3. A results section in this document: raw counts per split and per `impact`, the
   18 boundary spans, and every prediction in §9.6 scored, including those that
   fail.
4. Only then, the axis amendment or the published negative result.

**No judge call. No cost.** The reading is local and the corpus is already on
disk. TRAIL traces and the derived sheets are not committed — the diagnostics
convention and TRAIL's no-redistribution gate.
