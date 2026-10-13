# Result — TRAIL's `Resource Abuse` counts the waste axis we ship; `Context Handling Failure` counts loss, not resend

Rule: `TRAIL_CANDIDATE_MAPPING_PREREG.md`, merged as **`b8f6ce8`** before any
rationale was read. All **104** records coded in one pass, no sampling, **no judge
call, no cost**. Snapshot `b424ce63d5973d5dcd7169b1bc3c07ccdee276d1`.

## 0. The two verdicts, and the one that was not expected

| | n | primary | gate | verdict |
|---|---:|---:|---|---|
| `Resource Abuse` → our shipped waste axis (**D**) | 57 | **D = 30 / 57 = 0.5263** | ≥ 0.40 **and** ≥ 23 records | ✅ **passes both** |
| `Context Handling Failure` → `context_resend` (**R**) | 47 | **R = 3 / 47 = 0.0638** | ≥ 0.40 | ❌ fails |
| `Context Handling Failure` → context loss (**L**) | 47 | **L = 29 / 47 = 0.6170** | ≥ 0.40 | ✅ passes, with a split caveat (§3) |

🔴 **The prediction was wrong, and in the direction that helps us.** §6 predicted
D at 0.15–0.35 with the gate *"predicted to fail"*, because the earlier
`Instruction Non-compliance` coding had found 73 of 156 rationales about printing
too much. That prior was declared in §2 for exactly this reason, and it was wrong:
V came in at 0.3684 and D at 0.5263. **This is not reported as a confirmation of
anything.** It is the first candidate of three whose name matched the construct it
was picked for, and it got there against a written prediction.

🔴 **The pass has one qualifier that has to travel with it everywhere.** Half of
the D pool — **15 of 30** — is a single harness defect: the `page_down` tool,
declared with no parameters, called with `{'': ''}` or `{'': {}}` and retried.
And the detector our public figures actually sit on has **zero** support here:

| D sub-code | detector | n |
|---|---|---:|
| **D1** same tool/query invoked again on the same input | `repeat` | **27** |
| D2 same message content sent again in a later call | `context_resend` | **0** |
| **D3** same resource read again | `redundant_read` | **3** |
| D4 same artifact created again | `duplicate_creation` | **0** |

So the sentence this result licenses is narrow: *TRAIL's `Resource Abuse` is an
external, human-labelled pool for **`repeat`**, half of it concentrated on one
tool-schema defect.* It licenses nothing about `context_resend`, which is where
the public waste dollars are measured.

## 1. `Resource Abuse` — counts (n = 57)

| bucket | n | share |
|---|---:|---:|
| **D** repetition one of the four detectors counts | **30** | **0.5263** |
| **V** volume without repetition | 21 | 0.3684 |
| **X** another construct | 5 | 0.0877 |
| **O** not decidable | 1 | 0.0175 |
| **E** the limit was external | **0** | 0.0000 |

Per split, never pooled: gaia **D 22 / 39 = 0.5641**, swe_bench **D 8 / 18 =
0.4444**. Both clear 0.40, so the splits do not straddle the boundary and the
guard that would have restricted the pool to one split does not fire.

By `impact`: HIGH **D 4** / V 2 / X 2 · MEDIUM D 26 / V 18 / X 3 · LOW V 1 / O 1.

**Guards, all clear:**

- `(O + tie-breaks)` = (1 + 7) / 57 = **0.1404** against the 0.30 cut. Seven
  tie-breaks fired, all counted; six of them were `D | V` and all six were
  decided **against** D.
- Tie-resolved upper bound: **D ≤ 36 / 57 = 0.6316** (0.6491 if the single O is
  also handed to D). Point and upper are on the same side, so the verdict is
  stated rather than left undetermined.
- Strictly-blind subset: **D = 26 / 52 = 0.5000** against 0.5263 over all 57, a
  gap of **0.0263** — inside the 0.10 the prereg allowed. The pass does not
  depend on the 5 partially exposed records.

**Named sensitivity, reported rather than quietly recoded.** Records 67–69 sit in
one trace and carry the identical sentence *"makes the same tool call
repeatedly"* while their own evidence shows **three different URLs**. The rule
says code from the record's own three fields, so they are D1. If all three are
instead treated as ties and pushed to V, **D = 27 / 57 = 0.4737 and the gate
still passes** (27 ≥ 23).

