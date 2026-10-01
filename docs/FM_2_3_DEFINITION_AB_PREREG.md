# FM-2.3 definition A/B: is our line narrower than MAST's own wording?

Pre-registration. Written before any call is made. Supersedes the sketch in
`FM_2_3_DERAILMENT_TRAIL_PREREG.md` §15.5, and **asks a different question than
that sketch did** — see §0.1.

**One question.** `FM_2_3_DERAILMENT_TRAIL_RESULTS.md` §5 states that reading
**(b)** — *the first labeller's line may be narrower than FM-2.3's own wording* —
is untested, and that the 0–1 of 39 count is a statement about that labeller's
line rather than about the corpus. This run tests it without a human, by holding
the reader fixed and changing only the definition text.

---

## 0. Why this exists, and why it is not §15.5

§16 settled the gap between TRAIL's 21 and our 0–1: TRAIL's `Goal Deviation`
marks departure from the agent's **own plan**, at **span** granularity. That
closed reading (a). It said nothing about (b), and §16.3 required the negative
result to say so in those words. It does.

(b) is the more consequential of the two. If our line is narrower than MAST's
wording, then **every axis this project has stopped for want of a positive class
is suspect**, because the same labeller wrote the lines for all of them. Four
axes have stopped that way: FM-1.1 at 0 of 40, FM-1.5 at 1 candidate, FM-2.2 at
1 of 40, FM-2.3 at 0–1 of 39.

### 0.1 🔴 This is not the experiment §15.5 described

§15.5 wrote: *"the same traces judged twice, once under §2's wording and once
under TRAIL's own wording for `Goal Deviation`"*. That is **our line against
TRAIL's**, and it digs further into a gap §16 has already explained.

**(b) is our line against MAST's own wording.** The question is whether our
exclusions narrow MAST FM-2.3, not whether TRAIL meant something else — that is
already answered. This document runs the latter comparison and records the
substitution rather than performing it silently. §15.5's version is not run.

---

## 1. The three arms

The **only** thing that differs between arms is the definition sentence. The
system prompt's instructions about evidence, the view, the truncation, the output
shape and the question stem are byte-identical across arms.

### Arm A — the line that produced the 0–1 count

Verbatim from `FM_2_3_DERAILMENT_TRAIL_PREREG.md` §13.2:

> Failing is not deviating. A wrong answer, a fabricated answer, a skipped
> verification, a tool error or a format violation is not by itself a deviation.
> A deviation requires the agent's actions or output to aim at something other
> than the stated objective.

### Arm B — MAST FM-2.3, verbatim · **this is the test**

> Deviation from the intended objective or focus of a given task, potentially
> resulting in irrelevant or unproductive actions.

### Arm C — positive control, with a human count already in hand

Verbatim from `FM_2_3_DERAILMENT_TRAIL_PREREG.md` §13.3:

> Submitted an answer without ever obtaining the content of the source the
> question names.

🔴 **Arm C is a control, not a test.** The same labeller, on the same 39 traces,
counted **26** under this line. It exists because A and B both returning ~0 has
two readings — *the definition text does not matter* and *the instrument cannot
see this axis at all* — and only an arm with a known human target separates them.
Its target comes from our own labelling on our own traces, which is a tighter
control than TRAIL's 21 (different labellers, span granularity).

### 1.1 What is held identical

| | |
|---|---|
| model | `claude-haiku-4-5` (`DEFAULT_JUDGE_MODEL`, the shipped pin) |
| temperature / max_tokens | `0.0` / `256` (`anthropic_client`, shipped) |
| view builder | `render_trace_for_judge`, the shipped renderer |
| tool output cap | 2,000 chars (`TOOL_OUTPUT_MAX_CHARS`) |
| view cap | 120,000 chars (`VIEW_MAX_CHARS`) with the shipped truncation notice |
| sample | the **same 39** traces the hand labels were made on |
| output shape | `{"deviated": <true\|false>, "evidence": "<verbatim quote or an explanation if none>", "confidence": <0.0-1.0>}` |
| calls | one per trace per arm, no retries on content, no re-prompting |

**No prompt tuning.** The prompt is written once, before any call, and is not
revised after a count is seen. §7 of the verification prereg names re-prompting
after seeing the number as the thing pre-registration exists to prevent, and that
rule holds here.

**Nothing from this run ships.** No `src/` change is authorised by this document.

---

## 2. Predictions, with thresholds fixed now

Let **N_A**, **N_B**, **N_C** be positives out of 39 in each arm. The hand labels
are **0** strict, **1** counting the single BORDERLINE.

| # | prediction | if it misses |
|---|---|---|
| **Q0** | 🔴 **control**: `N_C ≥ 18` | the instrument does not track definition text on this corpus. **Q2 is not read**, and the run is reported as uninterpretable rather than as a null |
| **Q1** | *fidelity*: `N_A ≤ 4` | `N_A ≥ 10` means the written line does not reproduce the labels it supposedly produced. That is a finding about the line's writtenness, reported as one, and Q2 then compares two written lines rather than the labeller's actual standard |
| **Q2** | 🔴 **the test**: `N_B − N_A` | **≥ 7** → **(b) supported**: our line is narrower than MAST's wording. **≤ 3** → **(b) weakened**: the two definitions behave alike under a fixed reader. **4–6** → **inconclusive** |
| **Q3** | 0 findings per arm whose quoted evidence is absent from the view | any hallucinated evidence voids **that arm**; if Arm C is voided, Q0 fails with it |
| **Q4** | parse failures ≤ 2 of 39 per arm | reported with the cost |

The dead band at 4–6 is the same convention as §15.3 and for the same reason:
forcing a call across a single-case boundary would be false precision.

