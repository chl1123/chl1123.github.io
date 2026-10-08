# MoveFactory to Script RPC Troubleshooting

Use this reference when task arguments are empty, a script action remains `RUNNING`, PyIDE appears
to stop forwarding, or `get_task`, `update_cmd`, lifecycle control, or `scriptReport` is missing.

## Contents

1. Normal control path
2. Transport and interface contracts
3. Source and version discipline
4. Step-by-step investigation
5. Ownership rules
6. High-risk implementation details
7. Evidence checklist

## Normal Control Path

Establish which of these two task-delivery paths should have run before diagnosing the script.

```text
MoveTask
  -> MoveFactory ActionFactory / ActionExecutor
  -> RunScript::taskplan
  -> SDK RpcClient
  -> ipc:///tmp/cpp2broker.ipc
  -> PyIDE Broker
  -> ipc:///tmp/broker2server.ipc
  -> syspy RpcServer
  -> Module lifecycle method
```

Configured module task scripts are normally prestarted with empty startup arguments:

```text
broker::start [scriptName, {}, true]
  -> Python process starts
  -> register_service(scriptName, methods, "task")
```

Do not treat that empty `{}` as the current MoveTask. A later task is delivered by one of these
paths:

- Persistent configured script: PyIDE forwards `<script>::update_cmd` to the existing process.
- Dead or restart-required script: PyIDE starts the process with `json.dumps(taskArgs)` as its final
  command-line argument and completes the original `update_cmd` request itself.

Before dispatching a new task, MF normally calls `<script>::get_task`. It adds a generated `taskId`
to the task object and calls `update_cmd` only when it does not consider the existing task identical.

The script reports state through a separate direct channel:

```text
Module.setStatus
  -> MoveFactory::scriptReport [scriptName, {moveStatus, taskId}]
  -> ipc:///tmp/python2cpp_rpc.ipc
  -> C++ RpcServer
  -> RunScript::scriptReport
```

This report does not pass through the PyIDE Broker.

## Transport and Interface Contracts

### JSON-RPC envelope

All control requests use JSON-RPC 2.0:

```json
{
  "jsonrpc": "2.0",
  "method": "tasks/path/script.py::update_cmd",
  "params": [{"args": {"operation": "load"}, "taskId": 42}],
  "id": "uuid"
}
```

A success response contains `result`; an error contains `error.code`, `error.message`, and
`error.data`. Preserve the request and response IDs when correlating logs.

### Process management

| C++ API | JSON-RPC method | Params | Result |
| --- | --- | --- | --- |
| `startScript(name,args,isConfig)` | `broker::start` | `[name,args,isConfig]` | `bool` |
| `stopScript(name)` | `broker::stop` | `[name]` | `bool` |
| `killScript(name)` | `broker::kill` | `[name]` | `bool` |
| `createParams(name)` | `broker::import` | `[name]` | status integer |

The C++ wrappers return `0` on success, `-1` for a missing script, `-2` for an RPC error, and
`-3` for a false/invalid result where applicable.

### Task lifecycle

| Wire method | Params | Script result | Purpose |
| --- | --- | --- | --- |
| `<script>::get_task` | no arguments, commonly serialized as `null` | `{scriptName,scriptStatus,taskParams,taskId}` | Query current task |
| `<script>::update_cmd` | `[taskObject]` | `null`; PyIDE start branch returns `true` | Inject or start a task |
| `suspend` | `[]` | `null` | Broadcast pause |
| `resume` | `[]` | `null` | Broadcast resume |
| `cancel` | `[]` | `null` | Broadcast cancel |
| `<script>::safe_move_check` | `[checkId]` | `null` | Trigger safe-move callback |
| `<script>::get_safe_move_check` | no arguments | `[status,checkId]` | Poll safe-move state |
| `<script>::modbus` | `[taskId]` | `null` | Trigger Modbus task callback |

The lifecycle status values are shared by MF and syspy:

```text
0 NONE, 1 RUNNING, 2 NEARTOGOAL, 3 FINISHED, 4 FAILED, 5 SUSPENDED
```

`Module.getTaskArgs()` reads only `taskObject["args"]`. Use `Module.getTaskId()` for `taskId` and
`Module.getTaskParams()` for other top-level fields. The expected shape is:

```json
{
  "args": {"businessKey": "value"},
  "config": {},
  "_script_first_run_": true,
  "taskId": 42
}
```

### Broker frames

Use frame shape to distinguish frontend, registry, and backend failures:

