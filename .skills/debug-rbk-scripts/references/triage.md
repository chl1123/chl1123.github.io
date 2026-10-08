# RBK Fault Triage: Time Window First, Then Channel

Read this file first for any new RBK problem. It routes a symptom to the narrowest
log, trace channel, and source file before you read any other reference.

## Step 0: Get the time window before touching anything

Almost every RBK problem is unresolvable without a wall-clock window. Do not start by
reading logs, grepping source, or editing scripts. Ask for these first:

| Required input | Why it is needed | Acceptable precision |
| --- | --- | --- |
| Fault time (wall clock, with timezone) | Selects one `rbk+common_*.pft.zst` segment and the matching log files | ±1 minute is ideal; ±10 minutes still works |
| `taskId` (if a task was involved) | Filters trace, `ide` log, and `rbk+report.jsonl` to one task | exact string |
| Symptom class | Chooses the channel group below | one line |
| RBK full version | Channels/sources differ per version | a version string such as `3.5.4.x` |
| Repro or one-shot | Decides whether to keep tracing live or finalize a segment | one line |

If the reporter cannot give a time, ask them to reproduce once while watching the clock,
or to export the log bundle. Do not guess a window from "recently": the trace rolls
about every 15 minutes and the `ide` log rolls near 20 MB, so a wrong window silently
returns nothing.

Record the window, then continue. Example: `2026-09-29 13:47:00 ~ 13:57:00 CST`.

### Map wall clock to artifacts

```bash
TRACE_DIR=/opt/.data/diagnosis/rbk/trace/event
LOG_DIR=/opt/.data/diagnosis/rbk/logs

# Trace segments overlapping the window (name carries the segment start time)
ls -1 "$TRACE_DIR"/rbk+common_*.pft.zst | tail -40

# ide log files overlapping the window (name carries the file start time)
ls -1 "$LOG_DIR"/ide/*.log | tail -20

# Script-side logs overlapping the window (per-script process)
ls -1t "$LOG_DIR"/scripts/*.log | head -20
```

Convert the fault time to the trace spelling used by `ptcat` before querying:

```bash
DATE='2026-09-29'; T0='13:47:00'; T1='13:57:00'
B=$(echo "$DATE $T0" | sed 's/[-:]//g; s/ /./')   # 20260929.13:47:00
E=$(echo "$DATE $T1" | sed 's/[-:]//g; s/ /./')   # 20260929.13:57:00
```

Prefer `ptcat` against the active/`.__temp__.` file for live work. Call insightd `/sync`
only when a durable finalized segment is needed. See [tracing.md](tracing.md).

`ptcat` may not be on `PATH`. Resolve it with `command -v ptcat`, else
`/opt/data/rbk/tools/ptcat`; if neither exists, ask the user — on the Feishu/Lark online
AI environment the tool is obtained from
`https://seer-group.feishu.cn/docx/RIDEdz8pCogIHgxdFzdcTTEtnTf`. Details in
[tracing.md](tracing.md).

## Step 1: Pick the channel group from the symptom

All addressable groups and channels observed on RBK 3.5. The authoritative local
catalog is the `trace.cfg` shipped with the SDK. Its location differs per machine, so
resolve it rather than assuming a path:

```bash
# Find trace.cfg anywhere a checkout or release bundle may live
find "$HOME" /opt /srv /data -maxdepth 8 -name trace.cfg 2>/dev/null | head
```

Fallback when no `trace.cfg` is available: the deployed `syspy` sources under
`/opt/.data/rbk/resources/scripts` and the live trace (`ptcat -c stat`) still reveal
channel names. If neither yields the channel, ask the user for their SDK path or
version. Prefer the resolved `trace.cfg` over this table when a version may have moved a
channel.

### Script logic, script RPC, and script dispatch

Category: `rbk.script.utils_rpc`.

| Channel name | Meaning | Use it to answer |
| --- | --- | --- |
| `Rc` | RPC **client** side (`rbk::utils::RpcClient`, used by MoveFactory/SDK to call into PyIDE/scripts). Emitted from `rpcClient.cpp`; `scriptExecute`, `startScript`, `stopScript`, `scriptExists` events | Did MF/SDK actually send the request, with which `scriptName`/`args`/`executeType`? |
| `RcError` | Client-side failures: `connect`, `sendMessage`, `response.parse_error`, and `callFunc` returning a JSON-RPC `error` | Did the send fail, or did the peer return a JSON-RPC `error`? |
| `Rs` | RPC **server** side (`rbk::utils::RpcServer`, bound by RBK plugins, e.g. MoveFactory `scriptReport`/motor calls). `req` holds the raw request body; `io,stat` reports `recv/sent/inflight/overloadDrop` | Did the receiving plugin get the request unchanged, before its handler ran? |
| `RsError` | Server-side failures: `receiveError`, `sendResponse`, `pollError`, dispatch exceptions | Did the receiver fail to receive, parse, or reply? `overloadDrop` shows overload drops. |
| `BinMsgChannel` | Binary message channel exceptions | Did the raw-message channel throw? |
| `RpcServer` | `bindLog`/`putValue`/`getValue` wrapper messages | Did value registration or binding fail? |

