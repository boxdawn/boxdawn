# Sub-agent Bundle Upload — Pre-registration

**Scope.** `boxdawn submit` sends a session's sub-agent transcripts in the
same request as the session, and the server analyzes them together. The cloud
report then counts sub-agent spend, as the local report has since 0.5.19.
**Written.** 2026-10-18, before any code change. Engine `main` at `1b3f496`,
cloud `main` at `47b22a1`.
**Code and results** follow as separate commits: cloud first, then engine.

## 0. Why

- 0.5.19 (`#292`): `analyze <sid>.jsonl` also reads `<sid>/subagents/*.jsonl`.
- 0.5.19 (`#293`, `SESSION_CLOSE_RULE_PREREG.md` §10 R3a): a sub-agent file is
  no longer submitted on its own, because it carries the parent's `sessionId`
  and the server's upsert replaced the parent's row with it.
- So the cloud receives the parent only and counts the parent alone. For a
  session with sub-agents, the hosted report is lower than the local one.

The server already runs the same CLI on a temp file
(`app.py` `_run_analyzer`). If the sub-agent files sit beside that temp file
in the same layout, the 0.5.19 adapter reads them with no analyzer change.

## 1. Wire format (frozen)

- The existing part stays: `name="file"`, the session transcript.
- Zero or more extra parts: `name="subagent"`, `filename="agent-<id>.jsonl"`,
  one per file in `<sid>/subagents/*.jsonl`, in sorted order. This is the set
  the adapter and the guard read.
- No new header and no version field. A request with no `subagent` part is
  today's request byte for byte, apart from the random boundary.

## 2. Server (frozen)

1. `/analyze` accepts `subagent: list[UploadFile]`, default empty.
2. **Size.** The 16 MiB limit applies to the **sum** of all parts. A bundle
   over it gets 413, as a single file does today.
3. **Names.** Each `subagent` filename must match `^agent-[A-Za-z0-9_-]+\.jsonl$`
   after taking its basename. Otherwise 422 `bad_subagent_name`. Nothing from
   the client becomes a path component except a name that passed this check.
4. **Layout.** `trace<suffix>` as today, plus `trace/subagents/<name>` per part.
   The CLI then runs unchanged.
5. **Background path.** `analyze_job` gets the parts as `(name, bytes)` pairs.
6. **`payload_sha256`.** With no sub-agent part, `sha256(file)`, unchanged.
   With parts, `sha256` over the file bytes, then for each part in sorted
   name order, the name, a NUL byte, and its bytes. A different sub-agent
   file gives a different hash. The column is recorded only; the upsert key
   is `(project_id, trace_id, params_key)` (migration 0018).
7. The browser upload sends one file, so it is unchanged.

## 3. Client (frozen)

1. `submit_file(path)` adds the `subagent` parts when
   `path.with_suffix("") / "subagents"` is a directory. `_multipart` is the
   only place that builds the body.
2. **Size checks** (`_refused_for_size`, `refused_too_large`) use the bundle's
   total bytes, which is what the server measures.
3. **Ledger** stays keyed by the parent's path. A sub-agent transcript is
   complete before its parent's next write, so a parent with new content is
   the trigger, and R1 is judged on the parent alone.
4. **Order of deployment:** server first. An old client never sends a
   `subagent` part. A new client against an old server: the extra parts are
   ignored, which is the 0.5.19 behaviour. This is tested in §4 P4 and not
   assumed.

## 4. Predictions (frozen)

- **P1. Old shape, same answer.** A single-file request to the new server
  gives the same report as the old server, except `analyzed`. Tested on the
  cited trace and on 3 trace-commons sessions, run locally through the
  endpoint function.
- **P2. Bundle = local.** For the six local sessions with sub-agents, a
  bundled request gives `total_analyzed_cost` equal to local `boxdawn analyze`
  on the parent within 1e-6, and so equal to the guard.
- **P3. Size is the sum.** A bundle whose parts are each under the limit but
  whose sum is over gets 413.
- **P4. Old server tolerates the new client.** The current endpoint, given a
  request with `subagent` parts, answers as it does without them: same
  report, except `analyzed`.
- **P5. A bad name is refused.** `../x.jsonl`, `agent-1.json` and `x.jsonl`
  get 422 `bad_subagent_name`, and nothing is written outside the temp dir.
- **P6. Without sub-agents the client body is unchanged.** For a session with
  no `subagents/` directory, the body equals today's after replacing the
  boundary.

## 5. Stop conditions

- P1 or P4 fails: stop. Mixed versions would then change answers in
  production.
- P2 fails: the server and the local CLI disagree on one bundle. Find out why
  before either ships.

## 6. What this does not settle

- **Rows already uploaded.** They keep their values. A parent is re-sent
  only when it has new content.
- **A sub-agent still being written when its parent closes.** None observed.
  If it happens, its partial lines are sent. The adapter raises on a
  truncated line (`_load_jsonl`), so the request fails with 422 and the ledger
  records it for retry.