**No threshold in this table moves after a count is seen.** The author already
knows the hand labels, the 26, and which outcome would be convenient.

### 2.1 Expected before running, so the run can contradict it

| arm | expected | why |
|---|---:|---|
| A | **0–2** | should reproduce the hand labels if §13.2 is faithfully written |
| C | **20–30** | the human count on the same line and traces is 26 |
| B | **not predicted** | predicting it would be predicting the answer |

🔴 **B is deliberately left without an expectation.** A stated expectation for the
arm under test is a prior this document has no right to; A and C are the arms
whose values are already known from human labelling, and they are the ones that
can falsify the setup.

---

## 3. 🔴 Billing guard

The only visible sign of a dead API key is a cost of zero, which scores exactly
like a clean negative result. So:

- **Exact call budget: 117** (3 arms × 39 traces). The runner **aborts above 125**.
- **Spend ceiling $5.00.** The runner aborts on crossing it.
- 🔴 **Before any count is read**, assert **aggregate cost > 0** *and* **per-arm
  cost > 0** *and* **per-call cost > 0 for at least 37 of 39 calls in each arm.**
  A zero anywhere means the result is a key failure, not a measurement.
- The **recorded** cost is reported, not the planning figure.

**Planning figure:** §11.5 measured the 39 views at roughly 424,000 input tokens
after truncation ≈ **$0.48** per arm at the shipped rates ($1.00/Mtok input,
$5.00/Mtok output) ⇒ **about $1.44** for three arms. A planning figure, nothing
more.

---

## 4. Validity threats, stated before the result

- 🔴 **The reader is a model, not a human.** This isolates the definition text
  under a fixed reader. It does **not** establish what a human reading MAST's
  wording would mark, and it is therefore **not a substitute for the third
  labeller** in `FM_2_3_DERAILMENT_TRAIL_PREREG.md` §14. A Q2 result of ≥ 7 says
  our exclusions suppress the count *for this reader*; the human version of (b)
  stays open and the seed-59 sheet stays available.
- **The arms differ in length and specificity, not only in content.** Arm A is
  longer and carries explicit exclusions; Arm B is one sentence. That asymmetry
  is **the hypothesis**, not a confound to be removed: the claim under test is
  precisely that A's exclusions narrow B. Equalising length would mean rewriting
  one of the two definitions, and then neither arm would be the thing it is named
  after.
- **Order and state.** Calls are independent, temperature 0, no conversation
  carried between traces or arms. Arm order is A, B, C and is irrelevant for that
  reason; it is fixed anyway so the run is reproducible.
- **The same 39, including the one ingest failure's absence.** `swe_bench_011`
  stays excluded, as in the hand labels. It is TRAIL-negative.
- **Truncation.** Three of the 39 views exceed the cap and are cut with the
  shipped notice (§11.3): `gaia_037` (234,928 chars), `gaia_048` (306,539),
  `gaia_080` (249,099). The hand labels were made from the same reduced material,
  so the comparison is like-for-like, and 120,000 characters is what ships.
  🔴 **But `gaia_037` is the one trace the §16 coding returned as a genuine
  redirection, and only about half of it is visible to any arm.** If the evidence
  for a deviation sits past the cut, no arm can find it, and all three arms
  understate by the same unknown amount. This bounds Q2 downward: a low
  `N_B - N_A` is weaker evidence against (b) than a high one is for it.

---

## 5. What each outcome licenses

**Q2 ≥ 7 — (b) supported.** The negative results already published do not change
their counts, but their interpretation does: *the 0–1 of 39 reflects a line
narrower than MAST's wording.* The licensed next step is a **relabel under a new
pre-registration**, and the four axes stopped for want of a positive class are
re-examined in the same way — one arm each, same instrument. 🔴 Nothing is
retroactively edited; `FM_2_3_DERAILMENT_TRAIL_RESULTS.md` gains a pointer, not a
revision.

**Q2 ≤ 3 — (b) weakened.** Our line and MAST's wording behave alike under a fixed
reader. The 0–1 of 39 then stands as a statement about **MAST FM-2.3 on this
corpus** rather than about one labeller's strictness, and the published negative
result's limitation clause can be narrowed — in a documented amendment, with this
run named. The axis stays closed on this corpus.

**Q2 4–6, or Q0 fails.** Reported as inconclusive. No interpretation of the
published negative result changes, and the human third labeller becomes the
remaining route.

**In every case:** P2 stands at 0–1 of 39, FM-2.3 ships nothing, and the target
category in `FM_2_3_DERAILMENT_TRAIL_PREREG.md` §2 is unchanged.

---

## 6. Order of work

1. This document is committed and pushed **before the prompt file is written**.
2. The three prompts are written — one scaffold, three definition strings — and
   committed as a diagnostic, uncommitted per the standing rule.
3. A dry-run on **2 traces per arm** (6 calls) checks the parse shape and that
   cost is non-zero. Its counts are **not** read as evidence.
4. The full run: 117 calls. Costs recorded per arm.
5. The billing guard in §3 is checked **before** any count is looked at.
6. Q0 first, then Q1, then Q2. Results written to
   `docs/FM_2_3_DEFINITION_AB_RESULTS.md`.

---

## 7. What is explicitly NOT changed

- **No `src/` change.** Nothing here ships, and the shipped verification axis is
  untouched.
- **P2 stands at 0–1 of 39** and the published negative result's counts are final.
- **§14's seed-59 sheet is not withdrawn.** It remains the only instrument for the
  human form of (b), and a Q2 result does not replace it.
- The target category, the unit, the sample, the model pin, the view builder and
  the 120,000-character cap are the shipped ones and are not tuned here.
- TRAIL's no-redistribution gate holds: no trace content is committed.
