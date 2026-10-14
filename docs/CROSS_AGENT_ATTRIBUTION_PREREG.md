# Pre-registration — attributing a repeat to the agent that made it, and a separate label when two agents duplicate each other

Status: **pre-registration.** Written and merged before any code change. Every
number in §1 was measured first; §4's predictions were written before the
implementation existed.

## 0. Why this document exists

The product's public positioning is that the waste sits **between** agents. Two
of the four deterministic detectors do the opposite: `find_repeat_candidates`
(`structural.py:72-75`) and `find_redundant_reads` (`redundant_read.py:309-313`)
**drop** a candidate pair whose two spans have different nearest AGENT
ancestors. That gate is SPEC §16.

Measuring it turned up something smaller and more concrete than the positioning
gap, and it is the reason this document leads with a bug rather than a feature:

🔴 **The gate is deleting true findings.** On TRAIL's gaia split it drops **13**
tool pairs that share a tool and a normalised input. All 13 sit under two
*invocations of the same agent kind* (`ToolCallingAgent.run` on both sides), so
they are ordinary repeats — the gate removes them only because each invocation
got its own AGENT span.

🔴 **And whether a cross-agent duplicate is detected at all depends on the
producer, not on any decision of ours.** The gate keys on AGENT spans:

| producer | AGENT spans | gate | a cross-agent duplicate |
|---|---|---|---|
| TRAIL (smolagents) | **yes** — 167 survive preprocessing | fires | **dropped** |
| LangGraph (standard OpenInference instrumentation) | **no** — nodes arrive as CHAIN | never fires | **reported, as plain `repeat`** |

Same event, opposite outcome, decided by an instrumentation accident. That is
what this change fixes.

## 1. Structural facts, measured before this rule was written

### 1.1 What the pipeline already carries

Measured on a LangGraph graph (manager + `worker_a` + `worker_b`, both workers
calling one tool with the same input) run with a **fake chat model** — zero API
calls, zero dollars:

| | |
|---|---|
| raw OpenInference kinds | CHAIN 4 · LLM 3 · TOOL 2 · **AGENT 0** |
| `graph.node.id` (what `langgraph.py:69` reads for agent identity) | **absent on all 9 spans** |
| CHAIN names surviving `filter_router_spans` | `LangGraph`, **`worker_a`**, **`worker_b`** (`manager` removed as a router) |
| the two tool spans' normalised input | **identical** |
| `find_repeat_candidates` today | **1 pair — already found** |
| their nearest AGENT ancestor | **None on both** → gate not applied → kept |
| their nearest CHAIN ancestor | **`worker_a` vs `worker_b`** |

⇒ The worker identity is in the trace and survives preprocessing. Nothing reads
it. The gap is **attribution, not detection**.

### 1.2 Identity: kind, not invocation — and the choice changes the count

| definition of "a different agent" | CC (120) | TRAIL gaia | TRAIL swe | the $0 synthetic |
|---|---:|---:|---:|---:|
| **invocation** (the AGENT span instance) | 0 | **13** (4 traces) | 0 | 1 |
| **kind** (`agent_or_node_id`) | 0 | **0** | 0 | **1** |

TRAIL's 13 are `ToolCallingAgent.run` on both sides. Under *invocation* they
read as "between agents"; under *kind* they read as what they are — the same
agent called twice. **Kind is the definition this document freezes**, because
the other one would relabel ordinary repeats as cross-agent and inflate exactly
the claim the positioning already overstates.

🔴 Of those 13: byte-identical output **0 / 13**, an absent output side **0 / 13**
— the two invocations genuinely got different results.

### 1.3 The partition, measured

Identity rule under test:

```
identity(span) = nearest ancestor with span_kind == "agent"  -> its agent_or_node_id
                 else nearest ancestor with span_kind == "chain" -> its agent_or_node_id
                 else None
```

| corpus | `repeat` tool pairs today | new `repeat` | delta | new `cross_agent_repeat` |
|---|---:|---:|---:|---:|
| Claude Code, 120 of `mimo-cc-1k`, seed 42 | 12 | **12** | **+0** | **0** |
| TRAIL gaia (117) | 73 | **86** | **+13** | **0** |
| TRAIL swe_bench (30) | 0 | 0 | +0 | 0 |
| the $0 LangGraph synthetic | 1 | 0 | −1 | **1** |

Two facts follow and both are load-bearing:

- **On Claude Code nothing moves.** Every CC trace resolves to exactly **one**
  tool owner (103 of 120) or none (17); the identity comes from the chain
  ancestor in all 495 tool spans. Every published figure in the README is
  measured on CC traces, so **the published figures are untouched** — not
  because we assert it, but because the pairs that would have to move number 0.