- **Attribution** (`cross_agent_repeat` on Claude Code). Not in this stage.

## 7. Shipping and notice

- Cloud deploys first, with the 0.5.19 pin unchanged.
- The engine change ships in the next release. It changes what `submit`
  sends and adds a request shape, so the web gets the "cloud CLI change"
  notice. The response schema does not change.

## 8. Added before merge, from the web session's review (2026-10-18)

The web's copy quotes these values, and the copy must be live before the
client ships.

### 8.1 The verification judge reads sub-agent calls — found while answering

`verification_judge._user_texts` and `_assistant_texts`
(`src/clew/detect/llm_judge/verification_judge.py:163,190`) walk every entry of
`metadata["llm_calls"]`. Since 0.5.19 that list includes sub-agent calls
(`#292`). A sub-agent's first user message is the prompt the main agent wrote
to it, so it is read as **something the user said**. `#292`'s pre-registration
said detectors were unchanged and checked `context_resend` only; the judge was
not checked. Today this reaches only a local run with `--verification`,
because the server never has the `subagents/` directory. A bundle would carry
it to the hosted judge.

**Frozen:** before the bundle ships, the judge reads main-conversation calls
only (`conversation` absent or `"main"`). Sub-agent content is **not** sent to
the judge model. Prediction **P7**: on the six local sessions, the judge's
input text is identical to a run with the `subagents/` directory removed. On
traces without sub-agents, the judge input is unchanged (P1 covers it).

### 8.2 Values the copy can quote

1. **Judge input:** main conversation only (§8.1). Sub-agent files are
   analyzed for cost and resend, and are not sent to the judge model.
2. **Size:** 16 MiB on the **sum** of the session file and its sub-agent files.
   Over it, 413, the same code as a single file over it, whichever part is
   large. The client records the bundle total as `refused_bytes`.
3. **`submit --dry-run`** lists, under each session, its sub-agent files with
   their sizes and the bundle total. What is listed is exactly what is sent.
   Prediction **P8**: for a session with sub-agents, the dry-run lists the
   same file set that `_multipart` puts in the body.
4. **Order:** (a) cloud deploy that accepts `subagent` parts, harmless to
   today's client (P1). (b) Web copy live. (c) Engine release with the client
   change. The engine does not release (c) before the web confirms (b).

## 9. Amendment before code — P7 is one of three (2026-10-18)

Written on `main` at `ada0835`, before the fix. The fix ships alone as 0.5.20,
ahead of the bundle (decided 2026-10-18).

**What §8.1 missed.** Before writing the fix I listed every reader of
`metadata["llm_calls"]` outside ingest. Three of them assume the list is one
conversation, and since 0.5.19 it is not:

| Reader | Assumption | Effect with sub-agent calls appended |
|---|---|---|
| `verification_judge._user_texts` / `_assistant_texts` (`:163,190`) | every user message is the user's | a sub-agent's prompt, written by the main agent, is read as the user's words |
| `redundant_read._next_llm_call_after` (`:212-229`) | the list is in time order, and the last entry is the latest main call | a read after the last main call takes a sub-agent call's rate (its fallback is `llm_calls[-1]`) |
| `semantic_duplicate` candidate pairs (`:206-224`) | two calls are two requests of one conversation | a main chunk and a sub-agent chunk can be judged a paraphrased resend |

The other readers are correct with sub-agent calls in the list:
`report/_model.py`, `metrics/waste_rate.py` and `guard.py` sum cost, which is
the point of `#292`. `context_resend` was tested: 0 of 29,506 events cross
conversations (`CC_SUBAGENT_COST_RESULTS.md` P3). The `__main__` count is a
display.

**Frozen fix.** One helper, `main_conversation_calls(trace)`, returns the
calls whose `conversation` is absent or `"main"`.

- The judge and `redundant_read` read only those calls. `redundant_read`'s
  candidates are main-conversation tool spans, so their next call is a
  main-conversation call.
- `semantic_duplicate` pairs two chunks only when their calls share a
  conversation. Sub-agent resends inside one sub-agent stay in scope, as
  they do for `context_resend`.

**Predictions.**

- **P7** (unchanged): on the six local sessions, `render_trace_for_judge`
  with the `subagents/` directory present equals it with the directory
  removed.
- **P9**: on the six local sessions, the `redundant_read` result with the
  directory present equals it with the directory removed, field by field.
- **P10**: on the six local sessions, no `semantic_duplicate` candidate pair
  joins two conversations. Counted with a stub judge, so no model is called.
- **P1′**: traces without a `subagents/` directory are unchanged: the 28
  trace-commons sessions and the cited trace, analyze JSON field by field
  except `analyzed`.

Stop if P1′ fails.

### 9.1 Results (2026-10-18)

Code `e44a828`. "Before" is a worktree of `ada0835`. Probe scripts are
uncommitted (`field_test/diagnostics/_llm_calls_one_conversation_2026_10_18/`).

