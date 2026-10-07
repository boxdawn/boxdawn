# usage attribution decision — Claude Code adapter

> Status: **decided as (A) (2026-10-07). Implemented and measured** → §9.
> If a threshold appears, it splits out into a pre-registration.
> Why this document: on 2026-10-07 the published denominator was confirmed
> **1.523x over**, and only the denominator was settled. **The numerator and
> the ratio cannot be computed until "how one API call's usage is attributed
> to its sub-calls" is decided** — that is the question this document asked.
> Depends on: `STAGE4_AUTOFIX_DESIGN.md` §8 (Stage 4's savings use this path).

## 0. The decision, in one sentence

Is one element of `llm_calls` **one billed API call**, or **one input fed to
detection**? The code uses the same list for both, and on this corpus the two
part ways: **39 vs 27**.

## 1. Mechanism (read from code, 2026-10-07)

The source JSONL writes one API call as **one line per content block**, and
**every one of those lines carries the same usage record**. Pass 1 of the
adapter has a merge guard:

- `src/clew/ingest/claude_code.py:251-257` — extends `content` when
  `current_asst.get("message_id") == mid` (`# Same API call, next content block`).
- But `:238` — `etype == "user"` hits `_flush_current()` first.

⇒ A single intervening `user` tool_result line empties `current_asst`, and
**the next block of the same `message.id` starts as a new call carrying a full
copy of the usage.** It fires on parallel/sequential tool-use shapes.

Measured (`msg_01MwTSZsxhZnFzS2DHbWoe7k`, all 6 lines `in 6 / read 36,177 /
write 6,629 / out 1,224`): `assistant[thinking] assistant[text]
assistant[tool_use]` → call 1 / `user[tool_result]` → flush /
`assistant[tool_use]` → **call 2** / … ⇒ **one API call became 4 `llm_calls`.**

🔴 **`message.id` is the deciding field.** The duplicate calls have *different*
`input_text` (the conversation grows), so judging "separate call" from the
differing input is wrong.

### How far it spreads (all consumers)

| Consumer | Code | What duplication does |
|---|---|---|
| denominator (cost) | `metrics/waste_rate.py:134-141` — sums `input_cost_for_call` per call | **adds the full amount per usage copy** |
| denominator (bytes) | `metrics/waste_rate.py:131-132` — sums `input_text` bytes per call | 🔴 **the byte denominator inflates too**, not only cost |
| numerator | `(call, chunk)` flags = `resent_events` | **flag count grows with call count** (`1,720`) |
| the pointing | `report/markdown.py:651-668` — groups by `ev.llm_span_id`, sums cost | **ids with more duplicates rise to the top** |

## 2. Measured impact (2026-10-07)

| | What the adapter counts | Unique `message.id`, 27 | Factor |
|---|---:|---:|---:|
| cache_read | 2,097,279 | 1,512,529 | 1.39x |
| cache_write | 141,256 | 83,930 | 1.68x |
| output | 23,717 | 15,061 | 1.57x |

| `total_analyzed_cost` | Value |
|---|---|
| current = **published** | **$2.5248795** |
| one charge per API call | **$1.6576570** ← **1.523x over** |
| one charge per API call + TTL 1h | $1.9723945 |

| | calls | resent tokens | total tokens | ratio | chunks |
|---|---|---|---|---|---|
| **current = published** | 39 | 2,056,739 | 2,238,628 | **91.9%** | **1,720** |
| unique, **keep first** | 27 | 1,415,396 | 1,596,520 | 88.7% | 1,231 |
| unique, keep last | 27 | 1,419,156 | 1,596,520 | 88.9% | 1,255 |

★ **The two reconstructions land at 88.655 / 88.891 ⇒ direction and magnitude
are insensitive to which one is picked.**
🔴 These are **defect-size indicators, not shipped behavior.** Dropping the
duplicate calls removes comparison inputs, so **detection differs** — a
behavior change, not an accounting correction.

🔴 **There are three cache-write numbers**: 322,360 (all 72 source lines
summed) / 141,256 (the adapter's 39 calls) / **83,930 (27 unique calls = what
was actually billed)**. Do not compute cost from the first two.

## 3. The three candidates

### (A) `llm_calls` = **one API call** — merge the same `message.id` into one element

| | |
|---|---|
| denominator | ✅ correct by construction (usage counted once per call) |
| numerator / flags | ✅ **no separate attribution rule to invent** — `(call, chunk)` is counted over 27 calls |
| the pointing | ✅ `span_id` becomes 1:1 with `message.id`, so the Top-offenders sum is honest |
| cost | 🔴 **behavior change** — detection input drops 39→27. Needs re-measurement and re-approval |
| implementation | buffer `user` entries in Pass 1, or a post-pass merge over `llm_calls` |

**(A) is the same thing as §2's "unique, keep first" reconstruction** — merging
leaves `input_text` at the state before the first block. So it is **the option
already measured**. And it matches the facts: the real API call happened
**once** with that input, and the intervening tool_result came into being
**after the call returned**.

### (B) Keep 39 calls, **prorate** usage across the blocks

| | |
|---|---|
| denominator | ✅ the total is right |
| numerator / flags | 🔴 **needs its own decision** — a chunk flag is a count, not tokens, so prorating is undefined for it |
| the pointing | ✅ restored if summed by `span_id` |
| cost | 🔴 **no call carries the actually-billed value** — per-call reconciliation against the invoice becomes impossible |
| implementation | you then have to pick a prorating axis (output tokens? even split?) |

### (C) Keep 39 calls, **usage on the first block only, 0 on the rest**

| | |
|---|---|
| denominator | ✅ total right, smallest change |
| numerator / flags | 🔴 **`1,720` stays** (a count scales with call count) |
| the pointing | 🔴 a 0-usage call reads as a free call; per-call rate math gets a zero denominator |
| cost | 🔴 **"39 calls" and "27 charges" coexist inside one report** |

## 4. Recommendation — **(A)**

Three reasons.

1. **The numerator decision follows.** (B) and (C) fix the denominator and
   then still require a *second* decision about the `(call, chunk)` flag
   count. (A) settles numerator, denominator and pointing **at once** by
   fixing the unit. The numerator is exactly what is blocked right now.
2. **A unit that can be reconciled with the invoice survives.**
   `message.id` = number of charges. (B) removes that reference line.
3. **The pointing is where a user picks what to fix.** 3 of the top 5
   replaced (60%) was the strongest reason to hold the live numbers, and (A)
   prevents that shape structurally.

🔴 **(A) is a behavior change, not an accounting correction.** Approving it
drops the detection input 39→27; `91.9%` is retired and a new value comes from
re-measurement. **Not "the same number gets more accurate" but "a different
number comes out."**

## 5. Guards required if (A) is taken (so a defect cannot pass everything)

Lesson from 2026-10-06: when undecidability is quietly absorbed to one side, a
guard passes at `0.0000`. ⇒ **Count how often the merge fired and how often the
billed line was undecidable, and report both.**

- `api_call_merge_count` — calls removed by merging (this corpus: **39 → 27 = 12**)
- `usage_conflict_count` — ids where the repeated usage records **disagree**
  🔴 **It must be 0.** If it is not, which line holds the charge is undecided,
  so **do not quietly take the first one** — surface the count in the report.

**Measured on this corpus (2026-10-07, reading the source JSONL directly):**

| | Value |
|---|---:|
| assistant lines | **72** |
| unique `message.id` | **27** (0 lines without an id) |
| current adapter `llm_calls` | **39** |
| `api_call_merge_count` | **12** |
| `usage_conflict_count` | **0** |

★ `usage_conflict_count = 0` is **a counted value, not a check that never
ran** — all 27 ids were walked and the number of distinct
(`input_tokens`, `cache_read`, `cache_creation`, `output_tokens`) combinations
was counted per id; every id had exactly one. ⇒ **"which line do we pick" is a
non-question on this corpus.** It has to be recounted on any other corpus.
🔴 **Passing everything is also the shape of a bug** — which is why this value
stays a permanently emitted field.

🔴 **Do not fix this with a heuristic.** `cost/amplification.py:66-72`'s
`_prev_equals_next` filters repeated usage by comparing two cache fields —
**that knowledge is already in the repo**, but it is an inference where
`message.id` is ground truth. Patching this defect with `_prev_equals_next`
would wrongly erase two genuinely distinct calls that happen to share usage.

🔴 **(A) does not fix the amplification path** (corrected by measurement on
2026-10-07 — this section first claimed "the aggregate moves in the same PR",
which was **wrong**). `_collect_cc_usage_metadata` never looks at `llm_calls`;
it walks the **raw `entries`**. After the fix:

| | Value |
|---|---:|
| `cc_total_turns` | **72** ← assistant **lines**. API calls are 27 |
| `cc_usage_pair` | 45 |
| `prev==next` skips | 21 / 45 = **46.7%** |
| `llm_calls` (fixed) | 27 |

⇒ **The same replication defect sits there untouched.** `cc_total_turns`
counts **content-block lines** under the name "turns", and `prev==next` is
filtering out adjacent lines with equal usage (i.e. copies of one call) —
suppressing the symptom without naming the cause. **Handled separately** (§9.5).

## 6. Out of scope — what this document does **not** decide

- **TTL 1h unread** (the source's
  `usage.cache_creation.ephemeral_1h_input_tokens` is never read).
  **Separate defect, direction is under-counting.** Re-measured 2026-10-07:
  lines carrying the `cache_creation` sub-object **72/72**, `ephemeral_1h`
  total **322,360**, `ephemeral_5m` total **0**.
  🔴 That `322,360` is the **sum over all 72 lines (duplicates included)** —
  on 27 unique calls the actually-billed write is **83,930**. The two defects
  **overlap on the same field**, so fixing TTL first inflates that amount by
  the duplication again. ⇒ **(A) comes before the TTL fix.**
- **Blended distribution rate** (resent share carries cache_write weight,
  1.6193x the cache-read floor). **Separate defect, direction is
  over-counting.**
- Live-number replacement copy (web's scope) and prohibited-phrase updates
  (marketing's scope).

🔴 **The three defects do not point the same way**: duplication **over**, TTL
**under**, blended rate **over**. They partially cancel, which is why the
total never looked wrong. **Do not describe them as having one direction.**
🔴 When quoting a factor, name the denominator: fixing duplication alone is
**1.523x**; fixing duplication and TTL together is **1.280x**.

## 7. Order (recommended)

1. ✅ **Decide (A)/(B)/(C)** — decided as (A) (2026-10-07) → §9
2. ✅ **Adapter fix + the two §5 guards + `usage_conflict_count = 0` measured** → §9.1-9.2
3. 🔴 **Re-measure the whole corpus** — retire the `91.9%` family, produce new
   values. **Put the unit in the name** (API call count / reconstructed call
   count / `(call, chunk)` flag count / tokens and dollars — on 2026-10-07
   three engine statements and one marketing statement were wrong from this
   one cause)
4. TTL and blended rate, each as its own change
5. Notify about the replaced public numbers (web, marketing)

🔴 **This defect happened with `cost_accuracy_flag = "accurate"`** — a wrong
number and an "accurate" label stand together in production. That flag only
looks at **whether the tier fields are present**. Do not cite `accurate` as
evidence of accuracy.

## 8. Reproduction

- Adapter path: the Claude Code adapter **does not go through
  `preprocess_trace`** (it builds `llm_calls` directly; sending it through
  takes `llm_calls` from 39 to 0).
- Trace: `data/hf_agent_traces/agent-race/claude-code.jsonl`
  (`trace_id = 7f309fce-093f-412d-be64-cbd2860481f3`, model `claude-opus-4-7`).
  🔴 **This is the same trace behind the `91.9%` on the home page and in the
  cited report** — nothing else needs to be obtained.
- 🔴 Grouping by `span_id` double-counts (39 calls but 27 `span_id`s).
  **Sum per event.**

---

## 9. Decision, implementation, measurement (2026-10-07)

**Decision: (A).** One element of `llm_calls` = **one billed API call**.

### 9.1 Implementation

Pass 1 of `src/clew/ingest/claude_code.py` now merges **by id instead of by
adjacency**. The group keeps its position in `sequence`, so the `input_text`
Pass 2 snapshots is the state **before that call's first block** — the input
the API actually saw, with the intervening tool_result being something that
happened after the call returned (= the "unique, keep first" row in §2).

🔴 **This is what the adapter had already promised in writing.** The first
line of the `_extract_llm_calls` docstring reads *"one entry per unique
Anthropic API call (identified by `message.id`)"* while the implementation
comment said *"consecutive"* — **two sentences disagreed inside the same
docstring** and nobody compared them. At the contract level this is a bug fix.
🔴 **The shipped numbers still change** — do not use "it only did what the
contract said" to cover a change in the numbers.

### 9.2 Guards (§5), measured

| Field | Value | Note |
|---|---:|---|
| `api_call_merge_count` | **12** | 27 + 12 = **39** = the old call count |
| `usage_conflict_count` | **0** | all 27 ids compared |

★ `27 + merge == the old call count` is **a self-check**. The old version was
actually run via `git show HEAD:` to obtain the 39 for comparison.

🔴 **That self-check is what caught a counter bug.** The first implementation
reported `13` against a predicted 12; the cause was not recording a reopened
group as the last-written item, so the third line of
`A(X) → user → A(X) → A(X)` **counted as a second reopen**. The old code
merges that line by adjacency, so it adds no call. **Without writing the
prediction down first, the 13 would have shipped.**

### 9.3 Number changes (cited trace, one run)

| | before (published) | after | |
|---|---:|---:|---|
| `llm_calls` | 39 | **27** | |
| `total_analyzed_cost` | $2.5248795 | **$1.657657** | predicted $1.6576570, **matches** |
| `total_llm_input_cost` | $1.9319545 | **$1.281132** | |
| resent tokens | 2,056,739 | **1,415,467** | |
| total tokens | 2,238,628 | **1,596,520** | matches |
| resent ratio | 91.9% | **88.7%** | |
| resent cost | $1.6652490 | **$1.031040** | |
| `(call, chunk)` flags | 1,720 | **1,050** | 🔴 differs from §2's reconstruction, **1,231** |
| `cost_accuracy_flag` | accurate | accurate | |

🔴 **The reconstruction missed in two places**: chunks **1,231 → actually
1,050** (-181), resent tokens **1,415,396 → actually 1,415,467** (+71). The
ratio 88.7% and the denominator 1,596,520 were right. ⇒ **§2's reconstructions
are defect-size indicators, not predictions** — the document said so, and that
is how it turned out. **Anywhere 1,231 was quoted, correct it to 1,050.**

### 9.4 Top offenders — the pointing really did change

| Rank | before (39 calls) | cost | after (27 calls) | cost |
|---|---|---:|---|---:|
| 1 | `msg_01S2rT` | $0.253172 | **`msg_01S2rT`** | **$0.125574** |
| 2 | `msg_01MwTS` | $0.206537 | `msg_01EgXB` | $0.059813 |
| 3 | `msg_01GmBJ` | $0.138267 | `msg_01T1py` | $0.058984 |
| 4 | `msg_011ZR8` | $0.133689 | `msg_011yRB` | $0.053635 |
| 5 | `msg_01K8ws` | $0.092611 | `msg_01GmBJ` | $0.046411 |

Rank 1 keeps its place at half the money (two duplicates' worth). Ranks 2-4
are all replaced.
🔴 **"ranks 1 and 2 were duplication artifacts" overstates it for rank 1** —
rank 1's position was correct.

### 9.5 What is left

- **TTL 1h unread** and the **blended distribution rate** remain unfixed (§6).
  With duplication now removed, the TTL fix has to be re-measured as well (the
  earlier $1.9723945 estimate was computed **before** dedup).
- 🔴 **The amplification path was not fixed** — `cc_total_turns` is still 72
  after this change (§5). The same replication survives there under the name
  "turn count", with `prev==next` suppressing the symptom. **Separate, open.**
  Do not write that this PR fixed it.
- Notify web and marketing about the replaced public numbers — **`91.9%`,
  `1,720` and `$2.5248795` are retired values.**
