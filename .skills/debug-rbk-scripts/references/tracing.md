# insightd and Perfetto Trace Collection

For symptom-to-channel routing (script RPC `Rc`/`Rs`, navigation, localization, map,
and device channels), read [triage.md](triage.md) first. This file covers the trace
mechanics: layout, finalization, and `ptcat` invocation.

## Getting `ptcat`

`ptcat` reads `.pft` / `.pft.zst` traces and is not always on `PATH`. Resolve it in this
order; never assume a fixed path:

1. Already on `PATH`: `command -v ptcat` (some machines add it via `~/.zshrc` or
   `~/.bashrc`).
2. The robot's tool directory: `ls /opt/data/rbk/tools | rg -i 'ptcat|trace'`.
3. Otherwise, ask the user. On the Feishu/Lark online AI environment, request the tool
   from this document: `https://seer-group.feishu.cn/docx/RIDEdz8pCogIHgxdFzdcTTEtnTf`
   (download the `ptcat` tool). Report that the trace cannot be read without it rather
   than guessing.

```bash
PT=ptcat                       # default when on PATH
command -v ptcat >/dev/null || PT=/opt/data/rbk/tools/ptcat
command -v "$PT" >/dev/null || echo "ptcat unavailable: ask the user / fetch per Feishu doc"
```

If `ptcat` is unavailable, the trace is still partially readable with
`zstd -dc trace.pft.zst | strings -n 12 | rg '<pattern>'`, but string order is not a
substitute for timestamped Perfetto events. State that limitation explicitly.

## Live Debugging Versus Evidence Finalization

Use `ptcat` against the active trace for iterative, real-time debugging when a
durable artifact is not required. This avoids rolling the trace after every
probe. Discover or apply focused category/name filters as described below.

Call insightd `/sync` only when a finalized trace is needed for durable evidence,
handoff, defect reporting, or repeatable offline analysis. `/sync` is not a
prerequisite for reading current events with `ptcat`.

## Verified Layout

On the observed RBK 3.5 installation:

- Service: `insightd.service`
- Binary: `/usr/share/perfetto-trace/x86_64/insightd`
- Query server: `http://127.0.0.1:8019`
- Trace directory: `/opt/.data/diagnosis/rbk/trace/event`
- Common trace: `rbk+common_<timestamp>.pft.zst`
- Active temporary trace: `rbk+common_<timestamp>.__temp__.pft.zst`
- Event report: `rbk+report.jsonl`

Confirm rather than assume:

```bash
systemctl status insightd.service --no-pager -l
systemctl show-environment | rg '^INSIGHTD'
curl -sS --max-time 3 http://127.0.0.1:8019/config
```

## Immediate Finalization

Use the query server instead of restarting services or sending guessed signals:

```bash
curl -sS --max-time 10 http://127.0.0.1:8019/sync
```

An observed response was:

```json
{"wait_sec":5,"label":"2026-07-30_18-19-20"}
```

Wait for the returned interval plus a small margin, then select the newest finalized `rbk+common_*.pft.zst` that does not contain `.__temp__`. Do not infer the final filename from `label`; the filename can retain the active segment's earlier start time.

The common runner was observed with store-on-the-fly enabled and roughly 15-minute natural rollovers. `/sync` forced a rollover in about five seconds.

## Reports and Focused Evidence

`GET /report` returns a recent JSON event list. The observed daemon retained up to 500 report entries and 10 recent minutes. It is useful for immediate task status/error extraction, but it is not a substitute for the finalized trace.

```bash
curl -sS --max-time 10 http://127.0.0.1:8019/report |
jq --arg task_id 'exact-task-id' \
  '{events:[.list[] | select((.da|tostring)|contains($task_id))]}'
```

Also retain matching lines from `rbk+report.jsonl`. Verify that the finalized binary trace contains the task ID:

```bash
zstd -dc /path/to/rbk+common_timestamp.pft.zst |
strings -n 12 | rg 'exact-task-id'
```

The string check proves inclusion only. Use Perfetto/trace tooling for semantic event analysis.

## Focused `ptcat` Queries

Always pick the category/name from the symptom first; see the channel tables in
[triage.md](triage.md). The high-value groups are:

| Category | Channels |
| --- | --- |
| `rbk.script.utils_rpc` | `Rc`, `RcError`, `Rs`, `RsError`, `BinMsgChannel`, script-defined channels |
| `rbk.nav.MoveFactory` | navigation action tasks (runtime group) |
| `rbk.loc.MCLoc` | `locationEachFrame`, `locByNDT`, `eKFLocalizationFusion`, `locationbyRef`, ... |
| `rbk.loc.BlockMapLoader` | `changeMap` |
| `rbk.device.DSPChassis` | `motorInfo`, `messageDI`, `messageDO`, `distanceInfo`, ... |

