# Results — what is the resend that `context_resend` counts?

🔴 **Not pre-registered.** This is a measurement taken before writing the Stage 4
Phase 3 design, to size what a context reduction could touch. There is no
threshold and no gate. Predictions were written down before the run and are
reported in §4, including the one that missed. Cost: **zero**, with no judge,
no API key and no network. Engine at `d079811`.

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

⇒ The resend figure is a correct count of what was sent again. It is **not a
count of what could have been left out**: removing a replayed chunk removes
something the model was reading.

## 1. What a reduction could touch

Two levers were sized over the same calls, as input tokens carried across all
calls (a block present in five calls counts five times).

| lever | what it does | cited trace | trace-commons (pooled) | trace-commons per session |
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
