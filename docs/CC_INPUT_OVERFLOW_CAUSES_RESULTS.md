# Claude Code Input Overflow — Causes

**What this is.** After the compaction fix (0.5.16, `#278`), 1,557 of the 4,354
trace-commons calls still measured more tokens in their reconstructed input
than they were billed for (`docs/CONTEXT_RESEND_DECOMPOSITION_RESULTS.md` §6;
README, Corpus A correction). Two causes were named as images and "one not yet
identified". This document identifies the second one and accounts for every
call.

**Measured.** 2026-10-17, on `main` at `76fbbd4`, over the 28 trace-commons
sessions. It uses the same overflow test as the compaction-fix measurement:
the call's messages are serialized one by one as JSON, counted with
`context_resend._chunk_token_len`, and compared with the call's billed
`input_tokens`. It then repeats the count with each candidate cause removed.
The census script is diagnostic and not committed.

## Result

| Removed from the reconstructed messages | Calls still over their bill |
|---|---:|
| nothing | **1,557** (in 11 of 28 sessions) |
| image blocks | 847 |
| image blocks and thinking-block `signature` fields | **8** |

- **Images: 710 calls.** The tokenizer counts base64 image data by length.
- **Thinking signatures: 839 calls.** This is the unidentified cause. Each
  `thinking` block carries a `signature`, a long base64 string that the
  tokenizer also counts by length. Session `3be5ba0c`, previously noted as
  having neither compaction nor images, accounts for 237 of these.
- **The other 8 are not API calls.** One per session, each is a `<synthetic>`
  entry with zero usage (billed 0, output 0). Claude Code writes these without
  calling the API, so any non-empty input "exceeds" a bill of 0.

The attribution is sequential: images were removed first. A call with both an
image and a signature counts under images.

**No overflow is left unexplained.**

## Effect on published figures

`context_resend` apportions each call's billed input across its chunks by
those chunks' token lengths, so base64 counted by length gives image and
signature chunks more weight than they had in the bill.

**Measured.** 2026-10-18, on `main` at `ec136cc`, over the same 28 sessions,
`PYTHONHASHSEED=0`. Corpus A was measured twice in one process: as is, and
with `_chunk_token_len` counting each chunk after removing its image blocks
and `signature` fields. Nothing else changed. Predictions were written before
the run. The script is diagnostic and not committed.

| | As is | Images and signatures removed |
|---|---:|---:|
| `union_wr_cost` (23 priced) | 124.7402 / 147.6331 = **0.8449** | 124.8520 / 147.6331 = **0.8457** |
| `union_wr_char` | 0.9916 | 0.9916 (bit-identical) |
| `union_sdr_at_10` | 0.9643 | 0.9643 |

- The as-is run reproduces the published figures.
- `union_wr_char` cannot move: it counts the bytes of flagged chunks, and which
  chunks are flagged does not depend on token lengths.
- 14 sessions change, exactly the 14 that contain images or signatures. The
  other 14 are bit-identical. Of the 9 priced sessions that change, 5 fall and
  4 rise: from −0.0612 (`c84c0ad3`, 0.9013 → 0.8401) to +0.0281 (`860618e1`,
  0.8448 → 0.8729). In aggregate they nearly cancel.
- In every changed session the change in `union_waste_cost` equals the change
  in `context_resend` alone, so it does not come from overlap with the other
  detectors.

**The prediction of direction missed.** We predicted `union_wr_cost` would
fall, since nearly all of the inflated tokens sit in chunks the detector flags
as resent. It rose. Resent tokens increased in 13 of the 14 sessions. Not
established: why, and why several sessions lose cost while gaining resent
tokens. One reading, unverified: apportionment is per call, and a call whose
new message carries a screenshot had its resent share pushed down by that
image.

## What this does not establish

- **Not a fix.** Removing images counts them as zero tokens, but images are
  billed. This measurement is one bound, not the corrected value. A fix would
  count each image and signature as it is billed, which has not been checked.
- **`Context Resend Detector 84.5%`** (README) was not re-measured.
- **Not fixed.** Changing how chunks are counted changes the detector and
  goes through its own pre-registration.
