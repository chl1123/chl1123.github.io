# Simulation Mode (RBK Sim Container)

`RBK_SIMULATION=True` changes which failures are real. Use this file before blaming
script logic for something that only a simulated chassis produces.

Confirm the mode first:

```python
from syspy import RBK_SIMULATION, RBK_FULL_VERSION     # config-time constants
from syspy.sim import is_simulation                    # env RBK_SIMULATION wins
```

```bash
/opt/data/rms/bin/rms-cli robot simulation get          # authoritative per-node flag
```

## What Is Different

| Area | Simulation behaviour |
| --- | --- |
| Camera / recognition | no camera; `fork_utils` injects a result file via `tests/fork_sim_inject.py` (`FORK_SIM_FILE`, default `/tmp/fork_sim_rec_result.json`) |
| Contact / fork-tip DI | no physical DI; geometry-based fake trigger inside `_read_contact_di` when a sim injector is importable |
| Chassis motors | walk motors accumulate an **unbounded** odometer value; position is not a wheel angle |
| Velocity | capped low (~0.15–0.5 m/s) and has long accel/decel ramps, so a 2 m move can take 6 s and a 5 m move 13 s |
| `MF` ETA model | `AutoPreETABreakdown.source: mf_static_model`, `maxDec: 0.15` — it predicts a trapezoid the simulated chassis cannot follow, so `AutoPreETAResult.errorSeconds` is routinely 8–28 s off |

## Known Simulation Traps (each one looks like a script bug)

### 1. Walk motors drift, then the chassis stops responding

Symptom: `/navigate` returns `retCode:0`, `NavStatus.taskStatus=RUNNING`, MF
`moveTask` shows `distance` frozen, `NavSpeed.getSpeeds()==(0,0,0)` and the pose does
not change for minutes.

Check:

```python
from syspy import Motor, Navigation
[Motor.getMotorPos(m) for m in ("Motor-000", "Motor-001")]   # e.g. [20.91, 8.92]
Navigation.isPathReached()                                    # may be True
```

When the two walk motors diverge (or exceed their configured range) the simulated
chassis stops accepting motion. **Only a container/RBK restart clears it.** Do not
chase this in the script.

### 2. Raising the fork stops the chassis

Observed on a 3.5.4 sim: after an action lifts the fork to `startHeight=0.35`, the next
`/navigate` reports RUNNING but never moves. `startHeight<=0.2` behaves normally.
Practical rule for sim runs: keep `startHeight` at or below 0.2, and if a run
suddenly stops moving after a lift, restart the container before re-testing.

### 3. `Navigation.hasGoods()` and `Container.hasGoods("0")` diverge

After a simulated `load`, `Navigation.hasGoods()` can stay `True` while
`Container.hasGoods("0")` is already `False`. The next `load` then fails with
`py@ForkHasGoods` before the action queue is even built.

Clearing attempts that were observed **not** to work:

```python
Container.unbindContainer("0")
Navigation.clearGoodsShape()
```

`tools_leveldb` writes succeed (the `containers` and `move` leveldb show `hasGoods: false`),
but MF's in-memory cargo state keeps the stale value until the process restarts.
**Restart RBK** and verify before the next case:

```bash
curl -s 'http://127.0.0.1:8081/getSpecifiedFieldsAIO?includedFields=navigation' \
  | jq -c '(.data.navigation // .navigation).moveStatusInfo | fromjson | .containers'
# want: [{"containerId":"0","desc":"","goodsName":"","hasGoods":false}]
```

### 4. `insightd` does not autostart

See [tracing.md](tracing.md) — a restart leaves it `inactive`, so traces silently stop.

### 5. Map gets stuck on the previous map

`Map.switchMap(name, point)` can return `0` while `Map.getCurrentMapName()` still
reports the old map (the workspace list no longer contains the target map). Symptom:
`/navigate` between two stations of the *displayed* map fails with
`ms@3066PathFailed: Cannot find Path between: {1},{2}`. Switch the map in the web UI,
then re-read `getSiteDataList()` before trusting any station name.

### 6. Some station pairs are not connected

Not every pair of stations on a test map has an edge. A 3066 leg between them fails
with `ms@3066PathFailed … Cannot find Path between: 7,8`. Verify a candidate route
pair by pair with a single-segment `/navigate` before building a multi-segment case.

## Designing a Simulation Test That Proves Something

1. Start from a clean state: walk motors ~0, `containers[0].hasGoods=false`, fork at
   `min_height`, no leftover `py@…` robot error, `NavStatus` taskId of the previous run.
2. Use a route whose segments you already validated individually.
3. Keep `startHeight<=0.2`.
4. Subscribe to the PyIDE console **before** submitting ([pyide-console.md](pyide-console.md)).
5. Make sure `insightd` is running before you rely on `ptcat`.
6. Record per-poll `Odometer.getSpeeds()` rather than only start/end poses — a "stuck"
   chassis and a "slow" chassis look identical in poses, but not in speed.
7. Compare MF's own numbers instead of guessing: `AutoPreETAResult.errorSeconds`,
   `AutoPreETASegmentResult.finishReason`, `3066TaskCheck`, `moveTask.distance`.
   When MF's static model is wrong, quote its error rather than calling the script slow.

## Reporting

Always state explicitly which findings are simulation artefacts. A legitimate claim
needs either a real robot, or an MF/script log line that is independent of the
simulated chassis dynamics.