**Who set the standard that was exceeded** (the instrument committed in §3.4):
`labeller` **55**, `harness` **1**, `unclear` **1**, `task` **0**. 🔴 **No record
in this category measures consumption against a budget anyone stated.** The one
`harness` record cites the framework's own *"take care not to repeat previous
errors"* line. This is the same shape the FM-1.1 coding found — the standard
lives with the annotator, not with the task — and it bounds what a precision
study on this pool can claim.

**Top families:** `page_down_args` **17** · `web_search_many_different` 11 ·
`visit_page_repeat` 4 · `code_bug` 4 · `inspect_file_repeat` 2 ·
`same_dir_reinspected` 2 · `interpreter_calls_many` 2.

The broad construct, reported separately as §3.1 required rather than mixed into
D: **(D + V) = 51 / 57 = 0.8947.** Nine of ten records in this category are about
consumption of some kind; the split between them is whether anything repeated.

## 2. `Context Handling Failure` — counts (n = 47)

| bucket | n | share |
|---|---:|---:|
| **L** context lost — earlier information forgotten, dropped, ignored | **29** | **0.6170** |
| O not decidable | 6 | 0.1277 |
| X another construct | 5 | 0.1064 |
| W window or truncation | 4 | 0.0851 |
| **R** context carried or sent again (`context_resend`) | **3** | **0.0638** |

🔴 **All three R records are among the 17 partially exposed ones.** Over the 35
strictly blind records, **R = 0.0000**. The gap (0.0638) is inside the allowed
0.10, so it does not overturn anything — but the only records that matched the
shipped detector are precisely the ones whose span text had been seen under
another tag, and that is stated here rather than left for someone to notice.

**Guards:**

- `(O + tie-breaks)` = (6 + 4) / 47 = **0.2128**, under 0.30. Four tie-breaks,
  three of them `L | X` decided against L.
- Upper bounds: **R ≤ 0.0638** (no tie could go to R) and **L ≤ 32 / 47 =
  0.6809**. Both verdicts are statable.
- Strictly blind: L = 25 / 35 = **0.7143** against 0.6170, gap **0.0973** — inside
  0.10 by 0.0027. 🔴 Thin. The blind reading is the one that counts and it is the
  *higher* one, so L's pass does not rest on exposure.

**🔴 The splits straddle the boundary, which is the case the prereg said to
expect**: gaia **L 21 / 24 = 0.8750** against swe_bench **L 8 / 23 = 0.3478**.
Under §4.3 the usable pool is therefore **gaia's 21 records, not the union's 29**,
and the pooled 0.6170 must not be quoted as the pool size.

**Why swe_bench behaves differently — and it is not about agents.** Its 23 records
are dominated by `final_answer_output_absent` **13** plus `record_cut` **5**: the
rationale says the final answer is missing, or says outright *"this indicates that
there is missing or cut content."* **17 of 23 swe_bench records are about the
captured trace being incomplete**, not about anything the agent did. That is also
why O is 6 here and 0 on gaia: six of those records name no mechanism at all
beyond the absence. The §6 concentration prediction (one pattern ≥ 0.40 of
swe_bench) holds on this family reading, **13 / 23 = 0.5652**; on the strictest
reading — one byte-identical sentence — it is 7 / 23 = 0.3043 and would fail. Both
numbers are given because the grouping rule is a choice.

**Where the record points** (the LOCUS instrument): `act` **33**, `unclear` 11,
`input` **3**. `find_context_resend` lives on the input side only, and the input
side is 3 records.

## 3. 🔴 The same harness defect is tagged under both category names

`page_down_args` is the top family in **both** categories: **17** records inside
`Resource Abuse` (15 of them coded D — the call was repeated — and 2 coded V) and
**8** inside `Context Handling Failure` (7 of them coded L — the error message was
not incorporated — and 1 coded X).
The underlying event is one thing: a tool declared with no parameters, called
with an empty-string key, retried.