- **On TRAIL `repeat` goes up by 13.** Those are the findings §0 says the gate
  is deleting. TRAIL carries no published figure, so this moves nothing public;
  it is reported here so the increase is never mistaken for a regression.

### 1.4 🔴 The new label fires on nothing we hold

Under the frozen definition, `cross_agent_repeat` is **0 on Claude Code, 0 on
TRAIL gaia, 0 on TRAIL swe_bench**. The only positive case in existence is the
synthetic graph in §1.1, which we wrote. This is stated here, in the
pre-registration, so that no later document has to discover it.

## 2. What is frozen by this document

**2.1 The label is a report-stage label, not a fifth detector.** It is assigned
where `requery_known` is assigned — `_enrich._classify_pattern` (`report/_enrich.py:499`), on candidates
the existing detectors already produced (CLAUDE.md §1). The detector set stays
**four** and `waste_rate.py`'s frozen position (`WASTE_RATE_METRIC_PREREG` §1,
§3) is not reopened. Making cross-agent duplication a first-class detector with
its own threshold would be a different document.

**2.2 Identity is the agent's kind**, per §1.2, resolved by the rule in §1.3.
`None` on either side means the pair is **not** cross-agent.

**2.3 The partition is exclusive and additive.** A pair is `repeat` **or**
`cross_agent_repeat`, never both:

- identities equal, or either side `None` → `repeat`
- identities differ and neither is `None` → `cross_agent_repeat`

**2.4 The SPEC §16 gate stops dropping and starts classifying.** No pair is
discarded for having different AGENT ancestors. The same change applies to
`redundant_read.py:309-313`, which reuses the gate.

**2.5 Both detectors keep every other gate.** `redundant_read`'s state check (no
intervening write, no Bash/PowerShell in the interval) is unchanged;
`cascade`'s refusal to pair on an absent output is unchanged; `n` is unchanged.

## 3. What is explicitly NOT changed

- **No published number.** §1.3 measured the CC movement as **0 pairs**.
- **No pricing, no cost model, no `waste_rate` basis.**
- **No new dependency**, and no change to any adapter's output. The identity rule
  reads spans that already exist.
- **The homepage claim is not made true by this.** Shipping a label that reports
  0 on every corpus we hold does not license "the waste is between your agents".
  §6 says what would.

## 4. Predictions, written before the implementation exists

| # | Prediction | What rejects it |
|---|---|---|
| **P1** | CC 120-sample after the change: `repeat` tool pairs **exactly 12**, `cross_agent_repeat` **0** | any other pair of numbers |
| **P2** | TRAIL gaia after the change: `repeat` **86**, `cross_agent_repeat` **0** | any other pair |
| **P3** | The $0 synthetic after the change: `repeat` **0**, `cross_agent_repeat` **1**, and the label names **`worker_a`** and **`worker_b`** | the label missing, or naming something else |
| **P4** | 🔴 **trace-commons, all 28 CC sessions** (the corpus behind the published figures): `cross_agent_repeat` **0** and every `repeat`/waste figure **byte-identical** to the pre-change run | any movement at all — see §5 |
| **P5** | Full local suite green, with no existing test edited; new tests only | an existing assertion changing |
| **P6** | `redundant_read` on CC 120-sample: finding count **unchanged** | any change |
| **P7** | No report renders a `cross_agent_repeat` section on a trace with fewer than two distinct identities | a section on a single-identity trace |

