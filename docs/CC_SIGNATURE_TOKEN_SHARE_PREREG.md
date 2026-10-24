# Thinking Signatures Weighted by the Thinking They Carry — Pre-registration

**Status.** Drafted 2026-10-21 before any measurement of the effect; 세원님
decided on 2026-10-24 to pursue it. Revised the same day after one adversarial
review (24 findings, before any code). From this PR on the text is frozen;
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
    below fixes a different serialization over the resent chunks, so 2.35 is
    a description of the probe, not of the change.
  - For all 685 signature chunks that are resent, the call immediately before
    the chunk's first appearance in `input_text` has `output_tokens` equal to
    the producing message's own usage (685/685; the other 5 are final
    messages never resent). The review reran this: 685 distinct chunk hashes,
    one signature per chunk, no signature under two hashes, none first
    appearing in call 0.
  - Model of every thinking message: `claude-sonnet-4-6` 126 ·
    `claude-opus-4-8` 564. Both keep earlier thinking (below).
- Other corpora: no signature in TRAIL GAIA, the framework dumps or the example
  OTel traces (2026-10-21). Corpus B: 0 files under `data/toolathlon` contain
  `"signature"` (2026-10-24). Corpus C (10,056 sessions, 1,920 with a Claude
  model): `"signature"` occurs in span messages of 13 sessions (152 spans), all
  13 `gemini-3-pro-preview`, as a key beside tool-call arguments; 0 in Claude
  sessions (2026-10-24, scan of `gen_ai.input.messages` /
  `gen_ai.output.messages`). Corpus D: no Claude calls.
- Billing (Anthropic docs, read 2026-10-24,
  `build-with-claude/extended-thinking`, "Migrating to adaptive thinking"):
  *"Claude Opus 4.5 and models numbered 4.6 and higher keep prior turns'
  thinking blocks in context and bill them as input, where Claude Sonnet 4.5
  (deprecated), Claude Haiku 4.5, and earlier models strip them."* Kept
  thinking is billed at its original thinking tokens
  (`_b64_billing_facts_2026_10_20.md` §1). The same page names
  `usage.output_tokens_details.thinking_tokens`; Corpus A does not carry it.
- Seen during review, **not reproduced and not used as evidence**: the
  reviewer's own script put the summed length of the 685 signature chunks at
  first appearance at 2,664,094 tokens as counted today and 1,242,278 under a
  reading of §1. The thresholds in §2 were set after seeing this figure.
- Not measured: the effect of the change on `union_wr_cost`, on the census,
  or on reports.

## 1. The change

All names refer to `src/clew/detect/context_resend.py` at `3659761`.

**1.1 Signature chunk.** A chunk from `_chunk_boundary` is a signature chunk
when all of these hold:
- it came from a parsed element (not the whole-input fallback, role `None`);
- `json.loads(text)` is a dict whose `sort_keys` re-dump equals `text` (the
  same test `_image_weighted_len` uses);
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
sum over the chunk's `content` blocks, each block counted separately with
`_text_token_len(·, model of call p)`:
- `type == "text"`: the `text` string as is;
- `type == "tool_use"`: the `name` string, plus
  `json.dumps(input, sort_keys=True, ensure_ascii=False)`;
- every other block type contributes 0.

One estimate per chunk, however many thinking blocks it holds.

**1.4 Which occurrences change.** Each occurrence of a signature chunk is
judged by the model of the call it occurs in. An occurrence changes only when
that model keeps earlier thinking: `_model_version(model)` returns
`(major, minor)` with `(major, minor) >= (4, 6)`, or the model name contains
`"opus"` and the version is exactly `(4, 5)`. Every occurrence that meets this
changes, the first included (it is never flagged, but it is in its call's
`share_total`). Occurrences in other calls (`<synthetic>`, unparsable names,
models that strip thinking) keep their 0.5.23 length. So do chunks with no
estimate.

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
`_image_weight_results_2026_10_21/run_a.RESULTS.json`, `weighted`); census 848.

Guards that hold by construction (they check the harness, not the change):
- **G1.** `union_wr_char` and `union_sdr_at_10` bit-identical (byte-based).
- **G2.** `total_input_cost` bit-identical in all 28 (pricing does not read
  chunk lengths).
- **G3.** Sessions with no signature chunk: `resent_cost` bit-identical,
  `union_waste_cost` within 1e-9 (its set summation is not bitwise stable).

Guards that test the change:
- **G4.** In all 28 sessions, the length of every chunk occurrence that 1.4
  does not change equals its as-is length, checked one occurrence at a time.
- **G5.** For each signature chunk, the `p` the implementation chose has
  `output_tokens` equal to the producing message's usage in the raw JSONL
  (685/685). The harness reads `p` from the implementation's own function,
  then reads the JSONL; it does not recompute `p`.
- **G6.** Corpus D: report bit-identical (no Claude calls).

Predictions (judgements):
- **P1.** Census with the implementation's lengths (the values
  `find_context_resend` uses as share weights, read from the implementation,
  not re-implemented): **at most 50** calls over their bill (from 848). Floor
  is 8 (`<synthetic>`). `thinking_est` is an upper estimate (§4), so every
  call above 8 is reported with its overshoot as evidence of overestimation.
- **P2.** Corpus A `union_wr_cost` **falls**, by **less than 0.03** from
  0.8876262110940424. Reason for the direction: 685 of 690 signature chunks
  are resent, so shortening them takes more weight off resent chunks than off
  first appearances.
- **P3.** Corpus B and C: no signature in a Claude call (§0), so both are
  unchanged by construction. The implementation's count of changed
  occurrences is reported for each; if it is above 0 for either, that corpus
  is re-measured under §1 and reported alongside A.

Negative result: a P1 or P2 miss is published as a miss, with its size. A
miss alone does not stop shipping; stop conditions do.

## 3. Stop conditions (no shipping, report only)

- The as-is arm does not reproduce every baseline value above.
- Any guard fails.
- Any Corpus A signature chunk has no estimate (`p < 0` or no `output_tokens`).
- More than 1% of Corpus A signature chunks have `thinking_est = 0`
  (underestimate side).
- Census above **200** (overestimate side: §1 would be heavier than the bill
  in roughly a quarter of the calls it was meant to fix).

## 4. After the results

Results are appended to this file as a dated section, with every value above
and both arms. Whether to release, re-pin the hosted analyzer, correct the
README and notify the web and marketing sessions is 세원님's decision after
reading them.

## 5. Not covered

- Exactness. `visible` is a cl100k count, not Anthropic's tokenizer, so
  `thinking_est` is an upper estimate of the thinking tokens, not the bill.
  Public wording may say "estimated from the producing call's output", never
  "exact" or "as billed".
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
