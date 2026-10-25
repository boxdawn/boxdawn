# Thinking Signatures Weighted by the Thinking They Carry — Pre-registration

**Status.** Drafted 2026-10-21 before any measurement of the effect; 세원님
decided on 2026-10-24 to pursue it. Revised after two adversarial reviews
(24 and 10 findings, 2026-10-24/25, before any code). From this PR on the text is frozen;
anything changed later goes in a dated amendment.
**Engine.** `main` at `3659761` (0.5.23, released). `src/` is unchanged since
the draft was written at `655e9b1`; only the version number moved.

## 0. What is known (before this document)

- Corpus A (trace-commons, 28 Claude Code sessions) overflow census
  (`field_test/diagnostics/_overflow_cause_2026_10_17/census.py`): with images
  weighted as in 0.5.23, **848** calls measure more input than they were
  billed (`CC_IMAGE_TOKEN_SHARE_PREREG.md` §6). Removing signatures as well
  leaves the 8 `<synthetic>` entries. The 839 in README "Still open" is the
  other arm (images and signatures both counted by length, 2026-10-17).
- Facts measured 2026-10-21 on Corpus A, no detector change
  (`field_test/diagnostics/_signature_size_facts_2026_10_21/`, uncommitted):
  - 690 assistant messages carry a thinking block; every `thinking` text is
    empty (display omitted). 0 `redacted_thinking` blocks.
  - Per message, signature length correlates 0.984 with
    `output_tokens − visible output tokens` (text + tool_use input, cl100k).
  - Counted by length, a signature weighs a median 2.35× that estimate
    (p10 1.77, p90 3.04). These ratios come from `probe.py`, whose `visible`
    serializes tool_use input without `sort_keys` over all 690 messages; §1
    below fixes a different serialization over the chunks that reach an
    input, so 2.35 is a description of the probe, not of the change.
  - 685 signature chunks appear in at least one call's `input_text` (681 of
    them in two or more, so flaggable; the other 5 of the 690 messages are
    final messages never sent back). For all 685, the call immediately
    before the chunk's first appearance has `output_tokens` equal to the
    producing message's own usage (685/685). The first review reran this:
    685 distinct chunk hashes, one signature per chunk, no signature under
    two hashes, none first appearing in call 0.
  - Model of every thinking message: `claude-sonnet-4-6` 126 ·
    `claude-opus-4-8` 564. Both keep earlier thinking (below).
  - Of the 685 (second review's figures, reproduced by the author
    2026-10-25 with the §1 definitions, `PYTHONHASHSEED=0`): 682 first appear
    in a call of the producing model and 3 in a `<synthetic>` call; 684 also
    carry text or tool_use; none has more than one thinking block; 1 has
    `output_tokens − visible ≤ 0`. 8 of the 28 sessions have a signature
    chunk; the other 20 raw session files contain no `"signature"` string.
- Other corpora: no signature in TRAIL GAIA, the framework dumps or the example
  OTel traces (2026-10-21). Corpus B: 0 files under `data/toolathlon` contain
  `"signature"` (2026-10-24). Corpus C (10,056 sessions, 1,920 with a Claude
  model): `"signature"` occurs in span messages of 13 sessions (152 spans), all
  13 `gemini-3-pro-preview`, as a key beside tool-call arguments; 0 in Claude
  sessions (2026-10-24, scan of the raw `gen_ai.input.messages` /
  `gen_ai.output.messages` attributes, not of the adapter-built `input_text`;
  G7 checks the latter). Corpus D: no Claude calls.
- Billing (Anthropic docs, read 2026-10-24,
  `build-with-claude/extended-thinking`, "Migrating to adaptive thinking"):
  *"Claude Opus 4.5 and models numbered 4.6 and higher keep prior turns'
  thinking blocks in context and bill them as input, where Claude Sonnet 4.5
  (deprecated), Claude Haiku 4.5, and earlier models strip them."* That kept
  thinking is billed at its original thinking tokens is a reading of the
  docs (`_b64_billing_facts_2026_10_20.md` §1), not measured here. The same page names
  `usage.output_tokens_details.thinking_tokens`; Corpus A does not carry it.