🔴 **Named in advance — the outcome that looks like success and is not.** If
`cross_agent_repeat` comes back non-zero on Claude Code, that is **not** a
discovery: it means the chain-ancestor fallback is reading something that is not
an agent (CC's chain spans are session scaffolding, not workers). Treat a
non-zero CC count as a **failure of the identity rule**, stop, and redesign.

## 5. KILL / stop conditions, fixed now

- **Any published CC figure moves** → stop, do not ship. The change's whole
  licence is that it is additive on CC, and §1.3 measured that as 0 pairs.
- **`cross_agent_repeat` > 0 on Claude Code** → the identity rule is wrong (§4's
  named trap). Stop and redesign rather than report the count.
- **P2's +13 does not appear** → the gate is not the thing that was dropping
  them, and §0's diagnosis is wrong. Stop and re-measure before touching more.
- **Any existing test needs editing to pass** → treat as an intentional-drift
  violation, not as a test to update.

## 6. What this cannot settle

- **Prevalence.** The label reports 0 everywhere we can measure. Nothing here
  says cross-agent duplication is common, rare, or expensive.
- **Precision.** With no positive case outside a synthetic graph we wrote, there
  is no pool to measure precision on. A precision study needs real multi-agent
  traces, and no public corpus we examined carries them with tool inputs **and**
  tokens: Exgentic filters out `invoke_agent` parents, MAST-Data's trace field is
  a raw text log, and Who&When and HAL carry no licence statement.
- **Dollars.** Cost attribution for a cross-agent pair is unaddressed; the
  existing `repeat` cost model is unchanged by this document.
- **Whether a cross-agent duplicate is waste at all.** Two agents reaching the
  same tool with the same input may be deliberate cross-checking. This document
  labels the structure; it does not judge it. The judgement needs the pool
  §6 says we do not have.
- **The Claude Code path.** CC traces carry no agent at all (0 of 120, and
  `isSidechain` is `false` on all 25,931 local transcript lines), so a CC user
  sees nothing from this change. Subagent support in the CC adapter is a
  separate document.

## 7. Order of work

1. This document, merged, before any code change. (rule 8)
2. Code: the identity helper, the partition, the gate change in both detectors,
   the report label. One commit, no behaviour beyond §2.
3. Dry-run reproducing **every** count in §1.3 and scoring P1–P7, including the
   trace-commons run P4 names.
4. A results section in this document, with the predictions scored — the failures
   too.

**No judge call. No API spend.** Every measurement behind this document was made
with local corpora and a fake chat model.

## 8. Scope amendment, before any code (2026-10-14)

§1.3 and §1.4 were measured on **tool** pairs — the dry-run behind them
(`_cross_agent_partition_dryrun.py`) skips every span whose `span_kind` is not
`"tool"`. §2.4's wording ("No pair is discarded for having different AGENT
ancestors") reads wider than that: it covers the groups keyed by
`agent_or_node_id` alone, where no input gate applies. The two were written as
if they said the same thing. They do not, and the difference was measured
before the implementation existed:

| corpus | non-tool pairs today | non-tool `repeat` if the gate goes | non-tool `cross_agent_repeat` | traces |
|---|---:|---:|---:|---:|
| Claude Code, 120 of `mimo-cc-1k`, seed 42 | 0 | 0 | **0** | 0 |
| TRAIL gaia (117) | 10 | 56 | **86** | **39** |
| TRAIL swe_bench (30) | 0 | 0 | 0 | 0 |

🔴 All 86 are `chain`/`chain` pairs — the E3 shape the gate was added for
(`Step 1` under `CodeAgent.run` against `Step 1` under `ToolCallingAgent.run`,
same topical vocabulary, legitimately different roles). Under the wide reading
**§1.4 is false and P2 is rejected**: the label would fire 86 times on a corpus
the pre-registration says it fires 0 times on. Two shipped tests
(`test_repeat_different_agent_parent_blocked`, `test_repeat_mixed_depth_blocked`)
assert that drop, so the wide reading also trips §5's last KILL condition —
an existing test would have to be edited.

**8.1 Frozen: the partition is scoped to tool pairs.** A pair is eligible for
`cross_agent_repeat` only when both spans have `span_kind == "tool"` — the pairs
that carry the `(tool name, normalised input)` gate, and the only pairs §1.3
measured. For every other kind the SPEC §16 gate stays exactly as shipped: a
pair whose nearest AGENT ancestors differ is still dropped. This narrows §2.4;
it changes no number in §1 and no prediction in §4.

**8.2 `redundant_read`'s half of §2.4 is behaviour-identical here.** Measured
the same way — the shipped detector against the detector with the gate
neutralised:

| corpus | events shipped | events with the gate off | added | waste tokens (both) |
|---|---:|---:|---:|---:|
| Claude Code, 120 of `mimo-cc-1k`, seed 42 | 8 | 8 | **0** | 269 |
| TRAIL gaia (117) | 0 | 0 | 0 | 0 |
| TRAIL swe_bench (30) | 0 | 0 | 0 | 0 |

The gate drops **nothing** there on any corpus we hold, so removing it is a
no-op on all three and P6 holds by measurement rather than by argument. No label
is added to `RedundantReadEvent`: there is no positive case to label, and its
JSON event schema is pinned by an exact key-set assertion in a shipped test
(`tests/report/test_redundant_read_report_integration.py`), which §5 forbids
editing. 🔴 **Known limit, stated here:** until that schema is reopened, a
cross-agent redundant read would be reported as an ordinary redundant read.

**8.3 What this amendment does not settle.** Whether the 86 `chain`/`chain`
pairs are waste, false positives, or genuine cross-agent duplication is
unexamined. They are excluded here because the gate's original justification
(E3) is about exactly that shape and because no measurement in §1 covers them —
not because they were judged. Deciding them needs the chain spans read one by
one, and that is a separate document.

Decision owner: 세원님, 2026-10-14. Measurements:
`_cross_agent_nontool_scope.py`, `_cross_agent_redundant_read_scope.py`
(diagnostics, uncommitted; raw counts reproduced above).
