# FM-2.3 definition A/B: results

Executed 2026-10-05 against `FM_2_3_DEFINITION_AB_PREREG.md`, which was merged
first (`08976af`) and whose thresholds were fixed before any call.

**Answer in one line.** Reading **(b)** — *our line is narrower than MAST's own
wording* — is **weakened**: the two written definitions behave alike under a
fixed reader (`N_B − N_A = 1`, against a support threshold of ≥ 7). But the run
also missed its own fidelity check hard, and that **limits what the weakening
licenses**: see §4.

🔴 **No trace content appears in this document.** TRAIL is MIT with
redistribution withheld, and the per-call records — which hold quoted trace text
— stay in the uncommitted diagnostic.

---

## 1. The billing guard, before any count (§3, §6 step 5)

| | |
|---|---:|
| calls, this run | **117** (3 arms × 39) |
| calls, cumulative incl. the 6-call dry run | **123** (abort above 125) |
| **recorded** spend, this run | **$1.320141** |
| recorded spend, cumulative | $1.356057 (ceiling $5.00) |
| planning figure in §3, for comparison | $1.44 |

| §3 assertion | result |
|---|---|
| aggregate cost > 0 | **yes** |
| per-arm cost > 0 | **yes** — A $0.441889 · B $0.438839 · C $0.439413 |
| per-call cost > 0 for ≥ 37 of 39, each arm | **yes — 39 of 39 in all three arms** |

The guard passes, so the counts below are a measurement and not a key failure.
The recorded figure is reported, as §3 requires; the $1.44 is named only so the
planning estimate can be scored (it was 9% high).

---

## 2. The counts

Model `claude-haiku-4-5`, temperature 0.0, `max_tokens` 256, view builder
`render_trace_for_judge`, 120,000-character cap with the shipped notice, the
same 39 traces the hand labels were made on, `swe_bench_011` excluded. One call
per trace per arm, no retries on content, no re-prompting. The scaffold is one
function and the arms are three strings handed to it, so the only difference
between arms is the definition sentence.

| arm | definition | positives / 39 | §2.1 expectation |
|---|---|---:|---|
| **A** | our §13.2 line | **19** | 0–2 |
| **B** | MAST FM-2.3 verbatim | **20** | not predicted, by design |
| **C** | §13.3 operational line (control) | **29** | 20–30 (human count 26) |

Hand labels on the same 39: **0** strict, **1** counting the single BORDERLINE.

Parse failures are counted as not-positive, the mechanical default; the
pre-registration does not specify a treatment. Over parsed-only denominators
the counts are A 19/37, B 20/36, C 29/37, which moves no threshold.

### 2.1 Q0 — the control, read first

**`N_C = 29 ≥ 18`. Passes.** The instrument tracks definition text on this
corpus, and it lands inside the band §2.1 fixed from the human count of 26. Q2
is therefore readable, and the run is not reported as uninterpretable.

### 2.2 Q1 — fidelity. 🔴 Missed, and not narrowly

**`N_A = 19`, against a pass threshold of ≤ 4.** 19 is past the `≥ 10` mark that
§2 reserved for a specific finding, in its own words: *the written line does not
reproduce the labels it supposedly produced.*

It is worth being exact about what fails here. The line in §13.2 was written by
the same person who labelled these 39 traces 0–1 positive. Handed to a fixed
reader, that same written line returns 19. So the sentence does not encode the
standard its author actually applied.

**The mechanism is visible in the evidence field.** Arm A's own text excludes a
wrong answer, a fabricated answer, a skipped verification, a tool error and a
format violation. **10 of the 19 arm-A positives rest on exactly those excluded
categories** — the reader read the definition's inclusion clause and did not
apply its exclusions. (Counted by pattern over the evidence strings; the
patterns and the strings are in the diagnostic.)

🔴 Per §2, this does not void the run. It changes what Q2 measures: **Q2 now
compares two written lines, not the labeller's actual standard.** §2 fixed that
reading before the run, and §4 is written against it rather than around it.

### 2.3 Q2 — the test

**`N_B − N_A = 20 − 19 = 1`.** The thresholds, fixed before the run: ≥ 7 → (b)
supported · ≤ 3 → **(b) weakened** · 4–6 → inconclusive.

**(b) is weakened.** The two definitions agree on 17 of the 22 traces either one
flags; arm A alone flags 2 (both `swe_bench`), arm B alone flags 3 (all `gaia`).
Under a fixed reader, our exclusion-laden sentence and MAST's one-sentence
wording do not behave differently.

### 2.4 Q3 — hallucinated evidence. 0 in every arm, and the first check was wrong

**0 findings per arm whose quoted evidence is absent from the view. No arm is
voided.**

🔴 **The first check said the opposite and it was broken.** The runner asked
whether the *whole* evidence string is a substring of the view. The judge
answers in narrative with short quotes embedded, so that test failed **68 of
68** positives — a result that, read mechanically, would have voided all three
arms and taken Q0 down with Arm C, reporting the run as uninterpretable.

A check that fails everything is a check, not a finding. Recorded here because
the mechanical output was sitting there ready to be believed:

1. **Whole-string substring** → 68 of 68 "absent". Broken: narrative is not a
   quote.
2. **Fragments between quote marks** → 74 of 193 "absent". Still broken: a
   possessive apostrophe opens a run that closes on the next real quote, so the
   regex returned prose nobody had quoted.
3. **Fragments with word-boundary guards on the single-quote form** → 19 of 141
   "absent". Small enough to read by hand.
4. **Hand-read, all 19.** Every one is explained by quoting mechanics: an
   ellipsis inside the quote, a re-wrap, or the model quoting the definition
   sentence back at us. **Each distinctive phrase was then located in the view
   directly — all present.**

So Q3 is 0, and the number that would have voided the run was an artefact of
three successive versions of our own test.

### 2.5 Q4 — parse failures. Arm B over the limit

| arm | parse failures / 39 |
|---|---:|
| A | 2 |
| **B** | **3** |
| C | 2 |

The limit is 2 per arm, so **arm B misses**. §2's column for Q4 is *reported
with the cost*, not a void, and it is reported here.

**Likely cause, named rather than fixed:** the evidence strings are cut
mid-sentence, and `max_tokens` is 256. A JSON object cut before its closing
brace is a parse failure. 256 is the value §1.1 fixed (`anthropic_client`, the
shipped semantic-duplicate default); the shipped verification axis uses **512**
(`src/clew/detect/llm_judge/verification_judge.py:234`). The pre-registered
value was used, and the tradeoff is recorded rather than resolved after the
fact — raising it after seeing counts is what §1.1 forbids.

---

## 3. What was observed that the prereg did not predict

- **Arm C reproduces a human count; arm A does not.** 29 against the human 26 on
  the same line and traces, versus 19 against the human 0–1 on §13.2. The
  reader is faithful to an operational one-clause line and unfaithful to an
  exclusion-laden one. Nothing in the pre-registration anticipated that split.
- 🔴 **The three truncation figures in §4 are stale.** They were measured at
  `0a355e9` (2026-09-28 23:04) and `085a09b` — the fix that stopped the
  OpenInference adapter dropping TOOL spans — landed **19 minutes later**
  (23:23). Measured today: `gaia_037` **237,465** (§4 says 234,928),
  `gaia_048` **306,948** (306,539), `gaia_080` **250,781** (249,099).
  **The set of three traces is unchanged**, which is what §4's like-for-like
  argument rests on, and the hand labels were made from the post-fix sheet, so
  the comparison holds. Only the three char counts were never re-measured.
  The earlier prereg's §12.1 said the views grew by *"a few hundred characters
  each"*; that is right for `gaia_048` (+409) and understates the other two
  (+2,537 and +1,682).
- **The planning figure was 9% high** — $1.44 against a recorded $1.320141.

---

## 4. What this licenses, and what it does not

§5 of the pre-registration assigned Q2 ≤ 3 the following: the 0–1 of 39 *"stands
as a statement about MAST FM-2.3 on this corpus rather than about one labeller's
strictness"*, and the published negative result's limitation clause *"can be
narrowed — in a documented amendment, with this run named."*

🔴 **Q1's miss blocks the first half of that.** We cannot conclude the 0–1 is a
statement about MAST FM-2.3 rather than about the labeller, because arm A — the
labeller's own written line, read by a fixed reader — returned 19 where the
labeller returned 0–1. The divergence this run actually exhibits is **not**
between the two written definitions. It is between a written definition and the
person who wrote it.

So the narrowing that is licensed is smaller than §5's sentence:

**Licensed.** The published negative result may record that, under a fixed
reader on these 39 traces, MAST FM-2.3's own wording and our §13.2 line produce
the same count to within 1 of 39. The specific worry that *our exclusions
suppress the count relative to MAST's wording* is weakened for this reader.

**Not licensed.** Any claim that the 0–1 of 39 is therefore about the corpus
rather than about one labeller's strictness. Q1 points the other way, and the
third reading now visible — **the labeller's actual standard is captured by
neither written sentence** — was not tested by this run and is not asserted by
it.

**Unchanged.** P2 stands at 0–1 of 39. FM-2.3 ships nothing; no `src/` change is
authorised by this run and none was made. The target category, the unit, the
sample, the model pin, the view builder and the 120,000-character cap are the
shipped ones. §14's seed-59 sheet is **not** withdrawn: §4's first validity
threat said this run is not a substitute for the human third labeller, and
Q1's miss makes that threat the operative one rather than a formality — the
human form of (b) is now the *more* interesting question, not the less.

---

## 5. Reproducing it

The runner, the corrected Q3 check and the per-call records are uncommitted
diagnostics under `field_test/diagnostics/`
(`_fm23_definition_ab.py`, `_fm23_definition_ab_q3.py`,
`_fm23_definition_ab.RESULTS.json`, `_fm23_definition_ab.LEDGER.json`), per the
standing rule that diagnostics are not committed. Here that rule is also the
redistribution gate: the records hold quoted TRAIL trace text.

The runner re-reads the three definitions out of the pre-registration and
refuses to run if either copy has drifted, so the arms cannot silently stop
being the sentences they are named after.
