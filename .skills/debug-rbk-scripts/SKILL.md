---
name: debug-rbk-scripts
description: Diagnose, test, and collect evidence for RBK 3.x robot scripts and navigation tasks using syspy, MoveFactory/PyIDE RPC sources and logs, syslog, the RBK HTTP API documentation MCP, and insightd/Perfetto traces. Use for script crashes, pyCrashed states, missing Module.getTaskArgs values, get_task/update_cmd/scriptReport failures, stuck RUNNING tasks, MF/PyIDE/ZMQ routing, /navigate tasks, motor or model problems, fork/load/unload behavior, localization drift (MCLoc), map switch failures (BlockMapLoader), DI/message latency, Navigation.hasGoods versus Container state, task-status polling, HTTP endpoint questions, and trace collection under /opt/.data/diagnosis/rbk/trace/event. Start by asking for the exact fault time and taskId, then filter the trace by category (rbk.script.utils_rpc, rbk.nav.MoveFactory, rbk.loc.MCLoc, rbk.loc.BlockMapLoader, rbk.device.DSPChassis) before reading source.
---

# Debug RBK Scripts

Use the robot's public control surfaces and preserve enough evidence to distinguish an RBK defect from a script defect.

## Start Here: Triage

Read [references/triage.md](references/triage.md) first for any new problem. It defines the
mandatory intake and the symptom-to-channel routing. In short:

1. **Ask for the exact fault time first** (wall clock with timezone), plus `taskId`, symptom
   class, RBK full version, and whether it reproduces. Without a time window the trace and
   logs cannot be filtered usefully.
2. Map the time window to one `rbk+common_*.pft.zst` segment and the matching `ide` /
   `scripts` logs.
3. Pick the channel group from the symptom, then query it with `ptcat -g`/`-n` before
   reading any source.

Then come back to the detailed workflow below.

## Intake Checklist

Ask the reporter for these before investigating. Missing items are the usual reason a
debug session stalls.

- Exact fault time (wall clock, timezone). ±1 minute preferred, ±10 minutes acceptable.
- `taskId` if a task was involved.
- One-line symptom: script logic, script dispatch/RPC, navigation, localization, map,
  device/motor, latency, or crash.
- RBK full version and simulation vs real-machine mode.
- Whether it reproduces, and whether a log bundle was exported.

## Channel Routing Cheat Sheet

Full detail and examples in [references/triage.md](references/triage.md).

| Symptom | Category / channel |
| --- | --- |
| Script logic, script dispatch, RPC client/server | `rbk.script.utils_rpc` / `Rc`, `RcError`, `Rs`, `RsError` |
| Script-defined channels (fork, actions, elevator, ...) | `rbk.script.utils_rpc` / `<channel name>` |
| **Fork** script (load/unload, fork motor, policy, recognition) | see [references/fork-channels.md](references/fork-channels.md) — `fork`, `fork.task`, `fork.motor`, `fork.nav`, `fork.policy`, `fork.rec`, `fork.cfg`, `fork.err`, `fork.taskActions` |
| Navigation, action planning, stuck `/navigate` | `rbk.nav.MoveFactory` |
| Pose, drift, confidence, `locMethod` | `rbk.loc.MCLoc` |
| Map load / switch | `rbk.loc.BlockMapLoader` / `changeMap` |
| Motors, DI/DO, sensors, battery | `rbk.device.DSPChassis` (`motorInfo`, `messageDI`, ...) |
| Whole-RBK crash | `syslog` |
| Script process crash | `logs/ide/*.log`, then `logs/scripts/*.log` |

Authoritative per-version channel catalog: resolve `trace.cfg` under the local SDK
checkout or release bundle (see [references/triage.md](references/triage.md) for the
discovery command). If it is unavailable, ask the reporter for their SDK path or version.

## Core Workflow

1. Complete the intake checklist above; get a time window before anything else.
2. Read the repository's `AGENTS.md` and `CLAUDE.md` before changing code.
3. Record the current model, RBK version, task state, container state, errors, and trace-file baseline.
4. Filter the trace by the routed category/channel for the reported window. Read
   [references/triage.md](references/triage.md) for the channel tables and
   [references/tracing.md](references/tracing.md) for `ptcat` and `/sync` mechanics.
5. Prove RBK is healthy before attributing a failure to Python code. Read [references/script-debugging.md](references/script-debugging.md) for known startup, motor, fork-runtime, and cargo-state failure modes.
6. For missing task arguments, `get_task`/`update_cmd` gaps, PyIDE routing, status-report loss, or an MF action stuck in `RUNNING`, read [references/mf-script-rpc.md](references/mf-script-rpc.md). Locate the first missing hop before assigning ownership. Use `Rc` vs `Rs` to prove what the SDK sent versus what the script received.
7. Consult the HTTP OpenAPI MCP before constructing or changing an RBK request. Read [references/http-api.md](references/http-api.md) for the MCP workflow and verified endpoint patterns.
8. Reproduce with a unique task ID through an existing flow test where possible. Poll the exact task ID, not merely the latest global status.
9. Cancel a running navigation through HTTP `/cancelNavigate`. Do not kill the persistent Python script process.
10. During iterative debugging, read the active trace with `ptcat`. When durable evidence is needed, collect the test report, console output, task IDs, status transitions, and an immediately finalized trace. Read [references/tracing.md](references/tracing.md), or run `scripts/collect-rbk-evidence.sh`.
11. To isolate a script-side or syspy defect, or to verify a syspy change, run the script directly against the live RBK with plain `python3` instead of going through MF/PyIDE. Read [references/standalone-probes.md](references/standalone-probes.md) first: it covers the `SCRIPTS_DIR` path trap that makes `cd <scripts dir> && python3 x.py` fail on symlinked installations, the minimal probe skeleton, and how to read the resulting channel from the trace.
12. For DI, sensor, SDK-message, or ZMQ latency, read [references/message-latency.md](references/message-latency.md). Separate publisher-to-reader visibility, API-call duration, action response, and task cleanup before assigning a cause.
13. For the **fork** script (load/unload, fork height, motor commands, obstacle-stop policy, recognition), read [references/fork-channels.md](references/fork-channels.md). Fork is high-frequency and writes nine fixed channels; that reference maps symptom → channel and lists the correlation fields (`taskId` / `phase` / `actionId`) that join an action across channels.
14. Restore temporary defect-reproduction patches. Run `py_compile`, `git diff --check`, targeted tests, and a final state query.

