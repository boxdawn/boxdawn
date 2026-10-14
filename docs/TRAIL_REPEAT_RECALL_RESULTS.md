# Results — the shipped `repeat` detector against TRAIL's labels

Pre-registration: `docs/TRAIL_REPEAT_RECALL_PREREG.md` (merged `500acbe`, PR
`#262`), written and merged before any of this was run. Revision
`b424ce63d5973d5dcd7169b1bc3c07ccdee276d1`. Pool hash check: **PASS** (30 / 15 /
27, three sha256 match). Cost: **zero** — no judge, no API key, no network.

## 0. 🔴 The stop condition fired, and the answer to it is not what it names

§8's first stop condition: *"S0 misses 10 or more of the 30 → stop. The question
is then whether our ingest carries TRAIL's tool spans."*

**S0 missed 15 of 30.** The question was asked and the answer is **no defect**:

| the 30 records, by the raw kind of the span the annotator pointed at | n |
|---|---:|
| `TOOL` — present after preprocessing, scored through the funnel | **15** |
| `LLM` (all named `LiteLLMModel.__call__`, all carrying `output.value`) | **15** |

Nothing was lost. Every one of those 15 LLM spans **survives ingest as an
`llm_calls` entry** (15 of 15, checked by id) — the adapter converts LLM spans
into `llm_calls` for the resend detector rather than emitting them as spans. On
the pool's 23 traces the adapter also produces **242 tool spans against 242
`"TOOL"` occurrences in the raw payload — ratio 1.000**.

⇒ 🔴 **Half this pool points at a locus our `repeat` axis structurally cannot
read.** `find_repeat_candidates` groups *spans*; an LLM call is visible only to
`context_resend`, and this same pool coded `context_resend` (D2) as **0**. The
pool that passed the mapping gate is half unusable for the detector it was
assembled to test.

**0.1 Why the mapping study could not see this.** `TRAIL_CANDIDATE_MAPPING` coded
each record by **construct** — "is this the thing our waste axis counts" — and
that question is about the sentence the annotator wrote. Whether the **locus**
they attached it to is a span our detector reads is a different question, and it
was never asked. Both codings are correct; they are about different things.

## 1. The funnel, every stage reported (§4)

S0 = present after `preprocess_trace` with `span_kind == "tool"`.
S1 = the labelled span is a member of a `find_repeat_candidates` pair (n = 2),
the loose rule frozen in §3.1. S2 = that pair survives `confirm_pair`.

| subset | n | S0 | S1 | **S2** | S2b (in `waste_span_ids`) |
|---|---:|---:|---:|---:|---:|
| `R_all` | 30 | 15 | 7 | **0** | 0 |
| `R_D1` | 27 | 15 | 7 | **0** | 0 |
| `R_clean` | 15 | 5 | 0 | **0** | 0 |
| **`R_clean_D1`** (headline) | **12** | **5** | **0** | **0** | 0 |
| `page_down_args` only | 15 | 10 | 7 | **0** | 0 |
| `D3` only | 3 | 0 | 0 | 0 | 0 |

Strict rule (§3.2, reported as sensitivity): both members of the pair carry an
annotator label — **0 of 30** when the label must be `Resource Abuse`,
**3 of 30** when any TRAIL category counts.

**1.1 🔴 S2 is zero everywhere, including where S1 fired.** Seven records reached
a candidate pair and **none** survived the cascade. The gate they failed is the
tool branch's byte identity (`cascade.py:5-6`: tool pairs are sha256-compared
and phi is never invoked). The repeated `page_down` calls share a tool and a
normalised input and return **different output**.

**1.2 The clean subset produces nothing to match.** On the 10 traces holding the
15 non-`page_down` records, `find_repeat_candidates` returns **0 pairs of any
kind**. Five of those records' spans are present; none is in a pair.

## 2. What we fire — published, with the sentence it requires (§5)

| | the 23 pool traces | the 10 clean traces |
|---|---:|---:|
| candidate pairs, all kinds | **52** | **0** |
| of which tool pairs | 49 | 0 |
| pairs confirmed by the cascade | **2** | 0 |
| spans in `waste_span_ids` | **2** | 0 |

🔴 **This count is not a false-positive count.** TRAIL's labels are not
exhaustive, so a pair with no label on it is **unverified, not wrong**. The
sentence travels with the number wherever it is cited (§5, decision of
2026-10-14).

Note the shape of it: 52 candidates, 2 confirmed. On this corpus the cascade
rejects 50 of 52 — the opposite of a noisy detector, and the same gate that
produced the zero in §1.1.

## 3. Predictions scored (§7)

| # | Prediction | Measured | Verdict |
|---|---|---|---|
| **P1** | S0 at least 26 of 30 | **15** | 🔴 **rejected** |
| **P2** | S1 at least 13 of the 15 `page_down_args` | **7** (of the 10 that arrived, 7 paired) | 🔴 **rejected** |
| **P3** | `R_clean_D1` at S2 between 4 and 8 | **0** | 🔴 **rejected** |
| **P4** | `R_all` share higher than `R_clean` share | at S1 **0.233 vs 0.000** — holds; at S2 both **0** — not evaluable | partially evaluable |
| **P5** | S1 to S2 attrition dominates | S0 loses **15**, S1 loses **8**, S2 loses **7** | 🔴 **rejected** — the dominant loss is S0, which §4 says is not a detector result |
| **P6** | D3's three records are missed | missed — but **all three never arrived as spans** (S0 = 0/3) | held, **for the wrong reason** |
| **P7** | pairs on the pool traces between 30 and 90 | **52** | ✅ held |

Four rejected, one held for the wrong reason, one held, one partly evaluable.
🔴 The bias I declared in §7 was that I **under**-predict this corpus. This time
I over-predicted it at every stage, so the declared bias did not protect the
predictions — it was the wrong bias, stated with confidence.

## 4. What this does and does not license

**Does:** the headline `R_clean_D1` is **0 of 12**, and this study cannot
separate "the detector does not fire on real duplicates" from "the pool does not
reach the detector", because 7 of those 12 point at LLM calls and the other 5
sit in traces where the detector produces no pairs at all.

🔴 **Does not:**
- Not a precision figure. §1 of the pre-registration says why, and nothing here
  changes it.
- Not a statement about Claude Code. Every published figure is measured on CC
  traces, and this pool contains none.
- 🔴 **Not "the `repeat` detector has 0% recall".** The measured sentence is
  narrower: *on the 12 TRAIL records that are neither the `page_down` harness
  family nor the redundant-read sub-code, the shipped pipeline reported none* —
  with 7 of the 12 unreadable by that detector by construction.
- Not evidence the cascade's byte-identity gate is wrong. It is evidence the gate
  is **decisive on this corpus**: 50 of 52 candidates die there.

## 5. What would actually test this detector

Named here so the next attempt does not re-derive it:

1. **A pool keyed by locus, not only by construct.** Any future mapping study has
   to record whether the labelled span is a TOOL span, because half of this one
   was spent on records our span-based detector cannot see.
2. **The LLM half belongs to `context_resend`,** which this pool coded as D2 = 0
   — so testing it needs a different pool, not this one re-cut.
3. **The byte-identity gate is the thing to study next.** 50 of 52 candidates die
   at it on TRAIL, and 0 of 13 recovered pairs were byte-equal earlier this week.
   Whether that gate is right is a question with a measurable answer, and no pool
   has been assembled for it.

Diagnostics (uncommitted, raw counts only): `_trail_repeat_pool`,
`_trail_repeat_recall`, `_trail_recall_s0_cause` and their `.RESULTS.json`.
TRAIL label text is not reproduced anywhere in this document.
