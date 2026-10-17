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

## What this does not establish

- **Not measured: the effect on published figures.** `context_resend`
  apportions each call's billed input across its chunks by those chunks'
  token lengths. Base64 that is counted by length but not billed that way
  gives image and signature chunks more weight than they had in the bill. Each
  call's resent tokens are clamped to its bill, so totals cannot exceed it,
  but the resend share can move. On Corpus A (0.8449 / 0.9916) this has not
  been measured.
- **Not fixed.** Changing how chunks are counted changes the detector and
  goes through its own pre-registration.