Discover category/name pairs before filtering message text:

```bash
ptcat -c stat -b '20260730.15:23:55' -e '20260730.15:23:57' trace.pft.zst |
  rg 'messageDI|fork.di_test'
```

Then query exact producers and consumers:

```bash
ptcat -b '20260730.15:23:55' -e '20260730.15:23:57' \
  -g 'rbk.device.DSPChassis' -n 'messageDI' trace.pft.zst

ptcat -b '20260730.15:23:55' -e '20260730.15:23:57' \
  -g 'rbk.script.utils_rpc' -n 'fork.di_test' trace.pft.zst
```

Avoid broad text filters such as `msg|message|DI`; they include unrelated high-frequency channels and can truncate the useful output. `ptcat` output may arrive outside timestamp order when records come from different buffers. Sort by the event timestamp or use a suitable `-w` reorder window before calculating intervals.

### `ptcat` output columns

A line looks like:

```text
[20261013.10:06:27.265.369.108][rbk.script.utils_rpc][Rs.probe.py][xx-7b87915c][0][295703]: {…}
[20261013.10:04:37.865.081.577][rbk.script.utils_rpc][Rs][I]: {"init":"complete"}
```

| Column | Field | Meaning |
| --- | --- | --- |
| `20261013.10:06:27.265.369.108` | `tsstr` | event timestamp |
| `rbk.script.utils_rpc` | `cats` | category |
| `Rs.probe.py` | `name` | event name (the channel you filter with `-n`) |
| `xx-7b87915c` | track id | which lane the event is drawn on; **not** a client id |
| `0` | `depth` | slice nesting depth |
| `295703` | `dur` | slice duration, ns |
| `[I]` | level | only on `TR_LOG` lines |

`TR_EVENT` emits a **slice** (start plus duration), `TR_LOG` emits an **instant log**
line. That is why the two kinds print a different number of columns: a `TR_LOG` line
has the level instead of track/depth/dur. Do not read the track id as an identity.
Use `-j` when you want the field names explicitly:

```bash
ptcat -j -g "rbk.script.utils_rpc" -n "^Rs\\." "$T" | head -1
```

### Name matching is regex substring, not exact

`-n` and `-g` take a C++ `std::regex` literal matched anywhere in the field, so
`-n "Rs"` matches `Rs`, `RsError`, and `Rs.probe.py` alike. Anchor or qualify when you
need precision: `-n "^Rs$"` for server lifecycle events only, `-n "^Rs\\."` for
per-caller request events only, `-n "<script name>"` to pull one script's traffic.

### Script RPC channels are split per caller

Request and error events carry the calling script in the channel name:

```text
Rb.probe.py     request slice, one per non-silent RPC
RsError.jack.py request error (parse failure, crash, send failure)
Rs              server lifecycle and counters (bind, init, ioLoop, io stat) — no caller
RsError         errors raised before/after a caller is known (socket recv/send)
```

The channel name uses the script's **basename**, while the `caller` field keeps the
full script id (for example `tasks/v3/standard/module/jack.py`). So to find who is
flooding one interface:

```bash
# Every caller that used one method
ptcat -g "rbk.script.utils_rpc" -n "^Rs\\." "$T" | rg 'NetProtocol::setModbusData'

# One script's requests only
ptcat -g "rbk.script.utils_rpc" -n "Rs\\.jack\\.py" "$T"
```

The `kSilentRpcMethods` set in `rpcServer.cpp` (`Trace::traceLog`, `Trace::traceLogD`,
`MoveFactory::setInfo`) deliberately emits no `Rs.*` event, so high-frequency trace
writes do not amplify into the trace. An RPC call with no matching `Rs.*` event is
usually a silenced method, not a lost request.

For publisher-to-script timing, state transitions, clock-domain rules, and causal limits, read [message-latency.md](message-latency.md).

`GET /perf` can initiate an additional performance capture and create a `rbk+perf_*.pft` file. Do not call it during routine log flushes unless that capture is intended. Treat `/debug` and undocumented query endpoints as version-specific until verified.

## Collection Script

Run:

```bash
# scripts/collect-rbk-evidence.sh from this skill directory
./scripts/collect-rbk-evidence.sh \
  --out /tmp/rbk-evidence \
  --task-id exact-task-id \
  --copy-trace
```

The script calls `/sync`, honors `wait_sec`, finds the finalized trace, copies report data, filters events by exact task ID, and writes a manifest. Without `--copy-trace`, it records the source trace path without duplicating the large file.
