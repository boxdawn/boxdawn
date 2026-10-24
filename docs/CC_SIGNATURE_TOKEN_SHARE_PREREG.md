# Thinking Signatures Weighted by the Thinking They Carry — Pre-registration

**Status.** Drafted 2026-10-21 before any measurement of the effect; 세원님
decided on 2026-10-24 to pursue it. From this PR on the text is frozen;
anything changed later goes in a dated amendment.
**Engine.** `main` at `3659761` (0.5.23, released). `src/` is unchanged since
the draft was written at `655e9b1`; only the version number moved.

## 0. What is known (before this document)

- After 0.5.23 weights images as billed, the only cause of a Corpus A call
  measuring more input than it was billed, besides 8 `<synthetic>` entries, is
  thinking-block `signature` fields counted by their base64 length
  (`CC_IMAGE_TOKEN_SHARE_PREREG.md` §6: 848 calls).
- Facts measured 2026-10-21 on Corpus A, no detector change
  (`field_test/diagnostics/_signature_size_facts_2026_10_21/`, uncommitted):
  - 690 assistant messages carry a thinking block; every `thinking` text is
    empty (display omitted).
  - Per message, signature length correlates 0.984 with
    `output_tokens − visible output tokens` (text + tool_use input, cl100k).
  - Counted by length, a signature weighs a median 2.35× that estimate
    (p10 1.77, p90 3.04).
  - For all 685 signatures that are resent, the call immediately before a
    signature's first appearance in `input_text` has `output_tokens` equal to
    the producing message's own usage (685/685).
  - No signature occurs in TRAIL GAIA, the framework dumps or the example OTel
    traces.
- Not measured: the effect of any change on `union_wr_cost`, on the overflow
  count, or on reports.

## 1. The change (frozen if approved)

In `context_resend`, Claude calls only. For an assistant chunk that contains
at least one thinking block with a `signature`:

1. Let `k` be the index of the call where this chunk first appears, and
   `p = k − 1`. If `p < 0`, no change for this chunk.
2. `thinking_est = max(0, llm_calls[p].output_tokens − visible)`, where
   `visible` = `_text_token_len` of the chunk's `text` blocks and `tool_use`
   blocks (input JSON + name) re-serialized as `_chunk_boundary` does.
3. Chunk length = `_chunk_token_len` of the chunk with every `signature` field
   removed (images still weighted as in 0.5.23) + `thinking_est`.
4. Every other chunk keeps its 0.5.23 count exactly.

## 2. Predictions (frozen if approved)

Corpus A, 28 sessions, public-figure method, both arms in one process,
`PYTHONHASHSEED=0`; as-is arm = 0.5.23.

Guards:
- **G1.** `union_wr_char` 0.9916 and `union_sdr_at_10` 0.9643 bit-identical.
- **G2.** Sessions with no signature: `resent_cost` bit-identical.
- **G3.** `total_input_cost` bit-identical in all 28.
- **G4.** The 685/685 link reproduces through the implementation.

Predictions (judgements, labelled as such):
- **P1.** The overflow census (images weighted, signatures weighted as §1)
  falls from 848 to **at most 100** calls.
- **P2.** Corpus A `union_wr_cost` moves by less than **0.01** from 0.8876.
  Direction not predicted.
- **P3.** Corpus B, C, D: no signature → no change, by construction; the count
  of signature-carrying chunks is reported.

## 3. Stop conditions

- As-is arm does not reproduce 0.8876 / census 848.
- Any guard fails.
- More than 1% of signature chunks have `thinking_est = 0` (would mean the
  visible-output subtraction is mis-specified).

## 4. Not covered

- Exactness: `visible` is a cl100k approximation of Anthropic's tokenizer;
  this weights signatures closer to their bill, not at it. Public wording may
  not call it exact.
- Non-Claude-Code adapters (no signatures observed).
