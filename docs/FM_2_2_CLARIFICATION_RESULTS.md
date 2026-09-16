# Results: FM-2.2 has no positive class here, and the follow-up corpus does not exist

Scores `FM_2_2_CLARIFICATION_PREREG.md`, including its §8.5 and §8.6
amendments. Labels and P1/P2 were scored 2026-09-10. The external-corpus
follow-up that §7 prescribes was then measured, 2026-09-15, and is reported
here because it changes what the negative result says.

**P2 missed: 1 positive in 40 hand-labelled candidates against a floor of 8 —
3 if both BORDERLINE drafts are counted as positive. The judge was never
called, so P3–P7 are not scored: not failed, not run.**

**P1 cleared 0.80 and the pass carries no information.** The labeller marked
all 15 NEG, so an instrument that marks everything NEG scores the same 0.8667.
§8.6 predicted this shape five days before the marks arrived.

---

## 0. What was scored

| # | prediction | result | |
|---|---|---|---|
| P1 | user–draft agreement ≥ 0.80 on the blind 15 | **0.8667** (13/15), identical to the all-NEG baseline | PASS, uninformative |
| P2 | ≥ **8 of 40** candidates hand-labelled positive | **1** strict / **3** counting BORDERLINE | **MISS → stop** |
| P3 | judge precision ≥ 0.70 | not run | — |
| P4 | judge recall ≥ 0.60 | not run | — |
| P5 | flag-rate gap ≥ +20 pp | not run | — |
| P6 | 0 hallucinated evidence | not run | — |
| P7 | parse failures ≤ 2 of 80 | not run | — |

**No judge call was made, and no key was charged.** §8 step 3 puts P1 and P2
before the judge precisely so that an axis with nothing to measure stops before
it costs anything.

Provenance. The draw, the labels and the scoring are diagnostics and stay
uncommitted, by the standing rule that diagnostics carry raw output and not
conclusions:

| artifact | what it fixes |
|---|---|
| `_fm22_draw.RESULTS.json` | the sample. seed `20260903`, corpus manifest sha256 `0c187af84b6dab1b…`, 84 sessions in frame |
| `_fm22_labels_drafted.json` | the 40 draft labels, frozen **before** the blind set was handed over |
| `_fm22_blind15.md` | the sheet the labeller marked |
| `_fm22_p1_scoring.RESULTS.json` | the P1 scoring, per item |
| `_fm22_hal_feasibility.RESULTS.json` | the HAL rows of §4 |
| `_fm22_mast_human_clarification.RESULTS.json` | the MAST row of §4, recounted 2026-09-16 |

The population drawn from is **616** candidates in the close-rule frame that
§8.5 fixed, not the **618** of §3, which was counted on the pre-amendment
frame. The draw records `population_matches_amendment: true`, so the number it
drew from is the number the amendment predicted.

## 1. P1 passed, and that is the least useful thing in this document

| | |
|---|---|
| agreement, all 15, draft BORDERLINE counted as disagreement | **13/15 = 0.8667** |
| agreement, draft BORDERLINE excluded | **13/14 = 0.9286** |
| `?` marks used by the labeller | **0** ⇒ §8.6's P1(a) and P1(b) coincide |
| disagreements | `C24` (draft POS / user NEG), `C31` (draft BORDERLINE / user NEG) |
| all-NEG baseline | **0.8667** |

Both readings are reported together because §8.6 fixed the handling of a `?`
on the **user's** side and left the handling of a BORDERLINE on the **draft**
side undefined. Neither reading is chosen here after the fact.

🔴 **The score equals the baseline.** §8.6, written 2026-09-05 with the sheet
empty: *"If the second one is common, P1 can clear 0.80 while measuring
nothing."* It was. The number may not be quoted as evidence that two people
applied the same criterion; it is consistent with them applying no criterion at
all.

The `?` mark that §8.6 introduced was available and went unused. During
marking the labeller said the material did not let them decide, had the `?`
rule explained, and chose to keep NEG. That choice is the reason this section
reads the pass as uninformative rather than as agreement.

## 2. P2 missed, and the miss is the result

Forty candidates, hand-labelled before the blind set was handed over:

| label | n |
|---|---:|
| POS | **1** (`C24`) |
| BORDERLINE | **2** (`C14`, `C31`) |
| NEG | 37 |

Against a floor of 8, the miss holds under either counting. The single POS is
*"좋아 크기만 좀 줄여줘"* — no amount is given, and the agent picked one. That
is the whole positive class.

**The cause §7 names is visible in the labels.** In 5 of the 40 candidates the
agent sought input without using an ask surface — it proposed and waited, or
offered options in prose (`C06`, `C23`, `C26`, `C29`, `C34`, recorded in the
label file as `agent_actually_sought_input_despite_no_ask`). The corpus-level
rate points the same way: **144 of 1,777 user-authored turns are stop-and-ask
(8.1%), across 45 of 85 sessions**. This repository instructs the agent to ask
when unsure, and it does.

Under §7 the consequences are fixed and are not re-decided here: publish as a
negative result about this corpus, name the instruction-to-ask, and **do not
widen the candidate rule to find positives**. The 40 drafts stay frozen. No
turn was relabelled after the blind marks arrived.

## 3. The validity threat §4 promised to check, checked

§4 warned that part of "did not ask" could be tooling rather than choice, since
`AskUserQuestion` did not exist in older sessions, and required the draw to
record per turn whether the tool appears anywhere in that session. It does, and
the drawn 40 split 20/20. Crossed against the labels:

| | tool available in session | not available |
|---|---:|---:|
| POS | 1 | 0 |
| BORDERLINE | 1 | 1 |
| NEG | 18 | 19 |

