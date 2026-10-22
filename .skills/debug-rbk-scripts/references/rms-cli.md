# rms-cli (Robot Management Service CLI)

`rms-cli` is the RMS node-management CLI. It is the **node-level** counterpart to the
RBK HTTP API: it talks to `rms-service` (`rms.normal`, health, backup, OTA, service
control) and can also fetch the whole aggregated robot status in one call.

## Where It Lives

```
/opt/data/rms/bin/rms-cli          # same node as RBK (robot: /opt/data, sim container too)
```

Relative to the RBK install it is `../rms/bin/rms-cli` (`/opt/data/rbk` →
`/opt/data/rms`). It runs **inside the robot / container filesystem**, not from your
laptop. Target an RBK on another host with `docker exec` (sim) or SSH (robot).

Default config: `/opt/data/rms/config.yaml` (override with `-c/--config`).
The web UI is `http://<robot>:8080`, its CLI reference is `http://<robot>:8080/docs/cli`.

## rms-cli vs the RBK HTTP API (8081)

| Need | Use | Why |
| --- | --- | --- |
| Navigate, cancel, task status, container/goods, settings | **HTTP 8081** (`/navigate`, `/multiPathNavigate`, `/cancelNavigate`, `/getSpecifiedFieldsAIO`) | That is the RBK/SPG control surface; `rms-cli` has no navigation commands |
| Full status snapshot incl. `navigation` + `taskStatusPackage` + `containers` + `stats` | either; `rms-cli robot status` is one call and self-describing | useful as a *witness* snapshot next to a temporary HTTP probe |
| Service lifecycle (start/stop/restart/status of `insightd`, `pyide`, …) | **rms-cli `cmd service`** | HTTP 8081 has no service control |
| Log bundle preparation/download | **rms-cli `logs`** | no HTTP equivalent |
| Robot identity, simulation flag, OTA, network config | **rms-cli `robot` / `network` / `ota`** | RMS-owned state |
| Perfetto perf capture | **rms-cli `insight perf`** | wraps the perf runner, returns the file path |

Rule of thumb: **behaviour** from HTTP, **environment/plumbing** from `rms-cli`.
When a test needs to prove that a misbehaving state is not your probe's fault, take an
`rms-cli robot status` snapshot at the same moment and quote it.

## Verified Commands

All of the following were executed against a 3.5.4.0226 simulation container.

```bash
RMS=/opt/data/rms/bin/rms-cli

$RMS --help              # groups: system logs network time ota cmd files activity
                         #         robot configuration spg insight mqtt health provision
$RMS cmd --help          # reboot shutdown service uptime disk memory processes network
                         # system-info cpu-info disk-space temperature system-stats
                         # services ping
$RMS robot --help        # info run-info status clear-dataset simulation audio backup
                         # network-config version-switch info-update modbus-config
$RMS logs --help         # prepare download events
$RMS insight --help      # perf debug
$RMS spg --help          # config-get config-set state
```

### Status snapshot (most useful for script debugging)

```bash
$RMS robot status
```

Prints the full `RobotStatusResponse` **and** then the same JSON again on stdout.
Read the second block (the pretty JSON). It contains, per node:

- `rms` / `spg` / `rbk` health + versions (`rbk.version`, `pyideVersion`,
  `taskRunnerVersion`, plugin `versionList`);
- `rbk.run_info.currentMap` and `currentMapEntries` (md5 per map file);
- `location` (`currentStation`, `x`, `y`, `confidence`, `locStatus`);
- `navigation`: `taskId`, `taskStatus`, `runningStatus`, `targetName`,
  `taskStatusPackage.taskStatusList` (per-segment status, the same numbers you would
  poll from HTTP), and `moveStatusInfo` (JSON **string** with `containers`,
  `forkHeight`, `moduleMotor`, per-action `action.N.<Type>.action_status`);
- `stats` (fork mileage/count), `battery`, `controller`, `chassis` (`isStop`, speeds).

It is noisy on stderr (INFO logs). To keep only the payload:

```bash
$RMS robot status 2>/dev/null | jq -s '.[-1]'
```

### Service control

```bash
$RMS cmd services                                   # list managed services
$RMS cmd service insightd --action status --node master
$RMS cmd service insightd --action restart
```

`cmd services` on a 3.5.4 container reported:
`startup_rbk3_5 spg pyide seer.taskmanagerd seer-system-ready traced insightd rms-service`.

This is the **correct** way to (re)start `insightd` on a robot where
`systemctl` is not available to you, and it is also how to restart `pyide` without
rebooting RBK.

### Logs

```bash
$RMS logs events --limit 50
$RMS logs prepare --since 2026-10-22T10:30:00 --until 2026-10-22T11:30:00
$RMS logs download
```

`logs prepare --since/--until` compares against **file mtime** (and the timestamp in
the filename), in node local time. Use it before `download` so the bundle is small.

### Insightd / perf

```bash
$RMS insight debug --enable      # push headroom for insightd-followed services
$RMS insight debug --disable
$RMS insight perf --duration 5   # -> "file": ".../rbk+perf_<ts>.perfetto_perf.pft"
```

`insight perf` is the quickest way to get a one-off CPU trace without touching
`insightd`. The `common` trace that carries `rbk.nav.MoveFactory` events still comes
from `insightd` itself — see [tracing.md](tracing.md).

### Robot identity / simulation flag

```bash
$RMS robot info                  # node, robotName, robokitVersion, simulation flag
$RMS robot run-info              # current run info (map, task, ...)
$RMS robot simulation get        # {"simulation": true, ...} per node
```

`robot simulation get` is the authoritative "am I on a simulated robot" check; do not
infer it from an empty device list (a real robot with an unbound motor looks the same).

## Pitfalls

- `rms-cli` prints a variable number of INFO lines to stderr before the JSON, and some
  subcommands print the JSON twice (inline debug + final). Always parse the **last**
  JSON document, e.g. `jq -s '.[-1]'`.
- It is inside the robot's filesystem; on the sim container run it via
  `docker exec <container> /opt/data/rms/bin/rms-cli …`.
- `--node` defaults to `master`; multi-node installs need it explicitly.
- Version-dependent: `robot status` field names differ between RMS 1.2.x releases.
  Prefer `jq` paths that tolerate missing keys.
- `rms-cli` cannot cancel a navigation task. Use HTTP `/cancelNavigate` for that.