`Rc` and `Rs` are the two ends of a C++ RPC call. They are emitted by the RBK C++
side, **not** by the Python script process: syspy's Python `RpcServer`
(`syspy/lib/rpc/server.py`) logs through the normal `rbk.script` logger instead, so a
Python-side request appears in `logs/scripts/<name>_*.log`, while the C++ peer appears in
the trace as `Rc`/`Rs`. Locate which side is missing before reading Python: a request in
`Rc` but absent in `Rs` never reached the receiving plugin; present in both with
different bodies means a routing or parse loss.

```bash
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n 'Rc'      trace.pft.zst
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n 'RcError' trace.pft.zst
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n 'Rs'      trace.pft.zst
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n 'RsError' trace.pft.zst
```

For a script-defined channel such as `fork`, `actions`, `elevator`, or `loc_angle`,
filter by that channel name inside the same category instead of by `Rc`/`Rs`:

```bash
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n 'fork\.task'  trace.pft.zst
ptcat -b "$B" -e "$E" -g 'rbk\.script\.utils_rpc' -n 'fork\.motor' trace.pft.zst
```

The channel name is whatever the script passed to `Trace.log(..., name=...)`; discover it
first with `ptcat -c stat` over a narrow window, then query the exact name. Known channels
shipped in `trace.cfg`: `fork.rec`, `fork.script`, `fork.task`, `fork.motor`.

### Navigation and movement

Category: `rbk.nav.MoveFactory` (runtime group; not always present in `trace.cfg`).

Use it to answer which action was scheduled, whether `RunScript` entered, whether
`GoPath`/movement advanced, and where a task stopped. This is the first place to look
when a `/navigate` task is stuck, a stage never runs, or action planning stops early.

```bash
ptcat -b "$B" -e "$E" -g 'rbk\.nav\.MoveFactory' trace.pft.zst
```

Related navigation channels: `rbk.nav.DSPChassis` (`publishNavspeed`, `MotorCmd`,
`Controller`, `IMU`), `rbk.nav.SensorFuser`, `rbk.nav.RBKSim`.

For the MF-to-script call chain itself, follow `Rc`/`Rs` afterwards and read
[mf-script-rpc.md](mf-script-rpc.md) to assign ownership at the first broken hop.

### Localization and positioning

Category: `rbk.loc.MCLoc`.

| Channel name | Meaning |
| --- | --- |
| `locationEachFrame` | Per-frame pose, `locState`, `locMethod`, `yawBias`, velocity |
| `locByNDT` | 3D NDT localization, with `confidence` |
| `eKFLocalizationFusion` | EKF fusion pose, with `dataTime`/`pubTime` |
| `locationbySLAM` | SLAM pose, with laser/odom data times and confidence |
| `locationbyRef` | Reflector-based pose, with confidence |
| `liveReflectorPosition` | Live reflector positions |
| `laserWithUndistort` | Motion-undistorted laser message |
| `switchMap` | Map switch status |
| `simLocation` | Simulator pose |

Use for jumps, drift, low confidence, wrong `locMethod`, or pose that disagrees with
odometry. Correlate the same timestamp across `locationEachFrame` and the source-method
channel to see which estimator produced the accepted pose.

```bash
ptcat -b "$B" -e "$E" -g 'rbk\.loc\.MCLoc' -n 'locationEachFrame' trace.pft.zst
ptcat -b "$B" -e "$E" -g 'rbk\.loc\.MCLoc' -n 'locByNDT'          trace.pft.zst
```

### Map loading and switching

Category: `rbk.loc.BlockMapLoader`.

| Channel name | Keys | Meaning |
| --- | --- | --- |
| `changeMap` | `name` (map name), `msg` (info) | Map load/switch request and result |

Use for "wrong map", "map fails to load", "robot positioned in the previous map", or
localization failure that begins right after a map switch. Pair with
`rbk.loc.MCLoc/switchMap` to see the localization side of the same switch.

```bash
ptcat -b "$B" -e "$E" -g 'rbk\.loc\.BlockMapLoader' -n 'changeMap' trace.pft.zst
```