- Seen during review, **not reproduced and not used as evidence**: the
  reviewer's own script put the summed length of the 685 signature chunks at
  first appearance at 2,664,094 tokens as counted today and 1,242,278 under a
  reading of §1. The second reviewer's script found 568 of 4,326 calls with
  `k > 0` where signatures weigh more among first appearances than among
  resent chunks (also not reproduced). The thresholds and the P2 direction in
  §2 were set after seeing both figures.
- Not measured: the effect of the change on `union_wr_cost`, on the census,
  or on reports.

## 1. The change

All names refer to `src/clew/detect/context_resend.py` at `3659761`.

**1.1 Signature chunk.** A chunk from `_chunk_boundary` is a signature chunk
when all of these hold:
- it is one element of the parsed list (top-level list or `messages`), not
  the whole-input fallback, and that element is a dict;
- its `role` is `"assistant"`;
- its `content` is a list with at least one block of `type == "thinking"`
  carrying a non-empty string `signature`.

Anything else, including `redacted_thinking`, is not a signature chunk.

**1.2 Identity and source call.** A chunk is identified by `_sha256_hex` of
its text, as the detector already does. `k` = the index in `llm_calls` of the
first call whose chunks contain that hash; `p = k − 1`.

**1.3 Estimate (once per chunk).** If `p < 0`, or `llm_calls[p]` has no
integer `output_tokens`, the chunk has no estimate. Otherwise
`thinking_est = max(0, output_tokens(p) − visible)`, where `visible` is the
sum of the following terms over the chunk's `content` blocks, each term a
separate call to `_text_token_len(·, model of call p)` (so each non-empty
string has its own floor of 1):
- `type == "text"`: the `text` value if it is a string, else nothing;
- `type == "tool_use"`: the `name` value if it is a string; and, as a second
  term, `json.dumps(input, sort_keys=True, ensure_ascii=False)` if the block
  has an `input` key, else nothing;
- every other block type contributes nothing.

One estimate per chunk, however many thinking blocks it holds.

**1.4 Which occurrences change.** Each occurrence of a signature chunk is
judged by the model of the call it occurs in. An occurrence changes only when
that model keeps earlier thinking: `_model_version(model)` returns
`(major, minor)` with `(major, minor) >= (4, 6)`, or the model name contains
`"opus"` and the version is exactly `(4, 5)`. Every occurrence that meets this
changes, the first included (it is never flagged, but it is in its call's
`share_total`). Occurrences in other calls (model `None`, `<synthetic>`,
names `_model_version` cannot parse, models that strip thinking) keep their
0.5.23 length. So do chunks with no estimate. In Corpus A this leaves 3
signature chunks heavy at their first appearance (a `<synthetic>` call)
while their later occurrences change; the implementation reports changed
and unchanged signature occurrences split by call model.

**1.5 New length.** Remove every `signature` key from thinking blocks, re-dump
with `sort_keys=True, ensure_ascii=False`, take `_chunk_token_len` of that
text with the occurrence's model (so images are still weighted as in 0.5.23),
then add `thinking_est`.

**1.6 Everything else.** Every chunk occurrence not changed by 1.4 keeps its
0.5.23 length exactly.

## 2. Guards and predictions

Corpus A, 28 sessions, public-figure method (`waste_rate_metric.py` way), both
arms in one process, `PYTHONHASHSEED=0`; as-is arm = 0.5.23 code.

**Baseline (as-is arm must reproduce, else stop):** `union_wr_cost`
304.71579418567944 / 343.2929203500001 = 0.8876262110940424; context_resend
alone 304.69214540000644; `union_wr_char` 0.991595182355781;
`union_sdr_at_10` 0.9642857142857143 (from
`_image_weight_results_2026_10_21/run_a.RESULTS.json`, `weighted`, produced
with `PYTHONHASHSEED=0` as `CC_IMAGE_TOKEN_SHARE_PREREG.md` §2 states);
census 848. Tolerance: the census, `union_wr_char`, `union_sdr_at_10` and
the context_resend sum must match exactly; values built from
`union_waste_cost` (its numerator and `union_wr_cost`) within 1e-9, because
that sum runs over a set.

Guards that hold by construction (they check the harness, not the change):
- **G1.** `union_wr_char` and `union_sdr_at_10` bit-identical (byte-based).
- **G2.** `total_input_cost` bit-identical in all 28 (pricing does not read
  chunk lengths).
