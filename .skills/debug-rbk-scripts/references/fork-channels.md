# Fork Script Trace Channels: Locate a Problem by Channel

Fork (`tasks/*/standard/fork.py` + `fork_utils.py`) writes to a fixed set of named
channels under `rbk.script.utils_rpc`. This reference maps symptom → channel → query,
so you can reach the decisive line without reading the script first.

For the general trace mechanics (`ptcat`, time windows, `/sync`) read
[tracing.md](tracing.md). For intake and non-fork routing read [triage.md](triage.md).

## Why channel-based lookup works here

Fork is a **high-frequency** script: `period_run()` ticks every ~0.1 s and a single
load/unload task emits thousands of records. Grepping the raw trace by text is
ineffective. Because every record carries a stable channel name, and because structured
events carry a common context (`taskId` / `operation` / `phase` / `actionId` /
`actionType`), you can jump straight to the layer you care about.

```bash
# One task, one channel, one window. This is the primary move.
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n '^fork\.policy$' trace.pft.zst

# Which fork channels exist at all in this window (discover before querying)
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n '^fork' trace.pft.zst \
  | sed 's/.*\]: //' | jq -r '.event // "(numeric snapshot)"' | sort | uniq -c | sort -rn
```

`ptcat -n` is an unanchored regex **substring** match: `-n 'fork'` also pulls in
`fork.task`, `fork.motor`, and any unrelated channel containing "fork". Anchor with
`^fork\.nav$` when you want exactly one channel.

## Channel map

| Channel | Type | Answers | Changes when |
| --- | --- | --- | --- |
| `fork` | event | Script lifecycle and task-level decisions: did the script start, receive args, validate, fail, cancel | Once per lifecycle transition |
| `fork.task` | numeric snapshot | Task-level state: `scriptStatus`, `actionStatus`, `actionIndex`, `actionCount`, `forkAutoFlag`, current action | On state change + 5 s heartbeat |
| `fork.taskActions` | event protocol | Action queue: `taskBuild`, `taskExtend`, `actionStateChanged`, `taskFinished`, `taskFailed` | On queue/action transition |
| `fork.motor` | event + numeric | Motor commands and fork mechanism: commanded / reached / failed / stopped, fork height, direction, speed, mileage | On change + 5 s heartbeat |
| `fork.nav` | event | Navigation: path commanded/planned, target resolved, final phase entered, collision devices, waypoints | Per navigation action |
| `fork.policy` | event | **Policy dispatch**: which obstacle-stop keys were changed, `before`/`after`, `changedKeys`, `resetPath` | Only when a policy value actually changes |
| `fork.rec` | event | Recognition: region set, progress, hole normalization, target computed, accepted/rejected | Per recognition attempt |
| `fork.cfg` | event | Config load and device model: `configLoaded`, `moduleInstallResolved`, `moduleMotorBuilt`, tip-laser config, deduct areas | Once per config load |
| `fork.err` | event | Errors: `errorCode` + `reason`. Timeouts, DI triggers, parse failures, invalid params | On error only |

`fork.task` and `fork.motor` are **numeric snapshots**: they have no `event` field and
are deduplicated by value (only written on change, plus a heartbeat). A long stretch
with no records while the fork is idle is **normal**, not a logging failure.

## Symptom → channel routing

| Symptom | First channel | Then |
| --- | --- | --- |
| Task never started / wrong args | `fork` (`scriptArgsReceived`, `scriptArgsValidated`, `scriptArgsNormalized`) | `fork.cfg` for config, [mf-script-rpc.md](mf-script-rpc.md) for the RPC hop |
| Script failed / cancelled | `fork` (`scriptFailed`, `scriptCancelled`) | `fork.err` for `errorCode` |
| Script hangs, no progress | `fork.task` (last `actionIndex`/`actionStatus`) | `fork.taskActions`, then `rbk.nav.MoveFactory` |
| Fork not moving / wrong height | `fork.motor` (`motorCommanded` → `motorReached`/`motorFailed`) | `rbk.device.DSPChassis/motorInfo` |
| Fork stopped early / unexpectedly | `fork.motor` `stopReason` (`stopDi` / `timeout` / `noMove` / `alreadyInPlace`) | `fork.err` |
| Unexpected obstruction / blocked | `fork.policy` (what was just pushed) | `rbk.nav.MoveFactory` for the block event |
| Robot drives wrong way or stops mid-path | `fork.nav` | `rbk.nav.MoveFactory`, `rbk.nav.DSPChassis` |
| Recognition wrong / no result | `fork.rec` | `fork.err`, `rbk.loc.MCLoc` for pose |
| Load/unload state mismatch | `fork.task` + `Container.hasGoods()` | See "Cargo state" below |
| Robot behaved oddly but no error | `fork.cfg` (device model) | `fork` lifecycle, then platform health |

## The load-bearing correlation fields

Every structured fork event carries these, injected automatically. Use them to join
across channels instead of correlating by timestamp.

