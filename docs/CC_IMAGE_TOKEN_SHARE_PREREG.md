# Image Blocks Weighted As Billed in `context_resend` — Pre-registration

**Scope.** `context_resend` splits each call's billed input across the call's
chunks in proportion to each chunk's token length
(`_chunk_token_len`, `src/clew/detect/context_resend.py:116`). A chunk that
carries a base64 image is measured by the length of the base64 text, which
has nothing to do with what the image is billed. This document fixes how an
image will be weighted instead, and what that must do to the published
figures, before the code changes.
**Written.** 2026-10-21. Engine `main` at `ed3a27e`. Nothing changed yet.
**Code and results** follow as separate commits. A release, the cloud pin
and any README change are decided after the results, not by this document.

## 0. What is known (before this document)

- 1,557 of 4,354 trace-commons calls measure more input than they were
  billed. 710 are explained by image blocks, 839 by thinking-block
  `signature` fields, 8 are `<synthetic>` entries
  ([`CC_INPUT_OVERFLOW_CAUSES_RESULTS.md`](CC_INPUT_OVERFLOW_CAUSES_RESULTS.md),
  census at `76fbbd4`).
- On 2026-10-18, with images **and** signatures removed, Corpus A
  `union_wr_cost` moved from 0.8449 to 0.8457 (same document). That was over
  the 23 sessions then priced, it removed both causes at once, and it counted
  images as 0 tokens. It is not a bound for this change.
- The published Corpus A figure is now **308.4824 / 343.2929 = 0.8986** over
  28 sessions ([`CORPUS_A_OPUS48_PRICING_PREREG.md`](CORPUS_A_OPUS48_PRICING_PREREG.md) §6).
  Corpus A's models: `claude-sonnet-4-6` (standard tier below),
  `claude-opus-4-8` (high tier), `<synthetic>`.