### Devices, motors, and DI/DO

Category: `rbk.device.DSPChassis`.

| Channel name | Meaning |
| --- | --- |
| `motorInfo` | Motor messages: the fastest way to confirm motor presence, config, and feedback |
| `codeSysPubMessageMotorCmd` | Codesys motor command (`messageMotorCmd`) |
| `messageDI` / `messageDO` | DI / DO state. Rising edge appears as `if_di_same:false`, `status:true` |
| `distanceInfo` | Distance sensors |
| `handleBatteryInfo`, `fill99batteryInfo` | Battery |
| `handleSafeModule` | Safety module |
| `ERadioMsg`, `EStadioBindStatus` | Radio / DTU |
| `msgDeviceStatusFromDSP`, `msgDeviceStatusFromRBK`, `EDeviceStatus` | Device status snapshots |
| `pubStdPlcToSrc`, `pubFastPlcToSrc` | PLC to SRC std/fast messages |

Use `motorInfo` directly for "motor not moving", "wrong motor config", "kinematics
wrong". A missing or empty `motorInfo` is an incomplete model startup, not a script bug:
see [script-debugging.md](script-debugging.md).

```bash
ptcat -b "$B" -e "$E" -g 'rbk\.device\.DSPChassis' -n 'motorInfo' trace.pft.zst
ptcat -b "$B" -e "$E" -g 'rbk\.device\.DSPChassis' -n 'messageDI' trace.pft.zst
```

### Full local channel catalog

`trace.cfg` (resolved as above) is the authoritative channel/key
catalog for the installed version. Its top-level groups are `rbk.nav.DSPChassis`,
`rbk.device.DSPChassis`, `rbk.loc.MCLoc`, `rbk.loc.BlockMapLoader`,
`rbk.script.utils_rpc`, and `protos`. Each group lists channels, keys, and zh/en
descriptions. Diff this file when a channel seems missing, and treat runtime-only groups
such as `rbk.nav.MoveFactory` as present even when absent from the file.

```bash
CFG=$(find "$HOME" /opt /srv /data -maxdepth 8 -name trace.cfg 2>/dev/null | head -1)
python3 - "$CFG" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for g, chans in d.items():
    if g == 'protos':
        continue
    print('==', g)
    for name, info in chans.items():
        keys = ','.join((info.get('keys') or {}))
        print(f'   {name}: {info.get("zh","")} | {keys}')
PY
```

## Step 2: Route by symptom class

Pick the row, then follow the linked path. Do this before reading source.

| Symptom | First artifact | Reference |
| --- | --- | --- |
| Whole RBK crashes / restarts / OOM-killed | `syslog` | This file, "Crash triage" |
| Script process crashed (`pyCrashed`) | PyIDE `ide` log, then `scripts/<name>_*.log` | "Crash triage" |
| Task sent but script did not run | `Rc`/`Rs`, then `ide` log | [mf-script-rpc.md](mf-script-rpc.md) |
| Task params empty in script | `Rc` (sent) vs `Rs` (received) vs `Module.getTaskArgs()` | [mf-script-rpc.md](mf-script-rpc.md) |
| Action stuck `RUNNING` | `rbk.nav.MoveFactory`, then `Rc`/`Rs` | [mf-script-rpc.md](mf-script-rpc.md) |
| `/navigate` stuck or wrong path | `rbk.nav.MoveFactory`, `rbk.nav.DSPChassis` | [tracing.md](tracing.md) |
| Robot pose wrong / jumps / low confidence | `rbk.loc.MCLoc` | [tracing.md](tracing.md) |
| Wrong map / map switch fails | `rbk.loc.BlockMapLoader` | [tracing.md](tracing.md) |
| Motor not moving / wrong config | `rbk.device.DSPChassis/motorInfo` | [script-debugging.md](script-debugging.md) |
| Sensor / DI / DO wrong | `rbk.device.DSPChassis/messageDI`, `distanceInfo` | [message-latency.md](message-latency.md) |
| Message/DI latency | publisher edge vs reader return | [message-latency.md](message-latency.md) |
| Sensor/model config wrong | `resources` bundle | This file, "Resource bundle" |
| HTTP endpoint / request shape | OpenAPI MCP | [http-api.md](http-api.md) |

## Crash triage

### Whole-RBK crash

Check `syslog` first. It holds kernel OOM kills, segfaults, service restarts, and driver
faults that never appear in RBK logs. A missing trace segment plus a service restart in
`syslog` usually means the crash predates any RBK-side logging.