This is the third time this corpus has turned out to encode one thing under more
than one category name — after self-adherence showing up behind both
`Goal Deviation` and `Instruction Non-compliance`. It means **category counts are
not disjoint event counts**, and anything downstream that sums across TRAIL
categories is double-counting. Nothing in this project does that today; this is
recorded so nothing starts.

## 4. Every prediction scored, including the ones that failed

### `Resource Abuse`

| prediction | actual | |
|---|---:|---|
| D **0.15 – 0.35**, point 0.25 | **0.5263** | ❌ **miss, above the range** |
| V 0.40 – 0.65, point 0.50 | 0.3684 | ❌ miss, below |
| gate "predicted to fail" | **passes** (0.5263, 30 ≥ 23) | ❌ miss |
| E ≤ 0.15 | 0.0000 | ✅ |
| X ≤ 0.10 | 0.0877 | ✅ |
| O ≤ 0.10 | 0.0175 | ✅ |
| D among the 8 HIGH ≥ 2 | 4 | ✅ |
| BASIS = `labeller` ≥ 0.50 | 0.9649 | ✅ |
| D1 leads and D2 ≤ 3 | D1 27, D2 **0** | ✅ |

The three misses are **one** miss: the declared prior about output volume was
wrong, and it was wrong in the favourable direction.

### `Context Handling Failure`

| prediction | actual | |
|---|---:|---|
| R 0.10 – 0.30, point 0.20 | **0.0638** | ❌ miss, below |
| L 0.40 – 0.65, point 0.50 | **0.6170** | ✅ in range |
| W 0.05 – 0.20 | 0.0851 | ✅ |
| X ≤ 0.10 | 0.1064 | ❌ miss, by 0.0064 |
| O ≤ 0.15 | 0.1277 | ✅ |
| LOCUS = `input` ≤ 0.35 | 0.0638 | ✅ |
| one swe_bench pattern ≥ 0.40 | 0.5652 family / 0.3043 strict | ✅ on the family reading |

**5 of 16 predictions missed.**

## 5. What this does and does not license

**Licensed.** `TRAIL`'s `Resource Abuse` is an external, human-labelled pool for
the `repeat` detector: 30 records, 27 of them D1, spread over **23 traces** (the
category's 42 traces are not the pool), gaia and swe_bench both above the bar. Half the pool is one tool-schema defect.

**Not licensed, in these words:**

- 🔴 Nothing about `context_resend`. **D2 = 0.** The public waste-dollar figures
  are measured through that detector, and this pool says nothing about them.
- 🔴 Nothing about **our detectors being right**. These are humans describing a
  kind of event. Whether our code fires on those spans is unmeasured, and TRAIL's
  tool-span density is low (159 tool spans over a 40-trace sample).
- 🔴 No rate transfers. TRAIL's base rates are properties of a label campaign that
  sampled traces, not of any production population, and nothing here re-measures
  our own corpus.
- 🔴 **MAST coverage stays at 2 of 14.** A mapping passing is not an axis passing.
- 🔴 The `Context Handling Failure` name is **not** wrong — it does carry a
  construct (loss, 0.6170 pooled / 0.8750 gaia). What was wrong was *our* assumed
  mapping from that name to `context_resend`. The third-strike clause of §4.2
  therefore does **not** fire, and the "pick a category by name" route is not
  closed — but the failure mode has moved: the name is honest and the mapping we
  hoped for was the invention.

## 6. What the result points at next

Both are pre-registrations, and neither is started here.

1. **Detector-firing study on the `repeat` pool** (follows §4.1). Does
   `find_repeat_candidates` fire on the 30 D spans, and what does it do on the 21
   V spans and the 27 non-D records? It needs its own precision gate, a stated
   position on the 15 `page_down` records, and a size check against TRAIL's low
   tool-span density. This is the first chance to test a **shipped** detector
   against labels we did not write.
2. **A context-loss axis**, on **gaia's 21 records over 19 traces only** (follows §4.2). It must
   carry a name of its own rather than inheriting a MAST number by analogy, and
   it has nothing to do with `context_resend`.

Diagnostics behind every number here are uncommitted
(`_trail_candidate_structure_probe`, `_trail_candidate_blinding_probe`,
`_trail_candidate_dump`, `_trail_candidate_codes`, each with a `.RESULTS.json`).
No TRAIL text is committed — its no-redistribution gate.