- How images are billed, Anthropic documentation read 2026-10-21
  ([vision](https://platform.claude.com/docs/en/build-with-claude/vision),
  [vision-coordinates](https://platform.claude.com/docs/en/build-with-claude/vision-coordinates)):
  an image costs `⌈width / 28⌉ × ⌈height / 28⌉` visual tokens after it is
  resized to the largest aspect-preserving size within the model's tier.
  High-resolution tier, "Claude 4.7 and later models": long edge 2576 px,
  4784 tokens. Standard tier, "All other models": 1568 px, 1568 tokens. The
  resize is given as a reference implementation (`resized_size`), with the
  short edge rounded half to even.
- Signatures are billed as the original thinking tokens. Claude Code
  transcripts carry no thinking token count, so they cannot be weighted as
  billed. **They are out of scope here** and stay counted by length.

## 1. The change (frozen)

In `_chunk_token_len` only. Nothing else in the detector changes.

1. **When.** The call's `model` contains `claude` (anywhere, case
   ignored), the chunk text parses as a JSON object, and
   `json.dumps(parsed, sort_keys=True, ensure_ascii=False)` equals the chunk
   text exactly. That last test admits only element chunks from
   `_chunk_boundary` and excludes its raw-text fallback chunk. Otherwise the
   current count, unchanged.
2. **Image block.** A dict with `"type": "image"` and
   `source.type == "base64"` that is an element of a list, at any depth
   (this includes images inside `tool_result` content). An image dict that
   is a dict value rather than a list element is not touched.
3. **Size.** Width and height from the decoded bytes, format chosen by
   magic bytes, not by `media_type`: PNG (`IHDR`), GIF (logical screen),
   WebP (`VP8 `, `VP8L`, `VP8X`), JPEG (first `SOF0`–`SOF15` marker other
   than `DHT` C4, `JPG` C8, `DAC` CC). EXIF orientation is ignored: swapping
   width and height changes neither the resize nor the token count. Invalid
   base64, an unknown format or an unreadable header: the block is
   **readable = no**, stays in place and is counted as today.
4. **Tier.** Version `(M, N)` from the model name: after the first
   `claude`, split on every run of non-alphanumeric characters; `M` is the
   first one-digit token, `N` is the next token if it is one or two digits,
   else 0. High-resolution tier when `(M, N) >= (4, 7)`. Standard when the
   version is lower or none is found. On the 42 `claude` names in
   `src/clew/cost/pricing.py` this puts on the high tier exactly Opus 4.7,
   Opus 4.8 and every 5.x name (Opus, Sonnet, Haiku, Fable, Mythos), and it
   reads `claude-sonnet-4-20250514` as 4.0, `claude-opus-4-8[1m]` as 4.8 and
   `us.anthropic.claude-opus-4-8-v1:0` as 4.8.
5. **Visual tokens.** `⌈w′/28⌉ × ⌈h′/28⌉` where `(w′, h′)` is the
   documented `resized_size(w, h, max_edge, max_tokens)` for the tier,
   ported as given.
6. **Chunk length.** Delete every readable image block from its parent
   list (an emptied list stays `[]`), re-serialize with
   `json.dumps(..., sort_keys=True, ensure_ascii=False)`, take its token
   length as today, and add the visual tokens of the removed blocks. This is
   the same removal as `strip(..., drop_images=True)` in the 10-17 census.
   A chunk with no readable image block keeps its current count exactly.

Unit tests carry the documented examples: standard tier 1075×1520 →
924×1307, 1920×1080 → 1456×819 (1560 tokens), 200×200 → 64; high tier
1920×1080 → 2691, 3840×2160 → 2576×1449 (4784). All were checked against a
port of the reference implementation on 2026-10-21. One row of the
documentation's table disagrees with its own reference implementation:
2000×1500 on the standard tier is listed as 1269×952, and the
implementation gives 1270×952. Both cost 1564 tokens, so the token count
does not depend on which is right. The implementation is what is ported.

## 2. Predictions (frozen)

Corpus A = the 28 trace-commons sessions, public-figure method
(`waste_rate_metric.py`, uncommitted), `PYTHONHASHSEED=0`, both arms in one
process. The as-is arm must reproduce 308.4824 / 343.2929 first.

**Guards.** These hold by construction; they check that the change stays
inside image chunks.

- **G1.** `union_wr_char` 0.9916 and `union_sdr_at_10` 0.9643 are
  bit-identical. Which chunks are flagged, and their bytes, does not depend
  on token lengths; `sdr_at_10` is a threshold on `wr_char`.
- **G2.** In every session with no readable image block, `context_resend`'s
  `resent_cost` is bit-identical. `union_waste_cost` is equal to within
  1e-9 absolute (its summation order over a set is not bitwise stable).
- **G3.** `total_input_cost` is bit-identical in all 28 sessions. The bill
  is not apportioned; only its split is.
- **G4.** Corpus D (MIMO): no `claude` model, so nothing applies.

**Predictions.**

- **P1.** Corpus A `union_wr_cost` changes by less than **0.005** in
  absolute value from 0.8986. This is a judgement, not derived: the only
  earlier measurement (§0) removed a different set of tokens over a
  different denominator. **Direction not predicted.**
- **P2.** The overflow census (`_overflow_cause_2026_10_17/census.py`,
  uncommitted) is first re-run on `ed3a27e` and must reproduce 1,557 and
  847. Then, with images weighted as in §1 and signatures as today, calls
  over their bill are **at least 847**: each chunk's length is its
  image-free length plus a non-negative number. No upper value is
  predicted; an image that compresses well can cost more visual tokens than
  its base64 has text tokens.
- **P3.** Corpus B (Toolathlon) and C (Exgentic): the number of chunks with
  a readable image block on a `claude` model is counted. No value is
  predicted. Where it is 0, the corpus does not move by construction. Where
  it is above 0, the corpus is re-measured and the result reported.

## 3. Stop conditions

- The as-is arm does not reproduce 0.8986, or the census does not reproduce
  1,557 / 847: the baseline moved. Find out why first.
- G1, G2 or G3 fails: the change reaches past image chunks.
- A unit test from the documented examples fails: the port is wrong.
- More than 5% of the distinct base64 images in Corpus A (distinct `data`
  strings, not occurrences across calls) are readable = no: the header
  reader is incomplete. This document is amended before going on.

## 4. After the results

- Results go in a dated section appended to this document, misses included.
- What is put to 세원님, not decided here: a patch release, the cloud pin
  after it (`context_resend` is on the hosted path, so a trace with
  screenshots would show a different `wr_cost` from that release on), and
  the README. README:305 currently describes the open item against 0.8449;
  any change to it says images are weighted as billed and signatures are
  not, and if the four-decimal Corpus A figure moves, a dated correction in
  the shape of the earlier ones with the old value kept visible.
- Notice to web and marketing if the detector's behaviour ships or a public
  figure moves.

## 5. Not covered

- Signatures (§0). They remain the larger of the two causes by call count.
- OpenAI-format images (`image_url` data URIs). OpenAI bills images by a
  different rule. No such chunk has been counted in our corpora.
- Images by `url` or `file_id`: no bytes in the trace, so no size to read.

## 6. Results (2026-10-21)

Run on the implementation commit, rebased on `main` at `9e16ba7`,
`PYTHONHASHSEED=0`, both arms in one process: as-is = `_text_token_len`
for every chunk, weighted = `_chunk_token_len` as shipped in that commit.
Scripts are diagnostic and not committed
(`field_test/diagnostics/_image_weight_results_2026_10_21/`).

### Corpus A

| | Prediction | As-is | Weighted | |
|---|---|---:|---:|---|
| baseline | reproduce 308.4824 / 343.2929 | **308.4824 / 343.2929 = 0.8986** | | ✅ |
| G1 | `union_wr_char` 0.9916, `union_sdr_at_10` 0.9643 bit-identical | 0.9916 · 0.9643 | 0.9916 · 0.9643 | ✅ bit-identical |
| G2 | sessions with no readable image unchanged | | 21 / 21 `resent_cost` bit-identical, `union_waste_cost` \|Δ\| = 0 | ✅ |
| G3 | `total_input_cost` bit-identical | | 28 / 28 | ✅ |
| stop | ≤ 5% of distinct images unreadable | | 0 of 63 | ✅ |
| **P1** | \|Δ `union_wr_cost`\| < 0.005 | 0.8986 | **304.7158 / 343.2929 = 0.8876** | ❌ **Δ −0.0110** |

**P1 missed.** The figure moved by −0.0110, more than twice the bound. The
bound was a judgement, labelled as one in §2, and it was wrong.

Where the move comes from. 7 of the 28 sessions carry readable images
(10,134 image occurrences across their calls, 63 distinct images). 5 fall
and 2 rise:

| session | images (occurrences) | input cost | Δ per-session `wr_cost` | Δ waste $ |
|---|---:|---:|---:|---:|
| `c84c0ad3` | 152 | $3.99 | −0.0622 | −0.2481 |
| `d4c4d47d` | 1,223 | $5.52 | −0.0610 | −0.3367 |
| `da5d32d6` | 7,979 | $118.44 | −0.0293 | −3.4691 |
| `7563bddf` | 165 | $14.07 | −0.0062 | −0.0866 |
| `17c2cf98` | 169 | $8.56 | −0.0027 | −0.0231 |
| `09d9abe9` | 190 | $5.48 | +0.0206 | +0.1129 |
| `860618e1` | 256 | $10.50 | +0.0271 | +0.2840 |

Of the $3.77 net fall, $3.47 is `da5d32d6`, the Opus 4.8 session that is
34.5% of the denominator. The single-detector ratio
(`resent_cost / total_input_cost`, README "Context Resend Detector")
moves from 308.4588 / 343.2929 = 0.8985 to 304.6921 / 343.2929 = **0.8876**.

Not established: why `da5d32d6` falls rather than rises. The 10-18 arm that
removed images and signatures together moved the aggregate up; this arm
weights images only, on the high tier, and moves it down. The two arms
differ in the denominator (23 vs 28 sessions), in whether signatures moved,
and in what an image weighs, so they do not explain each other.

### Overflow census (P2)

The census of the causes document, re-run on the same code. "Over" means a
call's messages, counted one by one, sum to more than its billed
`input_tokens`.

| arm | calls over their bill (of 4,354) |
|---|---:|
| as-is, nothing removed | **1,557** (reproduces) |
| as-is, images removed | **847** (reproduces) |
| as-is, images and signatures removed | **8** (reproduces) |
| **images weighted (§1), signatures as today** | **848** |
| images weighted, signatures removed | 8 |

**P2 holds:** 848 ≥ 847. With images weighted, removing signatures leaves
the same 8 calls as removing both, which are the 8 `<synthetic>` entries.
Weighting images as billed removes all but one of the 710 image-caused
overflows. A call's weighted count is never below its image-free count, so
the one extra call (848 vs 847) is over its bill only once its images'
visual tokens are added on top of its signatures.
Signatures are now the only cause of overflow outside `<synthetic>`.

### Corpus B, C and D (P3, G4)

| corpus | claude calls | claude chunks with a readable image block | |
|---|---:|---:|---|
| B · Toolathlon (6,780 traces) | 27,365 | **0** | does not move |
| C · Exgentic (10,056 sessions) | 55,789 (`claude-opus-4-5`) | **0** | does not move |
| D · MIMO | 0 | 0 | does not move (G4) |

In B, 21,709 calls contain the text `"image`. None is an image content
block: they are field names (`"images"`, `"image/jpeg"`, `"imageName"`)
inside escaped JSON in tool outputs. No claude call in B or C has a
`"type": "image"` block at all.

### Summary

| | |
|---|---|
| G1–G4, stop conditions | all hold |
| P1 | **missed**: Corpus A `union_wr_cost` 0.8986 → **0.8876** (Δ −0.0110 against a bound of 0.005) |
| P2 | holds (848 ≥ 847) |
| P3 | B and C have no image blocks; they do not move |

The published Corpus A figure would change in the third decimal if this
ships. Whether to release, raise the cloud pin and correct the README is
§4's decision and is not taken here.
