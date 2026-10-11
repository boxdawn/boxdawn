# usage attribution decision — Claude Code adapter

> Status: **decided as (A) (2026-10-07). Implemented and measured** → §9.
> All four defects closed: duplication §9, TTL 1h §10, blended rate §11,
> `cc_total_turns` §12 (2026-10-08). The first three shipped as `0.5.13`;
> 🔴 **§12 has not shipped.** If a threshold appears, it splits out into a
> pre-registration.
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
suppressing the symptom without naming the cause. **Handled separately** — ✅ §12 (2026-10-08).

## 6. Out of scope — what this document does **not** decide

- **TTL 1h unread** — ✅ **fixed 2026-10-08** (§10). Was: the source's
  `usage.cache_creation.ephemeral_1h_input_tokens` is never read.
  **Separate defect, direction was under-counting.** Re-measured 2026-10-07:
  lines carrying the `cache_creation` sub-object **72/72**, `ephemeral_1h`
  total **322,360**, `ephemeral_5m` total **0**.
  🔴 That `322,360` is the **sum over all 72 lines (duplicates included)** —
  on 27 unique calls the actually-billed write is **83,930**. The two defects
  **overlap on the same field**, so fixing TTL first inflates that amount by
  the duplication again. ⇒ **(A) comes before the TTL fix.**
- **Blended distribution rate** — ✅ **fixed 2026-10-08** (§11). Was: the
  resent share carried cache_write weight, 1.6193x the cache-read floor on the
  pre-dedup figure. **Separate defect, direction was over-counting.**
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
4. ✅ TTL and blended rate, each as its own change → §10, §11
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

- **TTL 1h unread** and the **blended distribution rate** — both ✅ fixed
  2026-10-08 (§10, §11). As written on 2026-10-07 they were open, and the TTL
  fix did have to be re-measured after dedup (the earlier $1.9723945 estimate
  was computed **before** dedup — it came out identical anyway, §10.2).
- **The amplification path was not fixed by this change** — `cc_total_turns`
  was still 72 afterwards (§5). The same replication lived on there under the
  name "turn count", with `prev==next` suppressing the symptom.
  Do not write that *this* PR fixed it. ✅ Closed separately on 2026-10-08 (§12).
- Notify web and marketing about the replaced public numbers — **`91.9%`,
  `1,720` and `$2.5248795` are retired values.**


---

## 10. TTL 1h — fixed (2026-10-08)

The source carries the TTL under `usage.cache_creation`
(`ephemeral_1h_input_tokens` / `ephemeral_5m_input_tokens`). The adapter read
only the `cache_creation_input_tokens` total above it and priced all of it at
the 5-minute rate, so `cache_write_1h_per_mtok` sat in the table **with no
call site at all**. Direction was under-counting.

### 10.1 What changed

| | |
|---|---|
| `ingest/claude_code.py` | reads the sub-object; emits `input_tokens_cache_write_1h` next to the existing total |
| `cost/pricing.py` | new `tier_input_cost(...)` — **one** formula for the four tiers |
| `detect/context_resend.py` · `report/_model.py` | both now call it |

★ The tier formula was **copied into two modules**. Adding the 1-hour rate to
each copy would have been a third place for them to drift, so the formula
moved into `pricing.py` and both callers were pointed at it. A test asserts
the detector and the report price the same call identically.

🔴 **Guard: `cache_creation_ttl_mismatch_count`.** When the sub-object's parts
do not add up to the total above them, which part carries the 1-hour rate is
undecided — so that call prices wholly at the 5-minute rate (**the lower, older
answer**) and the count is reported. It is **not** rounded upward into the
expensive tier. Emitted only when non-zero; this corpus measures **0**.
The 1-hour share is also clamped to the write it is part of, so a sub-object
larger than its total cannot invent tokens.

### 10.2 Numbers (cited trace, after both fixes)