**The empty positive class is not an artifact of a missing ask surface.** The
positive rate is 2/20 where the tool existed and 1/20 where it did not. This is
not a test — twenty is far too few — but it is the check §4 said would be
performed rather than assumed away, and it points away from the tooling
explanation, not toward it.

## 4. 🔴 §7's follow-up is closed: four external candidates, four failures

§7 sends this axis to an external corpus. That instruction was carried out and
the destination does not exist. Every row below was checked against the dataset
itself rather than against its paper, and the MAST and HAL rows are counts over
the data:

| corpus | what it has | why FM-2.2 cannot be scored on it |
|---|---|---|
| `mcemri/MAST-Data` (CC-BY-4.0) | human labels: **19 rows** | clarification-axis majority-positive: **5 of 19**, below the floor of 8 before a single label of ours is written. All five sit in Round 3; Round 1, Round 2 and the final "Generalizability" taxonomy have **0**, and the axis is coded `1.4` in Round 1 and `2.2` afterwards with the wording changing under it. Trajectories are text blocks with no tool or token structure |
| `magicgh/Ask-before-Plan` (CC-BY-4.0) | incomplete requests, by the thousand | the incompleteness is **planted by design**, so a positive rate there measures how the benchmark was built. Our own precedent for that confusion is FM-3.1: **37/1017 on the benchmark corpus against 0/85 on real sessions** (`FM_1_1_TURN_ADHERENCE_RESULTS.md` §5) |
| `allenai/WildChat-1M` (ODC-BY) | real people, incomplete requests | no tool calls and no cost, so the candidate rule's third clause selects nothing and the corpus is not what the product reads |
| HAL traces | spans, cost, tokens, real multi-turn users | **three independent blockers**, below |

The MAST figure was recounted from the cached `MAD_human_labelled_dataset.json`
while writing this document rather than carried over from the survey — majority
of three annotators, per row, matched on the failure-mode text because the axis
code moves between rounds (`_fm22_mast_human_clarification.py`). The HAL figures
are the run outputs named in §0.

HAL was the first-ranked candidate on 2026-09-10 and was rejected on
2026-09-15 after being decrypted and read. Each of these alone is sufficient:

1. **The user is instructed to withhold.** `taubench_airline`: **50 of 50**
   tasks carry *"Do not give away all the instruction at once."*
   `colbench_backend_programming`: **998 of 998** carry *"make use of the
   following hidden information."* Positives are guaranteed by construction,
   which is the same defect as the row above it and not a lesser version of it:
   the withholding is in the prompt, not in the person.
2. **The user is not a person.** τ-bench: **778 of 1,414** spans are a
   `gpt-4o` simulator. colbench: **3,120 of 7,240**. FM-2.2 asks whether a
   *person's* request was incomplete.
3. **The remaining runs have no user turns at all.** `assistantbench`:
   simulator spans **0**, and of its 188 `role=user` messages the 41 under 50
   characters are **one distinct string** — `"Now proceed and carry out this
   plan."` The candidate rule would return 41 candidates containing zero user
   requests.

The generator itself also fails there: colbench has **8 turns under 50
characters out of 5,120** (0.2%), and **0 of 1,000** opening turns, with an
opening-turn median of 1,310 characters.

⇒ **The negative result is larger than the one §7 anticipated.** Not *"our
corpus is a hard negative"* but *"this axis has no ground truth in public
corpora"*, and the reason is structural: **a benchmark that scores asking has
to plant incompleteness in order to score it.** A corpus that contains natural
clarification failures and a corpus that grades clarification are close to
disjoint by construction.

🔴 **This rejects HAL for FM-2.2 only.** Its cost and token structure are
intact (21,730 rollouts, 2.5B tokens; the one τ-bench run read here reports
`total_cost = 69.782865` over 1,414 spans and 50 episodes) and it remains a
first-rank candidate for the cost axes. Its licence is unstated on the dataset
card, which blocks publishing figures from it and is not resolved by this
document.

## 5. What this does and does not say

**It does not say agents rarely fail to ask.** Three narrowings, all of them
chosen before the result and all pushing the count the same way:

1. **The corpus is our own sessions**, and the agent's asking behaviour was
   shaped by this repository's own instruction to ask when unsure (§4). The
   8.1% ask-rate is not a population estimate for anyone else and is not
   published as one.
2. **The candidate rule is a generator, not the definition.** A request over 50
   characters that omits the one fact that matters was never read.
3. **A single labeller's judgement**, with the second labeller's marks
   uninformative for the reason in §1.

**It does say the axis cannot be measured on this corpus**, and — added by §4
of this document — **that the escape route §7 named is not available.** That is
the decision the pre-registration existed to reach.

## 6. What happens next

- **FM-2.2 is closed**, not paused. Reopening it requires a corpus with
  naturally occurring incomplete requests and real users, which no candidate
  examined here supplies. Finding one is a new pre-registration, not a
  continuation of this one.
- **The prompt is not rewritten.** §7: after a miss the next move is a
  different corpus, not a different prompt. There was no judge call to have a
  prompt in.
- **The shipped surface is unchanged.** No detector, threshold, view, renderer,
  privacy statement or published figure moves because of this document. §5 of
  the pre-registration listed what this axis was never allowed to touch, and
  the list is intact.
- **The division of labour it established stands.** Forty draft labels by the
  engine, fifteen blind marks by the auditor, and the axis stopped at the gate
  that costs the auditor least. §0 of the pre-registration stopped FM-1.5 the
  same way and earlier still — **0 candidates in 88 sessions**, before a sheet
  existed to hand anyone.