```bash
# Window around the fault
sudo journalctl -S '2026-09-29 13:45:00' -U '2026-09-29 14:00:00' --no-pager
# Or grep the flat file when journald is not the source
sudo awk '/^Sep 29 13:4[5-9]|^Sep 29 13:5[0-9]/' /var/log/syslog |
  rg -i 'rbk|segfault|oom|killed|core'
```

Also check `/opt/.data/diagnosis/rbk/coredump` and the last lines of the newest
`logs/ide/*.log` before the gap.

### Script process crash

For a Python script that died, the PyIDE `ide` log is the primary source: it records
`broker::start`, `program ... is start`, `register_service`, unregister, nonzero exit,
and traceback plumbing. The per-script log under `logs/scripts/` holds the script's own
stdout/stderr and JSON-RPC traffic.

```bash
IDE=/opt/.data/diagnosis/rbk/logs/ide/ide_2026-09-29_14-07-46.log
rg -n 'broker::start|register_service|unregister_service|Traceback|Error|exit' "$IDE"
ls -1t /opt/.data/diagnosis/rbk/logs/scripts/ | head
```

A `pyCrashed` robot state is sticky; read the safety rules in [SKILL.md](../SKILL.md) and
[script-debugging.md](script-debugging.md) before mutating the script.

## Correlating a task with `taskId`

`taskId` is the join key across artifacts. The PyIDE `ide` log carries it inside forwarded
JSON-RPC bodies (`get_task`, `update_cmd`, `scriptReport`), and the script-side log
carries it in each JSON-RPC line. Use it to prove what the script sent and received
before blaming SDK capability.

```bash
TASK=42
IDE=/opt/.data/diagnosis/rbk/logs/ide/ide_2026-09-29_14-07-46.log
SCRIPT=/opt/.data/diagnosis/rbk/logs/scripts/ContainerRobot_2026-09-29_13-47-14.log

rg -n "taskId[\"']?\s*[:=]\s*$TASK|::get_task|::update_cmd|scriptReport" "$IDE" | head -50
rg -n "$TASK|MoveFactory::scriptReport|update_cmd" "$SCRIPT" | head -50
```

Rules that keep this honest:

- `Rc` proves the RBK C++ client sent a request; `Rs` proves the receiving plugin
  received it. A Python-side send/receive is proven from `logs/scripts/<name>_*.log`
  instead. Confirm the relevant pair before saying a value was "lost".
- Confirm the script's outbound report through the trace (`Rc`/`Rs`/`scriptReport` event)
  and the script log before attributing a missing status to the SDK. If the script sent it
  correctly, the defect is downstream.
- When a script and SDK capability are both suspect, hold one variable fixed (same script,
  or same SDK) and state exactly which combination each run proves. See
  [message-latency.md](message-latency.md) for the control-variable matrix.

## Resource bundle

The robot's actual runtime inputs live under `/opt/.data/rbk/resources`. An exported log
bundle contains a `resources` directory with the same layout, so you can inspect exactly
what the robot was running rather than the repo HEAD.

| Path | Contains | Use it to check |
| --- | --- | --- |
| `resources/scripts/` | The scripts actually deployed and running | Whether the failing script matches your branch |
| `resources/scripts/params/` | Per-script task config/params JSON | Whether task params/defaults were the expected ones |
| `resources/maps/` | Deployed maps and `workspace*.json` | Whether the loaded map matches the expected one |
| `resources/devices/robot.model` | The device/model file | Whether a sensor, motor, or kinematics entry is configured correctly |
| `resources/tasks/` | Task definitions | Whether the dispatched task definition is the expected one |
| `resources/apps/` | App bindings and `script/task.json` symlink | Whether the active task config symlink points at the right file |

`robot.model` is the fastest way to confirm a sensor or motor is configured as intended:
open the model file and check the relevant device block instead of inferring from behavior.

```bash
ls -la /opt/.data/rbk/resources
sed -n '1,80p' /opt/.data/rbk/resources/devices/robot.model
readlink -f /opt/.data/rbk/resources/apps/script/task.json
```

When comparing against a bundled export, diff the bundle's `resources` against the live
tree before trusting either.

## Stop condition

Do not move to source reading or script edits until you have:

1. A wall-clock window with timezone.
2. The exact trace segment and log files covering it.
3. The channel group and channel name for the symptom.
4. For task problems, the `taskId` and the first missing hop (`Rc` vs `Rs` vs MF).

Only then open [tracing.md](tracing.md), [mf-script-rpc.md](mf-script-rpc.md),
[script-debugging.md](script-debugging.md), [message-latency.md](message-latency.md), or
[http-api.md](http-api.md) for the deep procedure.