- **G3.** Sessions with no signature chunk (20 of 28 by raw grep, §0; the
  implementation's own count is reported): `resent_cost` bit-identical,
  `union_waste_cost` within 1e-9 (its set summation is not bitwise stable).

Guards that test the change:
- **G4.** In all 28 sessions, the length of every chunk occurrence that 1.4
  does not change equals its as-is length, checked one occurrence at a time.
- **G5.** For each signature chunk, the `p` the implementation chose has
  `output_tokens` equal to the producing message's usage in the raw JSONL
  (685/685). The harness reads `p` from the implementation's own function,
  then reads the JSONL; it does not recompute `p`.
- **G6.** Corpus D: report bit-identical (no Claude calls).
- **G7.** Corpus B and C: the implementation's count of changed signature
  occurrences, over the adapter-built `input_text`, is 0.

Predictions (judgements):
- **P1.** Census with the implementation's lengths (the values
  `find_context_resend` uses as share weights, read from the implementation,
  not re-implemented): **at most 50** calls over their bill (from 848). Floor
  is 8 (`<synthetic>`), since the new length is never below the stripped
  one. Every call above 8 is reported with its overshoot. Whether an
  overshoot means `thinking_est` is too high depends on how cl100k compares
  with Anthropic's tokenizer on the visible text, which is not measured
  (§5).
- **P2.** Corpus A `union_wr_cost` **falls**, by **less than 0.03** from
  0.8876262110940424. The direction is a judgement: share is computed per
  call over `share_total`, so a call moves toward less resent weight only
  when signature chunks are a larger part of its resent weight than of its
  first-appearance weight. The second review found the opposite in 568 of
  4,326 calls with `k > 0`; the judgement is that the rest outweigh them.
  Dollar weighting (`_price_against_ladder`, cheapest rung first) and the
  per-call budget clamp are not part of the argument.
- **P3.** Corpus B and C unchanged (G7). Their reports are not re-run unless
  G7 fails.

Negative result: a P1 or P2 miss is published as a miss, with its size. A
miss alone does not stop shipping; stop conditions do.

## 3. Stop conditions (no shipping, report only)

- The as-is arm does not reproduce every baseline value above.
- Any guard fails (G7 failing means §0's absence claim was wrong for the
  text the detector reads: report the count and stop).
- Any Corpus A signature chunk has no estimate (`p < 0` or no `output_tokens`).
- More than 1% of Corpus A signature chunks have `thinking_est = 0`
  (underestimate side).
- Census above **200** (§1 would leave about a quarter of the 848 calls still
  measuring more than their bill).

## 4. After the results

Results are appended to this file as a dated section, with every value above
and both arms. Whether to release, re-pin the hosted analyzer, correct the
README and notify the web and marketing sessions is 세원님's decision after
reading them.

## 5. Not covered

- Exactness and direction. `visible` is a cl100k count, not Anthropic's
  tokenizer, so `thinking_est` is an estimate, and whether it errs high or low
  is not measured. Public wording may say "estimated from the producing
  call's output", never "exact", "as billed" or "upper bound".
- Signatures inside a whole-input fallback chunk (input that is not a list
  and has no `messages` list) are not signature chunks under 1.1 and keep
  their length-based weight.
- The 685/685 producer link, the 2.35× ratio and the counts in §0 are Corpus A
  (Claude Code) facts, not properties of the method.
- Models that strip earlier thinking. There, the kept signature is billed 0
  input tokens; 1.4 leaves those occurrences at their 0.5.23 length (too
  heavy). The count of such occurrences is reported; none occur in Corpus A.
- The scope is gated by model name, not by adapter. Any adapter whose
  assistant chunks carry thinking blocks with signatures, in a Claude call
  that keeps thinking, is affected. Only Claude Code traces were measured.
- Non-Claude signatures (Corpus C's Gemini sessions, §0) are still counted by
  length. Their billing was not looked up; this change does not touch them.
- Traces that carry `output_tokens_details.thinking_tokens` could be weighted
  exactly; no adapter reads it today and this change does not use it.
- A source call other than `k − 1` (resumed sessions, compaction, interleaved
  sub-agent calls). G5 checks the link on Corpus A only.
