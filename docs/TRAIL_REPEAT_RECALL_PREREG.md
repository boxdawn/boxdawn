# Pre-registration — does the shipped `repeat` detector fire where other people marked waste?

Status: **pre-registration.** No measurement of the outcome has been made. The
pool described in §2 was coded on 2026-10-13 under a separate pre-registration
(`TRAIL_CANDIDATE_MAPPING_PREREG`, merged `b8f6ce8`; results PR `#257`) and is
frozen here by hash before any detector is run against it.

## 0. Why this exists

`find_repeat_candidates` plus the cascade is **shipped**, and every public waste
figure rests on it. It has never been measured against anyone's labels but our
own. The only thing standing in for an evaluation is a precision figure from
synthetic generators and a mapping study that says TRAIL's `Resource Abuse`
category counts the same construct we do (D = 30/57 = 0.5263, both gates
passed).

A mapping passing is not a detector passing. This document is the first attempt
to point the shipped detector at labels written by someone else.

## 1. What is measured, and what is explicitly not

**Measured: recall.** Of the records a human marked, on how many does our
detector fire?

🔴 **Not measured: precision. It is not computable on this corpus, and that is
a property of the corpus, not a choice of convenience.** TRAIL's labels are
"failures the annotators found", not an exhaustive pass over every span. A span
nobody labelled is not thereby a span nobody would label. So when our detector
fires somewhere no label sits, there is no way to tell a false positive from an
unlabelled true one — the denominator precision needs does not exist here.

Writing a precision number from this pool would require treating "unlabelled"
as "negative", which is the one inference the corpus cannot support. §5
publishes what we fire anyway, with that sentence attached.

## 2. The pool, frozen

Thirty records coded **D** ("this is the construct our waste axis counts") out
of the 57 `Resource Abuse` records, on TRAIL revision
`b424ce63d5973d5dcd7169b1bc3c07ccdee276d1`.

| | records | distinct traces | split |
|---|---:|---:|---|
| **D, all** | **30** | **23** | gaia 22 · swe_bench 8 |
| of which family `page_down_args` | **15** | 13 | gaia 15 · swe_bench 0 |
| **D, excluding that family ("clean")** | **15** | **10** | gaia 7 · swe_bench 8 |

Sub-codes within D: **D1 = 27** (the `repeat` axis) and **D3 = 3** (the
`redundant_read` axis). D2 (`context_resend`) and D4 are **0** — the detector
the published waste dollars sit on has no evidence in this pool at all.
26 of the 30 are flagged `strictly_blind` by the blinding probe that ran before
coding.

**2.1 The pool is frozen by hash, not by listing.** TRAIL is MIT with a
redistribution bar on its contents, so the record ids live in an uncommitted
diagnostic (`_trail_repeat_pool.RESULTS.json`) and this document commits their
sha256 instead. Ids are sorted, newline-joined, UTF-8:

| subset | n | sha256 of the id list |
|---|---:|---|
| D, all | 30 | `c045e4b9f5b75a8518f619a9394858dd6ed34e9e6ad402d721851933c2ae91c2` |
| D1 only | 27 | `6cff88326c393e45759e197bc43e45e4803ba6e3ffdaecbdb5df12783d90ae58` |
| clean (no `page_down_args`) | 15 | `4cd787499af0a12c22c37353c00de6c0a1d9871b988d939fcc19d3b65c81637a` |

🔴 **A record may not leave or join the pool after this commit.** If the results
run reports a different n or a different hash, the run is invalid, not the pool.

**2.2 Every record points at a span.** Measured on the same revision:
`location` is present on **57 of 57** records and the 57 records resolve to
**57 distinct spans**. Span-level matching is therefore possible, which is what
§3 rests on.

## 3. The match rule — frozen before the run

A human label names **one span**. Our detector emits **a pair**: the first
occurrence and the re-occurrence. So "we agree with the annotator" needs a rule,
and the rule changes the number.

**3.1 Frozen (the loose rule): a record is a HIT when the labelled span is
*either* member of a pair our detector produced for that trace.**

**3.2 Reported alongside (the strict rule): both members labelled.** This is
reported as a sensitivity line, never as the headline.

🔴 **Why loose is the rule and strict is the sensitivity.** Annotators mark the
*re-occurrence* — the call that should not have happened. The first occurrence is
ordinary work and is typically not marked. A rule demanding both spans be
labelled therefore measures the annotators' convention, and would read near zero
by construction no matter how well the detector worked. Declaring this before
the run is what stops the choice from being made after seeing which number is
kinder.