```text
MF REQ -> Broker frontend ROUTER:
  [client_id, empty, request_json]

Broker backend ROUTER -> script DEALER:
  [service_id, empty, client_id, empty, request_json]

Script DEALER -> Broker backend ROUTER response:
  [service_id, client_id, empty, response_json]
```

The script registers through `register_service(name, methods, scriptType)`. PyIDE resolves a
qualified method with the last `::`, replaces it with the bare method name, and forwards it to the
registered DEALER identity. Unqualified `suspend`, `resume`, and `cancel` are broadcast to every
registered service exposing that method; PyIDE aggregates their responses.

## Source and Version Discipline

Record the runtime RBK full version, syspy commit/package state, PyIDE commit, and the SDK/MoveFactory
source version before comparing contracts. Do not use a nearby SDK tree as proof of exact runtime
behavior without labeling it as a cross-version reference.

### Locate source instead of assuming a path

A developer's SDK/PyIDE checkout location differs per person, and a non-developer may have
no checkout at all. Never assume `~/workspace` or any fixed home path. Resolve it at
runtime:

1. **Runtime truth (always present, no checkout needed):** the deployed Python sources sit
   next to the running robot:

   ```bash
   # Resolve the deployed scripts root (symlink-aware)
   readlink -f /opt/.data/rbk/resources/scripts
   find "$(readlink -f /opt/.data/rbk/resources/scripts)" -maxdepth 3 \
     \( -name module.py -o -name server.py -o -name client.py \) 2>/dev/null
   ```

2. **Find a local SDK/PyIDE checkout generically** rather than assuming a directory:

   ```bash
   find "$HOME" /opt /srv /data -maxdepth 6 -type d \
     \( -name MoveFactory -o -name PyIDE \) 2>/dev/null | head
   # For C++ RPC sources:
   find "$HOME" /opt /srv /data -maxdepth 8 -name 'rpcClient.*' -o -name 'rpcServer.*' 2>/dev/null | head
   ```

3. **If the required source cannot be found, ask the user.** Request the path, the
   version, or the specific file/function, and say why it is needed. Do not guess a path,
   and do not silently substitute a different version's source. A log/trace-only answer
   is valid when it answers the question; escalate to source only when it does not.

Common source *roles* (resolve the actual path as above):

| Role | Typical relative path under a checkout |
| --- | --- |
| syspy Module/task args | `.../scripts/syspy/lib/module.py` |
| syspy Python RPC server | `.../scripts/syspy/lib/rpc/server.py` |
| SDK Python RPC client | `.../scripts/syspy/v3/lib/rpc/client.py` |
| PyIDE broker route | `PyIDE/app/api/routes/broker.py` |
| PyIDE script service route | `PyIDE/app/api/routes/rbkServce.py` |
| PyIDE IDE route | `PyIDE/app/api/routes/ide.py` |
| PyIDE task manager | `PyIDE/app/utils/taskmanager.py` |
| MF RunScript action | `MoveFactory/src/Actions/RunScript.cpp` |
| MF action factory | `MoveFactory/src/Actions/ActionFactory.cpp` |
| C++ RPC client/server | `src/robokit/utils/rpc/rpcClient.{h,cpp}`, `rpcServer.{h,cpp}` |

The deployed `syspy` sources under `/opt/.data/rbk/resources/scripts` are the strongest
available evidence because they are exactly what the robot runs. Prefer them over any
checkout; use a checkout only to read code the deployment does not ship (for example C++
plugin sources).

Search all available SDK trees for `rpcClient.cpp` if the exact version contains only the public
header. Compare headers and corroborate behavior with raw runtime messages before borrowing an
implementation from another version.

Check response-field compatibility explicitly. Some MF sources read `scriptTask` from `get_task`,
while current syspy sources return `taskParams`. Report this as a version/contract mismatch. Do not
assume it alone explains a missing `update_cmd`; trace whether execution continued after the query.

## Step-by-Step Investigation

### 1. Freeze the evidence baseline

Before restart, cancellation, or code edits, retain:

- RBK full version, model health, simulation/real-machine mode, and current errors.
- Original request body, unique task ID, timezone, and submission timestamp.
- PyIDE log covering process startup, registration, task dispatch, and terminal state.
- Active/finalized trace covering task parsing, RunScript, RPC, and report events.
- Exact syspy, PyIDE, and MoveFactory source versions used for comparison.

Use `ptcat` for the active trace and insightd `/sync` before copying durable trace evidence. Read
`references/tracing.md` for collection details.

### 2. Prove task parameters reached MF

