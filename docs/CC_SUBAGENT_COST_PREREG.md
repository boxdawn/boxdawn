# Claude Code Subagent Cost — Pre-registration

**Scope.** A Claude Code session's report counts what its subagents spent.
Today it counts only the main transcript.
**Written.** 2026-10-18, before any code change, on `main` at `7f81ab9`.
**Code and results** follow as separate commits on the same branch.

## 0. Why, and what the data says first

Claude Code writes each subagent's conversation to its own file beside the
session: `<session>.jsonl` and `<session>/subagents/agent-<id>.jsonl`, with a
`agent-<id>.meta.json` carrying `agentType`, `toolUseId` (the parent's
`Agent` call) and `model`. The CC adapter (`ingest_claude_code_jsonl`) reads
the main file only. Nothing under `subagents/` reaches `llm_calls`, so
`total_analyzed_cost`, `total_llm_input_cost` and the waste-rate denominator
all leave subagent spend out.

The budget guard already counts it. `clew.guard.session_cost`
(`src/clew/guard.py:91-102`) prices the main transcript plus every
`subagents/*.jsonl`. So on one session, the guard and the report give
different totals.

Measured before writing this (diagnostic, uncommitted,
`field_test/diagnostics/_cc_subagent_cost_2026_10_18/`): the six subagent
transcripts on this machine (Claude Code 2.1.234 and 2.1.299), each with
its parent, analyzed with the shipped CLI.

| Subagent | Parent report | Subagent alone | Left out |
|---|---:|---:|---:|
| `a18b56c2` | $0.005260 | $0.004201 | 44.4% |
| `ae076458` | $0.004700 | $0.004450 | 48.6% |
| `ac449695` | $0.007224 | $0.005691 | 44.1% |
| `af4aa01a` | $0.004865 | $0.001929 | 28.4% |
| `abec93b4` | $0.005285 | $0.001940 | 26.9% |
| `a508a7ac` | $42.966238 | $0.021129 | 0.05% |

- 0 of the 12 subagent `message.id`s appear in the parent file.
- `guard.session_cost(parent)` equals parent + subagent report totals on 6/6,
  within 1e-6.
- The first five parents are budget-guard test sessions and are tiny. Their
  shares are not representative. How much real sessions leave out is
  **not known**.

Public data cannot size it. In trace-commons, 8 of 28 sessions call a
subagent (9 calls, all `Explore`), but no `subagents/` files were published
(0/28). The parent's `toolUseResult.totalTokens` appears to be the
subagent's **last turn only**: on the one local transcript that can tell
(`ae076458`, 3 turns), it is 29,847 against a 3-turn sum of 86,822. So it
gives a floor, not a total.

## 1. Mechanism (frozen)

In `ingest_claude_code_jsonl(path)`:

1. Let `sub_dir = path.with_suffix("") / "subagents"`, the directory
   `guard.session_cost` reads. If it is not a directory, nothing below runs
   and the function is unchanged.
2. For each file in `sorted(sub_dir.glob("*.jsonl"))`, the same set the
   guard reads, load its entries and call `_extract_llm_calls` on them
   **separately**, with the same cost tables. Each subagent's history is
   rebuilt from its own entries, as Claude Code sent it. Mixing them into
   the main sequence would corrupt both histories.
3. Append those calls to `llm_calls` after the main calls, in file order.
   Each gets `"conversation": "<agentId>"`, and main calls get
   `"conversation": "main"`.
4. A `message.id` already present is skipped, the guard's rule across files.
5. `ingest_notes` gains `subagent_files` and `subagent_llm_calls`.

## 2. Deliberately not in this stage

- **Tool spans.** Subagent tool calls are not added to `spans`. Adding them
  without an agent span would report main↔subagent overlap as a plain
  `repeat`. Attribution (`cross_agent_repeat`) is a separate stage with its
  own predictions.
- **Turn metadata.** `cc_turn_index`, `cc_usage_pair` and `cc_total_turns`
  stay main-only. Amplification is about the main conversation.
  The invariant `cc_total_turns == len(llm_calls)`
  (`tests/ingest/test_claude_code_llm_calls.py:406,498`) becomes
  `cc_total_turns == number of calls with conversation "main"`. Without a
  `subagents/` directory the two are the same.
- **Detectors.** `context_resend` is not changed. It sees the subagent calls
  in the flat list. Their chunks are hashed with the rest; §4 P3 tests that
  no chunk is shared across conversations.
- **Upload and cloud.** `submit` uploads one file's bytes
  (`src/clew/submit.py:483`). The server never has the sibling directory, so
  cloud results do not change in this stage. Note that `submit.discover`
  recurses `~/.claude/projects` (`submit.py:76-80`), so subagent files are
  already uploaded **as standalone traces** (6 of 80 files on this machine).
  Bundling them with their parent changes the upload contract and is a
  separate stage, with the web session.
- **Async subagents.** For a subagent launched with `isAsync:true`, the
  parent's launch result carries no usage (`status: async_launched`), but the
  subagent's own transcript has it. This stage reads the
  transcript, so it covers both. Not separately tested: one local example.

## 3. Tests

- A fixture session with a `subagents/` directory: calls appended, each with
  `conversation`, totals equal to `guard.session_cost` on the same files.
- A fixture without one: the trace equals today's output field by field.
- A duplicated `message.id` across files is counted once.
- The invariant test of §2 is restated, not deleted.

## 4. Predictions (frozen)

- **P1. Unchanged where there is no `subagents/` directory.** Bit-identical
  analyze JSON (`PYTHONHASHSEED=0`) on the 28 trace-commons sessions and on
  the cited trace `agent-race/claude-code.jsonl`. Corpus A stays
  `union_wr_cost` 0.844933 and `union_wr_char` 0.991595.
- **P2. The report agrees with the guard.** On the six local sessions,
  `total_analyzed_cost` equals `guard.session_cost(parent)["usd"]` within
  1e-6.
- **P3. No chunk crosses conversations.** On the six local sessions, 0
  `context_resend` events have a main-conversation origin and a subagent
  carrier, or the reverse.
- **P4. The large session barely moves.** On `a508a7ac`, `waste_ratio`
  changes by less than 0.001.
- **P5. The suite passes** with only the §2 invariant restated.

## 5. Stop conditions

- P1 fails: stop. Nothing ships; the cause is written up first.
- P3 fails: stop and amend. Cross-conversation matches would mean the
  detector is comparing histories that were never one request.
- P2 fails: the two paths disagree on what a session costs. Find out which is
  wrong before shipping either.

## 6. What this cannot settle

- How much real users' reports leave out. The only real-sized local session
  leaves out 0.05%, and public corpora publish no subagent files.
- Cloud reports. Unchanged until uploads carry the subagent files (§2).
- Whether `totalTokens` is always the last turn. One sample.
- Nested subagents (`spawnDepth` > 1). None observed.

## 7. Shipping

The analysis path changes, so the release raises the Modal pin and triggers
the web notice clause "pin or version raised". Cloud figures do not move
(§2), and the notice says so.