## Reporting a Finding

Lead with the conclusion, then support it with a few quoted log lines. Keep the whole
reply within roughly 50-200 characters of substance (Chinese) or equivalent.

Format:

1. **Conclusion first, one sentence**: what is broken and at which hop/layer, or
   explicitly "inconclusive, need X".
2. **Then 2-4 short bullets**, each citing the decisive line from the log/trace verbatim
   (trim to the meaningful fragment) so the reader can verify it.
3. **Then the next action** (one line) if something is still needed.

Rules:

- Do not narrate the investigation. Report the result and its evidence.
- Do not paste whole log files or long trace dumps; quote only the decisive lines.
- Do not state a cause you cannot tie to a quoted line; say what is unproven instead.
- If the answer is only "not enough information", name exactly which input is missing
  (for example fault time, task ID, or SDK path).

Example:

> 结论：任务参数没丢在 PyIDE，而是 `update_cmd` 之后脚本侧 `getTaskArgs()` 为空。
> - `Rc`：`scriptExecute scriptName=tasks/.../robotTypeE.py args={"args":{...}}` 已下发。
> - `ide`：`update_cmd ... taskId=42` 已转发。
> - `scripts`：`getTaskArgs -> {}`，顶层 `args` 为空。
> 下一步：检查任务体是否把业务值放在顶层 `args` 下。

## Non-Negotiable Safety Rules

- Treat `ss@pyCrashed` as sticky RBK state. Normal error clearing is not sufficient; coordinate a full RBK restart instead of repeatedly mutating the script.
- Treat `walk motor number is not 2 or 4`, `modelName=unknown`, or `motorInfo=[]` as incomplete RBK/model startup until disproved.
- Stop scripts through `/cancelNavigate`; never kill their process as routine cleanup.
- Never call `Motor.isMotorReached()` unless the same action lifecycle successfully called `Motor.setMotorPosition()` first. Reset every commanded motor on finish, failure, cancellation, rejection, and timeout.
- Do not assume `Navigation.hasGoods()` and `Container.hasGoods()` are equivalent. Capture both when diagnosing, but use Container as the logical load/unload lifecycle state.
- Do not restart RBK, insightd, or traced merely to flush logs. Use insightd `/sync`.
- Preserve unrelated worktree changes and untracked files.
- Compare only timestamps from compatible clock domains. Do not subtract `dataNsec` or `perf_counter_ns` from wall-clock trace timestamps.
- Do not infer parameter loss from an empty `get_task` response alone. Prove whether the task used command-line startup or `update_cmd`, and capture the request at MF, PyIDE, and syspy boundaries.
- Do not `cd` into the scripts directory to run a Python probe. On installations where `/opt/.data/rbk/resources/scripts` is a symlink, `__file__` resolves to the real path and `param_server._get_prefix_dir` rejects it with `ValueError: script path error`. Put the literal `/opt/.data/...` path on `sys.path` from another cwd instead ([references/standalone-probes.md](references/standalone-probes.md)).

## HTTP Documentation MCP

Use these tools as the source of truth:

- `mcp__seer_spg_http_api_docs__read_project_oas_gandze`: read the OpenAPI root and available paths.
- `mcp__seer_spg_http_api_docs__read_project_oas_ref_r_f7d7a1b846c1`: expand only the required path or schema `$ref` files.
- `mcp__seer_spg_http_api_docs__refresh_project_oas_gandze`: refresh the cached spec when the RBK version or observed behavior may be newer than the download timestamp.

Do not copy the entire OpenAPI spec into context when one or two `$ref` files answer the question. If the spec and runtime disagree, report both with RBK version and raw request/response evidence.

## Evidence Standard

For every reported defect, retain:

- RBK full version and simulation/real-machine mode.
- Reported fault time window (wall clock, timezone) and the artifacts it selected.
- Model health indicators and relevant motor names/configuration.
- Exact HTTP request payload and response.
- Unique task IDs and timestamps with timezone.
- Task status progression and terminal errors.
- The original task payload, MF `scriptName/scriptStage/scriptArgs`, and the observed `get_task`, `update_cmd`, and `scriptReport` requests for script-dispatch defects.
- Script-side state and HTTP-exposed state when comparing APIs.
- For script/RPC defects, the `Rc` (sent) and `Rs` (received) records plus any `RcError`/`RsError`.
- Finalized `.pft.zst`, `rbk+report.jsonl`, focused insight events, and flow-test JSON/log output.
- The code state used to reproduce and confirmation that temporary changes were restored.
- For latency defects, the last reader state before the edge, the publisher's first changed state, the reader's first observed state, API start/end timestamps, and downstream action/task transitions.

Do not claim a three-round pass when the defect caused skips or failed tasks. Describe each attempted round and why it terminated.
Do not generalize a result from a different script or SDK combination. State the exact control-variable combination that each run proves.
