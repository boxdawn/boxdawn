# Results — what is the resend that `context_resend` counts?

🔴 **Not pre-registered.** This is a measurement taken before writing the Stage 4
Phase 3 design, to size what a context reduction could touch. There is no
threshold and no gate. Predictions were written down before the run and are
reported in §4, including the one that missed. Cost: **zero**, with no judge,
no API key and no network. Engine at `d079811`.

> 🔴 **Correction, 2026-10-15 (same day). The trace-commons columns below are
> computed on an input the adapter reconstructs wrongly in 13 of the 28
> sessions.** The Claude Code adapter keeps accumulating the conversation past
> context compaction, so after a compaction `input_text` holds history the API
> was not sent. In those 13 sessions (84.2% of the corpus's input tokens), the
> messages measure more tokens than the call was billed for. The cited trace has
> no compaction and no such call, so **its figures stand**. Details and the
> corrected split are in §6. The follow-on simulation is in §7.

## 0. Finding

**Every resent token is history replay.** On the cited trace and on all 28
trace-commons sessions, each chunk `find_context_resend` flags was already in the
immediately previous call's input. The agent sends its whole conversation on
every call because the API is stateless, and the detector counts that replay.

| | cited trace (27 calls) | trace-commons (28 sessions, 4,354 calls) |
|---|---:|---:|
| input tokens | 1,596,520 | 662,627,717 |
| billed as cache read | 94.74% | 98.24% |
| resent / input | **88.66%** | 98.78% |
| resent that was in the previous call | **1,415,467 / 1,415,467** | **654,545,024 / 654,545,024** |
| resent that was not | 0 | 0 |

The cited trace is `data/hf_agent_traces/agent-race/claude-code.jsonl`, the one
behind the home page's 88.7%. Its resent cost here is `$0.9015315`, equal to the
live figure, so this measures the shipped detector and not a reimplementation.

⇒ On the cited trace, the resend figure is a correct count of what was sent
again. It is **not a
count of what could have been left out**: removing a replayed chunk removes
something the model was reading.

## 1. What a reduction could touch

Two levers were sized over the same calls, as input tokens carried across all
calls (a block present in five calls counts five times).

| lever | what it does | cited trace | trace-commons (pooled) 🔴 §6 | trace-commons per session 🔴 §6 |
|---|---|---:|---:|---|
| **DUP** | replace a `tool_result` that is byte-identical to an earlier one *in the same input* with a reference. The first copy stays, so no information leaves the context | 495 (**0.03%**) | 4,379,216 (**0.66%**) | median 0.39%, max 4.06% |
| STALE, K=5 | clear `tool_result` content more than K assistant turns back | 25.06% | 36.26% | — |
| STALE, K=10 | | 13.78% | 34.83% | median 19.77%, range 0.00–65.91% |
| STALE, K=20 | | 1.89% | 32.23% | — |

The pooled trace-commons figures are pulled up by a few long sessions. The
per-session spread is the safer reading.

## 2. What this means for Phase 3

1. **The reduction that leaves behaviour alone is under 1% of input.** DUP is
   0.03% on the cited trace and 0.66% pooled.
2. **The reduction with size removes information.** STALE clears tool output
   the model may still need. That is a behaviour change by construction, and
   this measurement cannot say what it does to task outcomes.
3. 🔴 **STALE may cost more than it saves. That is not measured here.** Nearly
   all input is a cache read. Editing the context at position *p* invalidates
   the provider's prefix cache from *p* onward, so the next call pays the cache
   write rate on everything after *p*. That rate is 12.5× the read rate at a
   5-minute TTL and 20× at a 1-hour TTL (`src/clew/cost/pricing.py:6-8`). The
   net dollar effect depends on where the edit lands and how many calls follow
   it. Only a simulation can settle it.

⇒ `STAGE4_AUTOFIX_DESIGN.md` §0 and §2 assumed that, because `context_resend`
holds nearly all the waste dollars, Phase 3 is where a "tokens saved" claim
would open. That assumption does not hold on this data. A note has been added
there, and Phase 3 is not being designed further for now.

## 3. Method

For each session, the Claude Code adapter builds `llm_calls`. Each call's
`input_text` is the full message list sent on that call.

- **PREFIX / OTHER.** Each `ResentEvent` from `find_context_resend` is assigned
  to its call in trace order. If its `chunk_hash` is among the chunk hashes of
  the previous call's input, it counts as PREFIX, and otherwise as OTHER. Chunk
  boundaries and hashes are the detector's own (`_chunk_boundary`,
  `_sha256_hex`).
- **DUP.** Within one call's input, every `tool_result` block is hashed
  (sha256 of its `content`, JSON-serialised with sorted keys when not a string).
  A block whose hash already appeared earlier in the same input counts.
- **STALE_K.** A `tool_result` block counts when more than K assistant messages
  follow it in the same input.