**3.3 Identity of the span is `span_id`,** compared after `preprocess_trace`
(the ingest path TRAIL goes through). No fuzzy matching, no time-window
matching, no name matching.

## 4. The funnel — a miss must say which stage missed

A single recall number cannot distinguish "the detector does not see this" from
"the trace never reached the detector". Each record is scored at three stages
and **all three counts are reported**:

| stage | question | a miss here means |
|---|---|---|
| **S0** | Is the labelled span present after `preprocess_trace`, with `span_kind == "tool"`? | an ingest/preprocess question, **not** a detector result. LLM spans are collapsed (`collapse_llm_spans`) and router chains filtered, so a label on one of those cannot be matched |
| **S1** | Is that span a member of a `find_repeat_candidates` pair (n = 2)? | the grouping key or `n` — the span was visible and not paired |
| **S2** | Does the pair survive the cascade into a reported finding? | the cascade gate, which for tool spans requires **byte-identical output** (`cascade.py`: tool pairs are sha256-compared and φ is never invoked) |

🔴 S2 is the stage most likely to drop records, and we have a measurement that
says so rather than a hunch: on the 13 gaia tool pairs recovered this week by
removing the SPEC §16 gate, byte-identical output was **0 of 13**, against
**60 of 73** for the pairs already kept.

## 5. The noise number is published

Alongside recall we report **the total number of pairs our detector produced on
the 23 pool traces**, and on the 10 clean-subset traces, including every pair no
label sits on.

🔴 **The sentence that must travel with it, in the results document and in any
later citation:** *this count is not a false-positive count. TRAIL's labels are
not exhaustive, so a pair with no label on it is unverified, not wrong.*
Publishing the number without that sentence overstates a defect; withholding the
number overstates the detector. Decision taken by 세원님 on 2026-10-14:
**publish, with the sentence.**

## 6. Denominators, named

Four denominators exist and a bare "recall" is therefore meaningless. Results
must carry the name:

| metric | denominator | n |
|---|---|---:|
| `R_all` | every D record | 30 |
| `R_D1` | D records coded as the `repeat` axis | 27 |
| `R_clean` | D records outside the `page_down_args` family | 15 |
| `R_clean_D1` | both filters | 12 |

**`R_clean_D1` is the headline.** The other three are reported in full, and
🔴 **`R_all` may not be cited alone**: half the pool is one harness defect
(`page_down` is declared with no parameters, called with `{'': ''}`, and
retried), which is not a duplicate a production agent would make.

## 7. Predictions, written before the implementation exists

Last time I predicted this corpus I was wrong in the favourable direction (D
predicted 0.15–0.35 as a "will miss" and it came in at 0.5263), so the bias to
declare is that I under-predict TRAIL. These are written anyway:

| # | Prediction | What rejects it |
|---|---|---|
| **P1** | S0: at least **26 of 30** labelled spans are present as tool spans after preprocessing | 25 or fewer — see §8's first stop condition |
| **P2** | S1 on `page_down_args` (15): at least **13** are in a candidate pair. Same tool, byte-identical empty arguments, repeated — this is the easiest shape the grouping key can see | 12 or fewer |
| **P3** | `R_clean_D1` (n = 12) at the S2 stage: **4 to 8** | outside that band |
| **P4** | `R_all` at S2 is **higher** than `R_clean` as a share — the harness family is easier for us than real duplicates | `R_clean` share ≥ `R_all` share |
| **P5** | S1 → S2 attrition is the dominant loss: more records are lost at S2 than at S1 | S1 loses more |
| **P6** | D3's three records (the `redundant_read` shape) are **missed by the repeat detector** at S1 or S2 | any of the three reported by `find_repeat_candidates` |
| **P7** | Total pairs produced on the 23 pool traces: **30 to 90** | outside that band |

## 8. Stop conditions, fixed now

- **S0 misses 10 or more of the 30** → stop. The question is then whether our
  ingest carries TRAIL's tool spans, not whether the detector fires. This has
  happened before: tool spans went from 79 to 159 when `#231` fixed an adapter
  defect, and a repeat of that class must not be reported as a detector result.
- **`R_all` is high while `R_clean` is at or near zero** → the result is about
  one harness defect. Report it in those words; do not publish `R_all` as the
  finding.
- **Any record's hash check fails (§2.1)** → the run is invalid.
- **A match requires loosening §3.1** → stop and report the miss. The rule does
  not move after the run.

## 9. Cost

Zero. Every stage is local and deterministic: the TRAIL parquet files are
already on disk, the detector is ours, and **no judge is called** — no
`--llm-judge`, no `--verification`, no API key read. If any stage appears to
need an API call, that is a design error in this document, not a budget request.