Find the original navigation/task JSON and the converted MoveTask. Capture these exact fields:

```text
scriptName
scriptStage
scriptArgs
taskId
```

Confirm that `scriptArgs` is valid JSON and that business values are nested under its top-level
`args` object. Classify missing or malformed values here as request parsing/task construction, not
PyIDE or script loss.

Then prove `ActionFactory` scheduled `RunScript`. For the common navigation path:

- stage `0`: before the movement action;
- stage `1`: parallel with `GoPath`;
- stage `2`: after movement, the default;
- stage `3`: standalone script action.

If the trace never builds a RunScript action, stop at action planning. Do not search PyIDE for a
request MF never attempted.

### 3. Prove process startup and registration

Search PyIDE logs for, in order:

```text
broker::start
start script
program <script> is start
register_service
```

Interpretation:

- Empty args in configured-script `broker::start` are expected.
- `broker::start result=true` means the PyIDE worker thread started, not that `Popen`, import,
  `Module.init`, or registration completed.
- A missing `register_service` localizes the failure to process launch, Python import/init, or the
  script-to-Broker backend connection.
- A registration without `update_cmd`/`get_task` indicates wrong script type or incomplete Module
  initialization.

Capture the registered service name exactly. A path/name mismatch creates a valid script process
that MF cannot address.

### 4. Follow `get_task` hop by hop

Find all four checkpoints:

1. MF `callFunc` event with `<script>::get_task` and request ID.
2. PyIDE frontend `Request <=` with the same request ID.
3. PyIDE `(forwarding) Request` with the resolved service ID.
4. Script response and PyIDE response to the original MF client.

Classify the first missing checkpoint:

- No MF call: RunScript did not enter its dispatch branch.
- MF call but no PyIDE request: C++ client/`cpp2broker.ipc` transport or timeout.
- PyIDE request but no service ID: registration/name mismatch.
- Forwarded but no response: script DEALER/RPC thread or `get_task` implementation.
- Response reached MF: inspect status, task ID, script name, and task-parameter field compatibility.

`scriptStatus=0`, `taskId=0`, and empty params only prove that the persistent script currently holds
no task. They do not prove where the next task parameters were lost.

### 5. Follow task delivery

When `get_task` does not describe the same running task, expect:

```text
<script>::update_cmd
params=[{..., taskId: N}]
```

The task object may also contain `_script_first_run_=true`. Compare the full object at these points:

1. MF trace immediately before `scriptExecute(TASK, scriptName, scriptArgs)`.
2. SDK `callFunc` method and params.
3. PyIDE frontend request.
4. PyIDE internal start decision or backend forward.
5. Script RpcServer received request, or Python command line for the start branch.
6. `Module.getTaskParams()`, then `Module.getTaskArgs()`.

PyIDE's branch matters:

- Configured main task script and alive: forward `update_cmd` to the current process.
- Nonconfigured script with a different task ID, or any dead script: start/restart and pass the
  object through the command line. No second `update_cmd` is sent to the new process.

If the PyIDE frontend log contains correct params and the backend forwarding log changes them,
assign the defect to Broker routing. If the script RpcServer receives the correct object but Module
state differs, assign it to syspy dispatch/initialization. If `Module.getTaskParams()` is correct but
`getTaskArgs()` is empty, inspect the top-level `args` envelope and the business key, not ZMQ.

If the chain stops immediately after a successful `get_task`, inspect MF between `isSameScript()`
and `scriptExecute()`: response-field exceptions, runtime/source mismatch, script-path checks, and
the ignored `scriptExecute()` return are higher-value leads than script business logic.

### 6. Follow status reporting independently

For a persistent process receiving `update_cmd`, syspy stores the new args and calls
`setStatus(RUNNING)`, which immediately sends `scriptReport`. For command-line startup,
`__initTaskArgs()` sets internal `RUNNING` but does not automatically report it; the script must later
call `Module.setStatus()`.

For every expected state change, capture:

1. Script call to `Module.setStatus(status)` and current `taskId`.
2. Python JSON-RPC request `MoveFactory::scriptReport`.
3. C++ RpcServer receipt/result.
4. `RunScript::scriptReport` task-ID comparison and resulting `m_move_status_rpc`.
5. MF action/task status transition.

If no report exists and `taskId` is `0` or `None`, syspy intentionally suppresses the report. If the
report reaches MF with a different task ID, MF rejects it by setting the RPC status to `NONE`. If MF
accepts `FINISHED/FAILED` but the navigation task remains active, continue in ActionExecutor/task
aggregation rather than the Python script.

