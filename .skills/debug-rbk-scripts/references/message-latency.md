# RBK Message Latency Analysis

Use this procedure for DI, laser, distance-sensor, SDK message, or ZMQ latency reports. Measure each layer separately; a slow task completion does not prove a slow message read.

## Required Evidence

Retain the following around the state transition:

- The reader's last observation of the old state.
- The publisher's first changed state.
- The reader's first observation of the new state.
- Wall-clock start/end and monotonic elapsed time around the SDK call.
- The action transition caused by the new state.
- The enclosing task transition.
- RBK and SDK versions and the exact script under test.

For DI, prefer a publisher record with both the key and changed value. On observed RBK 3.5 traces, `rbk.device.DSPChassis/messageDI` with `if_di_same:false` and `status:true` is explicit rising-edge evidence. Confirm the schema for the installed version before treating an omitted `status` field as `false`.

## Find Focused Channels

Start with a narrow time window and discover metadata:

```bash
ptcat -c stat \
  -b '20260730.15:23:55' \
  -e '20260730.15:23:57' \
  rbk+common_timestamp.pft.zst |
  rg 'messageDI|fork.di_test|taskActions'
```

Query the publisher, reader, and action state separately with `-g` and `-n`. Do not begin with broad body searches for `msg`, because nearly every protocol record can match.

Records from different trace buffers may be printed out of order. Order the selected events by their trace timestamps or use an adequate `ptcat -w` reorder window. Never calculate latency from line adjacency alone.

## Instrument the Reader

Record wall time for cross-component alignment and a monotonic duration for the call itself:

```python
start_wall = time.time()
start_ns = time.perf_counter_ns()
status = bool(Di.getDi(key))
end_wall = time.time()
elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6
Trace.log(
    f"getDi: key={key}, start={start_wall:.6f}, end={end_wall:.6f}, "
    f"elapsed_ms={elapsed_ms:.3f}, status={status}",
    name="fork.di_test",
)
```

Keep this instrumentation local to the diagnostic script where possible. Shared helper changes alter more than one control variable. Logging after the call can affect the next poll phase, but it does not inflate the measured call duration captured before `Trace.log`.

## Separate the Timeline

Calculate these intervals independently:

| Interval | Start | End | What it contains |
|---|---|---|---|
| Reader poll phase | last old-state read | publisher edge | Where the edge falls between polls |
| Observable message latency | publisher edge | first new-state read start/end | Transport, SDK refresh/cache, and remaining poll phase |
| API-call duration | SDK call start | SDK call end | Blocking inside the accessor |
| Action response | first new-state return | action finished/stopped | Script tick and action handling |
| Task cleanup | action finished | task finished | Scheduler cleanup; not message latency |

Use both the call start and end when reporting publisher-to-reader timing. The start gives when the script asked; the end gives when the value was available to script logic.

An observed calculation format:

```text
publisher first True: 15:23:56.348352356
getDi start:          15:23:56.356497000  (+8.145 ms)
getDi returns True:   15:23:56.356549000  (+8.197 ms)
call duration:                                  0.051 ms
```

This proves an end-to-end observable upper bound from the traced publisher layer to the script. It does not by itself separate ZMQ transport, SDK cache refresh, and polling phase.

## Respect Clock Domains

- Trace envelope timestamps and `time.time()` are wall clocks. Compare them only when they come from the same synchronized machine or synchronization is independently established.
- `time.perf_counter_ns()` is process-local monotonic time. Use it only for durations within that process.
- Protocol `dataNsec` and `pubNsec` may use an RBK monotonic epoch. Compare them with each other only after confirming their definitions.
- Never subtract monotonic timestamps from Unix epoch timestamps.
- Preserve nanosecond precision during calculation; round only the reported result.

## Understand the SDK Boundary

Do not automatically describe `Di.getDi()` as an RPC callback. In observed SDK versions it reads message state delivered over the Python/C++ raw-message ZMQ channel and may be subject to an SDK refresh/cache interval. Verify the installed SDK source and version because implementation and cache values can change.

A fast `getDi()` call proves that the accessor did not block. It does not prove the publisher-to-reader path was fast. Conversely, a long action/task completion after a fast first-True read does not prove message latency.

If the raw message channel has no per-request trace, report only the measurable publisher-to-reader bound and explicitly state that the internal transport/cache components cannot be separated with the available evidence.

## Control Variables

Use a matrix when script logic and SDK version are both suspected:

| Run | SDK | Script | Interpretation |
|---|---|---|---|
| A | old | production module | Reproduction baseline |
| B | new | production module | Isolate SDK change |
| C | new | reduced module flow | Remove reach/expand/sensor action complexity |
| D | new | unrelated comparison script | External comparison only |

Keep recognition input, target, DI configuration, robot model, and physical trigger comparable. A passing unrelated script does not clear the production module. A reduced module flow should preserve the same recognition result, base movement API, DI accessor, and stop path while removing only the suspected extensions.

State conclusions narrowly, for example:

> With SDK X and reduced module script Y, the publisher-to-first-True delay was 8.2 ms and the accessor duration was 0.051 ms. This run did not reproduce the earlier 0.48 s delay; it does not prove that every production-script or SDK combination is unaffected.