| | published (retired) | after dedup only | **after dedup + TTL** |
|---|---:|---:|---:|
| `total_analyzed_cost` | $2.5248795 | $1.657657 | **$1.9723945** |
| `total_llm_input_cost` | $1.9319545 | $1.281132 | **$1.5958695** |
| resent cost | $1.6652490 | $1.031040 | **$1.2417480** |
| resent tokens | 2,056,739 | 1,415,467 | **1,415,467** |
| resent ratio (tokens) | 91.9% | 88.7% | **88.7%** |
| resent / LLM input (cost) | 86.20% | 80.5% | **77.8%** |
| `llm_calls` | 39 | 27 | **27** |

- cache writes: **83,930, all of it 1-hour, 0 at 5m** — so the whole write
  moved from $6.25/Mtok to $10.00/Mtok on `claude-opus-4-7`. Delta
  83,930 × $3.75/Mtok = **+$0.3147**.
- 🔴 **Token counts and the 88.7% did not move** — TTL is a rate, not a
  quantity. Only the dollar rows change. Quoting "the numbers went up" without
  naming which axis repeats the 2026-10-07 mistake.
- ★ $1.9723945 matches, to seven decimals, the pre-fix estimate for
  "one charge per API call + TTL 1h" in §2. Two independent routes to the same
  figure.

### 10.3 Still open

- **Blended distribution rate** — ✅ **fixed 2026-10-08** (§11). The resent
  numerator walked a weighted average (`eff_rate`), so a resent chunk carried
  cache-write weight. Direction was **over**.
- **`cc_total_turns` = 72** for 27 API calls — ✅ **fixed 2026-10-08** (§12).
  🔴 Not shipped.
- 🔴 **Not shipped.** Both fixes are on `main`; the shipping bar is a PyPI
  re-release plus a Modal pin bump, so production still emits the retired
  numbers.

---

## 11. Blended distribution rate — fixed (2026-10-08)

The last of the three defects. Direction: **over-counting**. With it closed,
no known direction is left open on the cited figures.

### 11.1 What was wrong

`detect/context_resend.py::_rate_and_cost_for_call` priced a call tier by
tier and then **collapsed the result into one average rate**:

```python
eff_rate = (total_cost / total) if total > 0 else 0.0   # weighted average
...
resent_cost = resent_toks * eff_rate                    # every chunk, same rate
```

So the tiers were distinguished when the *call* was priced and undistinguished
when the *chunk* was. A resent chunk is content the call already sent, which
is the part of the prompt a cache serves — but the average carried a share of
the cache **write**, the tier that paid for the new content. On
`claude-opus-4-7` the write is $6.25/Mtok at 5-minute TTL and $10.00/Mtok at
one hour, against $0.50/Mtok for a read: a 12.5x to 20x spread folded into one
number.

🔴 The denominator never had this defect — `metrics/waste_rate.py:138` calls
`input_cost_for_call`, which uses `tier_input_cost` directly. **Numerator and
denominator priced the same call by two different rules**, which is what the
first amendment to `WASTE_RATE_METRIC_PREREG` §1.2 existed to stop.

### 11.2 What it does now

`cost/pricing.py::tier_input_ladder` returns the call's four tiers as
`(rate, token capacity)` pairs, and `tier_input_cost` is now defined as the
sum of that ladder — one description of the call, not two. The resend
numerator walks the ladder **cheapest rung first**, carrying over within a
call so two resent chunks cannot both claim the cache-read rate.

**Why cheapest first.** The provider reports how many tokens were billed in
each tier, never which chunk sat in which. Where the split is undecidable this
repository already has a rule, from `cache_creation_ttl_mismatch_count`: price
at the lower rate and surface a count, never round up into the dearer tier.
The mechanically-ordered alternative — cache prefix, then the write, then the
uncached tail, which is how a provider actually partitions a prompt — was
measured on the cited trace and differs by **$0.00004** (the trace bills 61
uncached tokens in total, so the overflow has nowhere to go but the write
either way). The choice is not what moves the number; dropping the average is.

