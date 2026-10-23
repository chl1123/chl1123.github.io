# Standalone Probes: Run Scripts Against a Live RBK

How to run a script or a few RPC calls directly against a running RBK, without
MoveFactory or PyIDE. Use this to isolate a script-side defect, to verify a syspy
change, or to produce a trace with only your own events in it.

This bypasses the normal dispatch path, so it proves **script/syspy/RPC** behavior
only. It does not prove MF or PyIDE routing — for that, read
[mf-script-rpc.md](mf-script-rpc.md).

## Pick the Interpreter First

The script runtime is the **interpreter PyIDE bundles**, not the system `python3`.
On a controller the system Python version follows the OS release (20.04 -> 3.8,
22.04 -> 3.10, 24.04 -> 3.12) while the bundled runtime is fixed. Using the wrong
one produces conclusions that do not hold in production — most visibly, syntax
such as `match` or `X | Y` annotations runs under 3.10+ and fails on a 3.8 controller.

Resolve it once and use that everywhere below:

```bash
# Bundled runtime (matches production). Falls back only on PyIDE old enough to
# have no bundled interpreter, where the system python3 was the runtime.
RT=/opt/data/pyide/runtime/python/bin/python3
[ -x "$RT" ] || RT=python3
"$RT" -V
```

Every `python3` in this file means `$RT`. Confirm which one you are on before
concluding anything about a version-dependent failure.

## Preconditions

The RPC sockets must exist, which means RBK is up:

```bash
ls -l /tmp/python2cpp_rpc.ipc      # script <-> C++ RPC (REQ/ROUTER, JSON-RPC)
ls -l /tmp/cpp2broker.ipc          # script <-> PyIDE broker
```

If `python2cpp_rpc.ipc` is absent, RBK is not running (or not finished starting).
A single call against a missing socket blocks for the client timeout,
`_RPC_RECV_TIMEOUT_MS = 3000` (3 s), then raises `TimeoutError`. Do not put such a
call on a startup path without checking the socket first.

## The `SCRIPTS_DIR` Trap

`syspy.utils.SCRIPTS_DIR` is the **literal** string `/opt/.data/rbk/resources/scripts/`,
while `param_server._get_prefix_dir` validates `__file__.startswith(SCRIPTS_DIR)`.
On installations where `/opt/.data/rbk/resources/scripts` is a symlink (for example
to `/mnt/log/3.5/rbk/resources/scripts`), the two spellings disagree and the import
fails. Whether it fails depends on **how you start Python**, not on the code:

| Invocation | `__file__` becomes | Result |
| --- | --- | --- |
| `cd /opt/.data/rbk/resources/scripts && $RT x.py` | `/mnt/log/...` (cwd resolved through the symlink) | `ValueError: script path error` |
| `cd /tmp && $RT -c "sys.path.insert(0, '/opt/.data/rbk/resources/scripts')"` | `/opt/.data/...` (literal path kept) | works |

So: **never `cd` into the scripts directory to run something.** Put the literal
`/opt/.data/...` path on `sys.path` from elsewhere.

```bash
# Run from anywhere except the scripts directory itself
cd /tmp
"$RT" - <<'PY'
import sys
sys.path.insert(0, "/opt/.data/rbk/resources/scripts")
from syspy import Module, NetProtocol
PY
```

The same rule applies to running a repository test file:

```bash
sudo env PYTHONPATH=/opt/.data/rbk/resources/scripts \
  "$RT" /opt/.data/rbk/resources/scripts/tests/test_example.py TestClass.test_name
```

## Minimal Probe

`Trace.log` works as soon as `syspy` is importable; it does not require
`Module.init()`. Call `Module.init()` only when you need a script identity (so the
trace shows `caller=<script>`) or the task/RPC server.

```python
import sys
sys.path.insert(0, "/opt/.data/rbk/resources/scripts")

from syspy import Module, NetProtocol, Trace
from syspy.utils import ScriptType

Module.init(script_type=ScriptType.GENERAL)          # optional: sets script identity

Trace.log("probe: script channel works", name="syspy.verify")
NetProtocol.getModbusData("3x", 0, 1)                # a real RPC, to exercise the server
```