| Field | Meaning |
| --- | --- |
| `taskId` | Task id (`RunScript-xxxx`). The primary join key. |
| `operation` | `load` / `unload` / other |
| `phase` | Fork's segmented-path phase: `direct_path`, `align_path`, `reach`, `final_path` |
| `actionId` | Action instance id, e.g. `GoPathWithContactDi-3767b80e` |
| `actionType` | Action class name |

`actionId` is what lets you follow **one** action across `fork.nav` (it was commanded),
`fork.policy` (it changed the stop distance), and `fork.motor` (its motor moved). This is
the highest-value join in a fork investigation.

```bash
# Follow one action id across every fork channel
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n '^fork' trace.pft.zst \
  | rg 'GoPathWithContactDi-3767b80e'
```

`phase` is empty for events with no action context (script lifecycle, config load,
parameter validation). That is expected — do not read it as a defect.

## Worked example: obstruction / blocked before reaching target

The signal is a platform block event in `rbk.nav.MoveFactory`. To explain it from the
script side, ask "what did the script just push?", then read `fork.policy`:

```
[13:51:15] fork.policy  policyApplied
  {"actionId":"GoPathWithContactDi-3767b80e","operation":"load","phase":"direct_path"}
```

Read only the three fields that matter first — `changedKeys`, `before`, `after`:

```bash
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n '^fork\.policy$' trace.pft.zst \
  | sed 's/.*\]: //' | jq -c '{t:.trigger,k:.changedKeys,b:.before,a:.after}'
```

A drop such as `obsStopUnload.obsStopDist: 1 → 0.1` explains a stop that the platform
trace alone cannot: the robot stopped because the script deliberately narrowed the stop
distance, not because the environment suddenly changed. Before the policy channel
existed, this was only inferable from a free-text `fork.task` line.

## Cargo state: `Navigation.hasGoods()` vs `Container.hasGoods()`

A recurring fork failure mode. **They are not equivalent and must both be captured.**

```bash
# Both states, plus the bound container list
"$RT" -c "
from syspy import Container, Navigation
print('Navigation.hasGoods:', Navigation.hasGoods())
print('Container.hasGoods(0):', Container.hasGoods('0'))
print('containers:', Container.getContainers())
"
```

`Navigation.hasGoods()=True` with `Container.hasGoods()=False` and `containers=[]` is a
**contradictory/residual** state seen in simulation after an aborted task. It makes
subsequent `load` cases fail almost immediately (~0.2 s) with `hasGoods True->True`,
because the script-side precondition rejects them. Before blaming a code change for such
a failure, reproduce it on the unmodified revision — the signature is identical.

Use `Container` as the logical load/unload lifecycle state. Do not treat a `load` case
failing in <0.5 s as a logic regression without first checking both flags.

## Reading `stopReason` on `fork.motor`

`motorReached` / `motorFailed` / `motorStopped` carry a fixed `stopReason` enum. It
distinguishes "worked as designed" from "gave up":

| `stopReason` | Meaning | Healthy? |
| --- | --- | --- |
| `positionReached` | Reached the target position | yes |
| `alreadyInPlace` | Already within tolerance; no move issued | yes |
| `stopDi` | Stopped on a stop-DI edge (contact) | yes, for contact flows |
| `targetIsMidHeight` | Target is between layers | check the task args |
| `noMove` | Commanded but never moved | **investigate** |
| `timeout` | `ForkMoveTimeout` exceeded | **investigate** |
| `cancelled` | Task/suspend cancelled the move | context |

```bash
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n '^fork\.motor$' trace.pft.zst \
  | sed 's/.*\]: //' | jq -c 'select(.event) | {e:.event,a:.actionId,m:.motor,s:.stopReason,d:.delta}'
```

## Pitfalls that waste time

- **Empty `phase` is normal** for lifecycle/config/parameter events. It is not a bug.
- **`fork.task` / `fork.motor` going quiet is normal.** They are change-triggered with a
  5 s heartbeat; an idle robot legitimately emits few records.
- **`_droppedFields` is not "data was cut".** It counts only non-serializable values.
  A `None` field is preserved as JSON `null`. If you need to know whether a value was
  genuinely absent versus dropped, `null` vs a missing key is the distinction.
- **`trace.cfg` only declares channels the SDK scanner found.** A channel can be live in
  the trace yet absent from `trace.cfg` (fork channels written via `emit_event` wrappers
  have no literal `Trace.log` call site for the scanner to key on). A missing channel in
  `trace.cfg` does **not** mean it is not being written — confirm from the trace.
- **Stale channels persist in `trace.cfg`.** Its generator merges into the existing file
  and never deletes, so a channel removed from source can linger for many builds.
- **The production path is `tasks/standard/`**, created at package time from `tasks/v3/`
  with the `v3` level stripped. The real machine imports `standard.fork`. Fixing only
  `tasks/v3/` changes nothing on the robot until it is packaged or mirrored.

## Stop condition

Report the conclusion plus the decisive quoted line from the routed channel. If the
channel is empty where it should not be, say which channel and which expected event is
missing — that is itself the finding, and it separates "script never got there" from
"script got there and misbehaved".