- **Tokens.** DUP and STALE blocks are sized the way the detector apportions:
  tiktoken length × (the call's reported `input_tokens` / the sum of tiktoken
  lengths of the call's chunks).

Check: PREFIX + OTHER equals the detector's `resent_input_tokens` exactly on
both the cited trace and the pooled corpus. All 28 sessions processed with no
errors, and PREFIX equals resent in every one of them.

Raw output sha256: `936f0017b2c443475adbfc23f4a273b801110727b00131a4149ac8644a63b923`
(diagnostics are not committed; the method above is the reproduction).

## 4. Predictions, written before the run

| | prediction | result | |
|---|---|---|---|
| P1 | PREFIX ≥ 95% of resent | 100% on both | ✅ |
| P2 | DUP ≤ 3% of resent | 0.03% / 0.67% | ✅ |
| P3 | STALE (K=10) between 30% and 60% of input | trace-commons 34.83% · **cited 13.78%** | 🔴 missed on the cited trace |

## 5. What this does not change

No published figure moves. The resend count, the 88.7% and the waste dollars
measure what they measured. What changes is what they can be read as: a share of
input that was replayed, **not** a share that could have been avoided. Whether
any public wording reads it the second way is for whoever owns that wording to
judge.

## 6. Correction — the trace-commons input is not what was sent

Found the same day, when the simulation in §7 failed its own validity check on
trace-commons.

**What is wrong.** In `src/clew/ingest/claude_code.py`, each call's
`input_text` is built from an `accumulated` message list (lines 342–410) that is
never reset. The adapter collects compaction boundaries (lines 509–520) but does
not use them there. Its docstring says the reconstruction *"matches what the
Anthropic API sees as the input to that turn"* (line 254). After a compaction
that is not true: the API was sent a summary plus what followed, and
`input_text` still holds everything before it.

**How it shows.** For each call, the tokens of the reconstructed messages were
compared with the input the call was billed for. In **2,254 of 4,354** calls the
messages are larger. That happens in **13 of 28** sessions, which hold **84.2%**
of the corpus's input tokens. In the raw files, 9 sessions carry compaction
markers and 9 carry images, whose base64 the tokenizer counts by length. At
least one affected session (`3be5ba0c`) has neither, so there is a third cause
that has not been identified.

**The split.** "Not observed" below means no call in the session had messages
larger than its bill. That does not prove the reconstruction right in those
sessions.

| trace-commons | sessions | calls | share of input | resent / input | resent in previous call | DUP | STALE K=5 / 10 / 20 |
|---|---:|---:|---:|---:|---|---:|---|
| overflow not observed | 15 | 993 | 15.8% | 97.43% | all | **1.35%** (median 0.18%, max 4.06%) | 25.61 / 23.43 / 19.66% |
| overflow observed | 13 | 3,361 | 84.2% | 99.03% | all | 0.53% | 38.26 / 36.98 / 34.60% |

**What changes.**

- The pooled trace-commons figures in §0 and §1 (98.78%, DUP 0.66%, STALE
  36.26 / 34.83 / 32.23%) are dominated by sessions whose input is
  reconstructed wrongly. **Do not cite them.** On the 15 sessions without the
  overflow, the safe lever is 1.35%, not 0.66%. The conclusion in §2 (the
  reduction that leaves behaviour alone is small) is unchanged.
- The cited trace's figures (88.66%, DUP 0.03%, all of §0's left column) are
  not affected.
- 🔴 **The shipped `context_resend` detector reads the same `input_text`.** On
  sessions with compaction it can count history that was not sent as resent.
  Each call's resent tokens are clamped to that call's billed input, so the
  total cannot exceed the bill, but the resend *share* is likely overstated.
  **The size and direction on the published trace-commons figures have not been
  measured.** That is a separate piece of work.

## 7. Simulation — does clearing stale tool output lower the bill?

Not pre-registered and not gated. The model, the predictions and a validity
condition were written to a file before the run (sha256
`4ed0eb5723cc20478bd7864558325873874e7a851dc2b04c4e847aeac60f8850`; diagnostics
are not committed).

**Model.** Each call's input is its message list, with cleared `tool_result`
content replaced by a short stub. The prefix cache is read up to the longest
*earlier call's whole input* that prefixes this one (`bp`, primary), or, more
favourably to clearing, up to the longest common prefix with the previous call
(`lcp`). Everything after the read is billed as a cache write, at the call's own
observed 1h/5m mix. The call sequence is held fixed. That favours clearing,
because an agent that lost information may re-fetch it or fail.

**Validity condition, fixed before the run.** The baseline (no clearing) must
reproduce the actual billed input cost within ±10%.

| | baseline vs actual | |
|---|---:|---|
| cited trace | −8.55% | ✅ valid |
| trace-commons | **+146.69%** | 🔴 invalid (§6 is why) |

**Result, cited trace only.** Net change in input cost, against the baseline:

| policy | cleared (share of input) | naive saving (cleared × read rate) | net, `bp` | net, `lcp` |
|---|---:|---:|---:|---:|
| every call, clear output > 5 turns back | 10.60% | 5.80% | **−192.93%** | −83.13% |
| every call, > 10 turns | 6.13% | 3.35% | **−204.33%** | −133.46% |
| every call, > 20 turns | 0.89% | 0.49% | **−104.61%** | −95.82% |
| every 5th call, > 5 turns | 9.04% | 4.94% | **−43.39%** | −23.29% |
| every 10th call, > 10 turns | 2.70% | 1.47% | **−13.92%** | −13.20% |
| every 20th call, > 20 turns | 0.00% | 0.00% | 0.00% | 0.00% |

Negative means the bill goes up. **Every policy that clears anything raises the
input cost, under both cache models.** Each clearing breaks the cached prefix
at the cleared block, and everything after it is written again at 12.5× (5m) or
20× (1h) the read rate. The cheapest policy that clears anything still costs
13–14% more.

**Predictions.**

| | prediction | result |
|---|---|---|
| Q1 | baseline within ±10% on both | 🔴 cited ✅, trace-commons ✗ |
| Q2 | clearing every call at K=5 raises the cited trace's cost | ✅ −192.93% |
| Q3 | every per-call policy nets less than its naive saving | ✅ on the cited trace |
| Q4, Q5 | about trace-commons | not scorable (invalid) |
| Q6 | `lcp` nets at least as much as `bp` | ✅ on the cited trace |

⇒ On the one trace where the model holds, clearing stale tool output does not
save money. It costs more. With §2, Phase 3 stays closed. One trace is not a
general result, and trace-commons cannot answer until §6 is fixed.