Run it and read the output:

```bash
cd /tmp && "$RT" probe.py
```

Expected stdout, and what each line proves:

```
[syspy] RBK_VERSION=3, RBK_FULL_VERSION=3.5.4.0210, RBK_SIMULATION=True   # syspy config loaded
log: {'scriptName': 'probe.py', ...}                                      # Module.init via Trace
log: probe: script channel works                                          # your channel
```

## Reading the Result in the Trace

Standalone runs are the cleanest way to verify a channel: the segment contains your
events and little else.

```bash
TRACE_DIR=/opt/.data/diagnosis/rbk/trace/event
T=$(ls -t "$TRACE_DIR"/rbk+common_*.pft.zst | grep -v __temp__ | head -1)

# Your own channels
ptcat -g "rbk.script.utils_rpc" -n "syspy.verify" "$T"

# Server-side request events, now split per caller
ptcat -g "rbk.script.utils_rpc" -n "^Rs\." "$T"
```

`ptcat -n` is a **regex substring** match, not anchored. `-n "Rs"` therefore matches
both `Rs` and `Rs.probe.py`; add `\.` or `$` to narrow it.

### `ptcat` line columns

A line looks like:

```
[20261013.10:06:27.265.369.108][rbk.script.utils_rpc][Rs.probe.py][xx-7b87915c][0][295703]: {…}
```

| Field | Meaning |
| --- | --- |
| `20261013.10:06:27.265.369.108` | event timestamp (`tsstr`) |
| `rbk.script.utils_rpc` | category (`cats`) |
| `Rs.probe.py` | event name (`name`) |
| `xx-7b87915c` | track id (which lane the event is drawn on) |
| `0` | slice nesting depth (`depth`) |
| `295703` | slice duration in ns (`dur`) |
| `[I]` (on `TR_LOG` lines) | log level; `TR_EVENT` lines show track/depth/dur instead |

`TR_EVENT` produces a slice (has start and duration); `TR_LOG` produces an instant
log line. That is why the two kinds have different column counts — do not read the
track id as a client id. Use `-j` to get the field names directly:

```bash
ptcat -j -g "rbk.script.utils_rpc" -n "^Rs\." "$T" | head -1
```

## Verifying a syspy Change

A standalone probe is the fastest loop for a change under `syspy/`:

1. Edit the file in the checkout.
2. Run the probe (from a non-scripts cwd, per the trap above).
3. Confirm stdout, then confirm the trace with `ptcat`.

Note that `/opt/.data/rbk/resources/scripts` may be a **bind mount** of the checkout,
so an edit in the repository is visible to the probe immediately — verify with
`readlink -f` before assuming you need to copy files:

```bash
readlink -f /opt/.data/rbk/resources/scripts   # where the mounted tree really lives
```

`__pycache__` under the scripts tree can be owned by the container's root when the
same tree is used from a container, which makes `$RT -m compileall` fail with
`PermissionError`. Use `ast.parse` for a syntax check in that case, or remove the
cache from inside the container.

## Do Not Use `logging` for Framework Output

If `syspy` needs to log before `Trace` is available (for example `syspy/config.py`,
which runs before `Trace` is bound and itself produces `RBK_VERSION`), do not fall
back to bare `logging` and expect it to appear anywhere. On a real installation the
`rbk.script` logger has **no handlers** and an effective level of `WARNING`, so
`debug`/`info` are silently dropped:

```
handlers: []
effective level: 30          # WARNING -> debug/info lost
```

Only `warning` and above reach stderr, and script stdout/stderr is not written to a
file except on a non-zero exit (see [script-debugging.md](script-debugging.md)).
Options that do work: buffer and replay through `Trace` once it is bound, keep a
plain `print` for the few startup lines, or fail fast with an exception.