| Session | P7 judge input equal (before → after) | P9 `redundant_read` equal | P10 cross-conversation semantic pairs (before → after) |
|---|---|---|---|
| `6f45b92c` | ✗ → ✅ | ✅ → ✅ | 1 → 0 (of 2 → 1) |
| `083ffa23` | ✗ → ✅ | ✅ → ✅ | 1 → 0 (of 3 → 2) |
| `14de1ba6` | ✗ → ✅ | ✅ → ✅ | 1 → 0 (of 1 → 0) |
| `b7995abe` | ✗ → ✅ | ✅ → ✅ | 0 → 0 (of 1 → 1) |
| `86d2d89f` | ✗ → ✅ | ✅ → ✅ | 1 → 0 (of 2 → 1) |
| `ee41edd2` | ✗ → ✅ | ✅ → ✅ | 33 → 0 (of 961 → 928) |

- **P7 ✅** 6/6. Before the fix, 6/6 differed.
- **P9 ✅** 6/6, but it was already equal before the fix: no read in these six
  sessions comes after the last main call, so the defect is not exercised by
  this data. A unit test exercises it, and fails on the unfixed code.
- **P10 ✅** 0 cross-conversation pairs. Before the fix, 5 of 6 sessions had
  some (37 in total). Same-conversation pairs are kept: 961 − 33 = 928.
- **P1′ ✅** 29/29 traces without `subagents/` identical except `analyzed`.
- The default `analyze` report of the six sub-agent sessions is also identical
  before and after. The judge and `semantic_duplicate` are opt-in, and
  `redundant_read` did not move. What changes is the input to
  `--verification` and `--llm-judge` on traces with sub-agents.
- Suite: 1201 passed, 1 xfailed.

## 10. Results — stage (a), the server (2026-10-18)

Code: boxdawn-cloud `feat/subagent-bundle` (`cloud#45`). Measured locally
through FastAPI's `TestClient` (the multipart HTTP shape, not a direct
function call) with the real analyzer: the `boxdawn` CLI 0.5.20, an editable install of
engine `main` at `e4410d9` (the code released as 0.5.20). "Old" is cloud `main` at `f1f7880`, the live deploy. Requests were
anonymous, so nothing was stored. Scripts uncommitted.

| | Prediction | Result |
|---|---|---|
| P1 | Old-shape request: new server = old | ✅ 4/4 identical except `analyzed`: the cited trace and the three smallest trace-commons sessions |
| P2 | Bundle total = local `boxdawn analyze` | ✅ 6/6 within 1e-6, e.g. `ee41edd2` $42.98736715 both. The old server on the same bundle gives the parent alone ($42.96623800) |
| P3 | Parts each under the limit, sum over → 413 | ✅ new 413 (two 9 MiB parts). The old server answered 200: it ignores the parts |
| P4 | Old server ignores `subagent` parts | ✅ 6/6: the bundle's report is identical to the parent-only report on the old server |
| P5 | Bad names → 422 `bad_subagent_name` | ✅ 3/3 (`../x.jsonl`, `agent-1.json`, `x.jsonl`). The check runs before anything is written |

Not measured here: P6 and P8 (client, stage (c)), and P7 (shipped in 0.5.20,
§9.1). The deployed server is not measured until (a) is deployed.

## 11. Results — stage (c), the client (2026-10-18)

Code `ced9df7` on `feat/submit-subagent-bundle`. **Not released**: the release
waits for the web to confirm its copy is live (§8.2 order). Scripts
uncommitted (`field_test/diagnostics/_submit_bundle_client_2026_10_18/`).

| | Prediction | Result |
|---|---|---|
| P6 | Without `subagents/`, the body is today's, boundary aside | ✅ 6/6 sha256-equal with the boundary replaced, measured before and after the change (cited trace and five trace-commons sessions). A test asserts the bytes |
| P8 | Dry-run lists the file set the body carries | ✅ 6/6 local sessions: `file` then each sub-agent part, in the order `subagent_files` gives. A test runs `run(dry_run=True)` and reads the `+ agent-…` lines |

**End to end against the live server** (stage (a), `ba0d168`, anonymous, not
stored): the body `_multipart` builds, sent as is, gave $0.00914996 for
`6f45b92c` and $0.01291494 for `86d2d89f`, equal to local `boxdawn analyze`
on each. So FastAPI parses the hand-built multipart with more than one part.

**A first P6 run was void.** The patch script stopped on a string it could
not match and wrote nothing. The P6 check then compared the old code with
itself and printed 6/6. The run reported above came after the patch was
applied and the diff was read.

**Known limit, as frozen.** Every `subagents/*.jsonl` file is sent. A file
whose name does not match the server's `agent-<id>.jsonl` would make the
whole session 422, and the ledger would retry it on every sweep. Every
sub-agent file observed is named that way (6/6 local). Not handled here.