🔴 **`b_all_cache_read` is still not the answer.** Pricing every resent token
at the cache-read rate gives $0.7077335 and passes on the trace total
(1,415,467 resent ≤ 1,512,529 cache read), but **3 of 27 calls resend more
than their own cache read** — the ladder charges that overflow, a flat
cache-read rate would not.

### 11.3 Guard

`resent_tokens_over_tier_capacity` on `ContextResendResult`, surfaced in the
JSON report **only when non-zero** (the adapter guard's convention). It counts
resent tokens that exceeded the sum of their call's tier capacities, which can
only happen if an adapter breaks the ingest invariant
`input_tokens == uncached + cache_read + cache_write`. Those tokens are priced
at the cheapest rung and counted rather than dropped — a dropped token is a
dollar the report never mentions. **On the cited trace: 0.**

### 11.4 Numbers (cited trace, one run)

| | published (retired) | dedup + TTL (`a1317c5`) | **+ ladder** |
|---|---:|---:|---:|
| `total_analyzed_cost` | $2.5248795 | $1.9723945 | **$1.9723945** |
| `total_llm_input_cost` | $1.9319545 | $1.5958695 | **$1.5958695** |
| `total_waste_cost` | $1.6652490 | $1.2417480 | **$0.9015315** |
| `waste_ratio` | 0.659536 | 0.629561 | **0.457075** |
| resent / LLM input (cost) | 86.20% | 77.8% | **56.4916%** |
| resent tokens | 2,056,739 | 1,415,467 | **1,415,467** |
| resent ratio (tokens) | 91.9% | 88.7% | **88.7%** |
| `llm_calls` | 39 | 27 | **27** |

- 🔴 **Only the waste dollar moved.** `total_analyzed_cost` and
  `total_llm_input_cost` are unchanged — this defect was never in the
  denominator. Tokens and the 88.7% are unchanged too: like the TTL, an
  apportionment rate is a rate, not a quantity. Saying "the numbers came down"
  without naming the axis repeats the 2026-10-07 mistake.
- The three defects together: `$1.6652490 → $0.9015315`, a factor of
  **1.847x** on the waste dollar. 🔴 Quoting a factor without naming which
  defects are in it is how the 1.523x / 1.280x pair got misused.
- ★ Two independent routes to $0.9015315: the detector's internal per-event
  ladder walk, and an external recomputation from the report's
  `resent_input_tokens` per call against the tier capacities. They agree to
  fifteen digits.
- **The pointing changed again.** The top offender by cost is now
  `msg_01S2rTDtWwK9s5G15AiHu3Zf` — 32,595 resent tokens for $0.182613 — ahead
  of calls that resend twice as many tokens, because its resent share spills
  into the 1-hour write rung. Under one average rate, cost ordering was token
  ordering; it is not any more.

### 11.5 Out of scope

- **`redundant_read.py:241`** reads the same `eff_rate` and keeps it. Its
  tokens are **counterfactual** — what a read would have added to the next
  call's input had it not been avoided — so there is no tier capacity on the
  call to fill them into. Pricing a hypothetical token by tier is a separate
  question with its own measurement, not a one-line follow-on.
- **`cc_total_turns` = 72** for 27 API calls — ✅ **fixed 2026-10-08** (§12),
  after this change. 🔴 Not shipped.
- 🔴 **Still not shipped.** All three fixes are on `main`; the bar is a PyPI
  re-release plus a Modal pin bump, so production still emits the retired
  numbers and the home page still says 91.9%.

---

## 12. `cc_total_turns` — fixed (2026-10-08)

The replication's last residence. §9.5 left it open; this closes it.

### 12.1 What was wrong

`_collect_cc_usage_metadata` walked the raw `entries` and counted every
`assistant` **line** as a turn. One API call is written as one line per content
block, so on the cited trace that was **72 turns for 27 calls**. Two separate
consequences, and they do not point the same way.

**(a) The turn numbers were line numbers.** `report/markdown.py:356` renders
`turn {origin} → re-run at turn {candidate} (of {total} total)`. Users were
told a total no API ever saw, and the two indices beside it were line indices.
Max turn index on the cited trace: **71**, against 27 calls.

**(b) `next` was the next *line's* usage.** Inside a multi-block call that line
is the same call repeating its own usage copy, so
`cost/amplification.py::_prev_equals_next` read it as duplicate/retry usage and
**discarded the event entirely**. On the cited trace that filter fired on
**21 of 45** pairs (46.7%); after the fix it fires on **0**. Every one of those
21 was an artefact of the grouping, not a retry.

🔴 **The two effects run opposite ways**, so this defect has no single
direction — unlike the other three:

| | effect of the defect |
|---|---|
| `turns_after` per surviving event | **inflated** — Σ 1,590 against 692 after the fix, **2.2977x** |
| events reaching the estimator at all | **suppressed** — 21 of 45 thrown away |

On the cited trace the net dollar effect is **not measurable**: it has
`waste_span_count = 0`, so the amplification estimator has no events to price
either way. Measured instead on a synthetic trace built for the shape (a tool
read repeated inside a multi-block call):

| | before | after |
|---|---:|---:|
| `cc_total_turns` | 8 (lines) | **5** (= `llm_calls`) |
| amplification events | **0** — 1 skipped as `prev == next` | **1** |
| `amp_tokens` | 0 | **2,112** |
| lower / upper | $0 / $0 | **$0.001056 / $0.01056** |

★ **The report was silent, not merely wrong.** Rendering that trace before and
after, the whole amplification passage is what appears:

```
before:  - **turns**: turn 1 -> re-run at turn 2 (of 8 total)
         (no amplification lines at all)

after:   - **turns**: turn 1 -> re-run at turn 2 (of 5 total)
         - **wasted output re-consumed across 3 subsequent turns** in total
           (amplification tokens = 2112)
         - **re-consumed across 3 subsequent turns**
           (~704 tokens/turn -> 2112 amplification tokens)
```

A discarded event produces no line, so the section simply was not there — the
project's recurring shape, where the failure is indistinguishable from a normal
answer.

🔴 So on that shape the figure goes **up**, from nothing to something. ★ This
contradicts the prediction written before the measurement
(`_cc_turns_replication_PREDICTIONS.md` said the amount would fall because
`turns_after` was over). The dominant term was not the inflated multiplier —
it was events being deleted. **Do not describe this fix as a reduction.**

### 12.2 What it does now

Assistant lines are grouped by `message.id` in first-appearance order, the same
rule `_extract_llm_calls` uses (§9.1), and each group is one turn:

- `cc_total_turns` = number of API calls
- `cc_turn_index[tool_use_id]` = 1-based call number
- `cc_usage_pair[tid]["prev"]` = that call's usage, `["next"]` = the **following
  call's** usage

An assistant line with no usable `message.id` is its own group, which is what
`_extract_llm_calls` does with it.

🔴 **Not fixed with `_prev_equals_next`**, per §5: that compares two cache
fields where `message.id` is ground truth, and it would erase two genuinely
distinct calls that happen to share usage.

🔴 **`_prev_equals_next` is left in place.** It now fires 0 times on the cited
trace, but removing a filter moves the aggregate again and is its own decision
with its own measurement — `feedback_intentional_drift`. "Fires 0 here" is not
"inert".

### 12.3 Guard

`cc_total_turns == len(llm_calls)` is asserted by test across three shapes
(single call, one call split across a tool_result, two calls with the second
split). Both numbers claim to count billed API calls from the same file; two
descriptions that agree only by accident drift. The 5 new tests were run
against the pre-fix code and **4 of 5 fail** — the fifth locks the no-id
contract, where lines and calls happen to coincide.

### 12.4 Still open

- **Stage 4 P1.4 suppression span** — a suppressed tool call emits no span, so a
  trace captured with the cache on reports *less* waste.
- 🔴 **Not shipped.** This lands after `0.5.13`, so production carries the
  line-based turn numbers until the next release.
