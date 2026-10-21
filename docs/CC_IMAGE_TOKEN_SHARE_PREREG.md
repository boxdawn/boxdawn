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
