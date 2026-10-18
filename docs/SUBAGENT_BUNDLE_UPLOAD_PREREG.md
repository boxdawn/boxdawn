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