### 7. Check pause, resume, and cancel separately

MF currently sends unqualified `suspend`, `resume`, and `cancel`, so PyIDE broadcasts them. Verify:

- Which registered services expose the method.
- Which script identities receive it.
- Whether PyIDE is waiting for multiple aggregated responses.
- Whether the target Module state permits the operation.
- Whether the script callback calls `Module.setStatus()` and preserves the same task ID.

Do not kill a persistent process to test cancellation. Use `/cancelNavigate` and retain lifecycle
evidence.

## Ownership Rules

Assign ownership only at the first proven broken boundary:

| Evidence | Primary area to investigate |
| --- | --- |
| Original task lacks script args | Request producer/task construction |
| Original task has args, converted MoveTask does not | MF task parsing/conversion |
| MoveTask is correct, RunScript action is absent | MF ActionFactory/action planning |
| RunScript enters, no MF `get_task` | MF RunScript control flow |
| MF request exists, PyIDE never receives it | SDK RpcClient/ZMQ frontend transport |
| PyIDE receives qualified method, registry lookup fails | PyIDE registry or script service name |
| PyIDE forwards, script never responds | Broker backend, script DEALER, or RpcServer thread |
| `get_task` completes, MF never attempts required `update_cmd` | MF post-query control flow/version contract |
| PyIDE receives `update_cmd` with correct args but forwards/starts with different args | PyIDE internal routing/start logic |
| Script RpcServer receives correct object, Module state is wrong | syspy RPC dispatch/Module initialization |
| `getTaskParams()` is correct, `getTaskArgs()` is empty | Missing/wrong top-level `args` envelope |
| Module state is correct, business behavior is wrong | Script business logic |
| Script reports terminal status, MF rejects it | task-ID/status correlation in MF |
| MF accepts terminal status, outer task stays active | MF ActionExecutor/task aggregation |

Use “not observed” rather than “not sent” when the available log does not instrument the sender.
Absence in PyIDE proves only that PyIDE did not log receipt; pair it with the MF `callFunc` trace before
assigning the previous hop.

## High-Risk Implementation Details

- C++ `callFunc()` defaults to 100 ms. syspy `update_cmd()` may wait up to 1 second for the previous
  task to become `NONE`, `FINISHED`, or `FAILED`. A valid call can therefore outlive the MF client.
- Some RunScript sources ignore the integer return from `scriptExecute(update_cmd)`. MF may set its
  local RPC state to `RUNNING` before a failed/timed-out dispatch and then appear stuck indefinitely.
- PyIDE signals its subprocess `started_event` before `Popen()` and script registration. A successful
  start response is not readiness evidence.
- `Module.__getArgs()` silently falls back to `{}` when command-line JSON parsing fails.
- Terminal `Module.setStatus(FINISHED/FAILED)` reports first, then clears task params and task ID. A
  later query can legitimately show empty params.
- MF correlates reports by task ID. In examined sources, `scriptName` is accepted but not used for
  report validation.
- Lifecycle control methods are broadcast, not qualified to the current RunScript script name.
- A `scriptTask` versus `taskParams` response-field mismatch is a concrete compatibility defect, but
  trace the subsequent branch before claiming it blocked dispatch.

## Evidence Checklist

For an MF/PyIDE/script RPC defect, retain this minimal chain:

- Runtime and source versions for RBK, MoveFactory/SDK, PyIDE, and syspy.
- Original task JSON and converted `scriptName`, `scriptStage`, `scriptArgs`, and task ID.
- ActionFactory/ActionExecutor proof that RunScript was scheduled and entered.
- `broker::start` and `register_service` messages when process lifecycle is relevant.
- `get_task` request ID, service ID, forwarding event, and raw response.
- `update_cmd` method, full params, PyIDE branch decision, and response/error.
- Script `Module.getTaskParams()`, `getTaskArgs()`, status, and task ID at receipt.
- Each `scriptReport` payload and MF task-ID comparison.
- Suspend/resume/cancel recipients and aggregated response when control flow is involved.
- Exact timeout/error codes and the first missing hop.

Useful search anchors:

```bash
rg -n 'broker::start|register_service|::get_task|::update_cmd|scriptReport|scriptExecute|callFunc' ide*.log
ptcat <active-or-finalized-trace> | rg 'RunScript|scriptArgs|get_task|update_cmd|scriptReport|RcError'
```

For compressed traces without an available query tool, `zstdcat trace.pft.zst | strings` can provide
supporting text, but do not treat string order as a substitute for timestamped Perfetto events.
