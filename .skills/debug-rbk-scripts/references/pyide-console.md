# PyIDE Live Script Console (实时脚本日志)

How to read a running script's `Trace.log` / `print` output **while it runs**, without
waiting for the ide log file. This is the fastest way to correlate script-side
decisions (`taskBuild`, `actionStateChanged`, `auto-pre …`) with navigation and
`MoveFactory` events.

## Why Not Just Read the Log File

`/opt/.data/diagnosis/rbk/logs/ide/*.log` is **not** written for every run:

- stdout/stderr of a script process is only persisted on a non-zero exit (see
  [script-debugging.md](script-debugging.md));
- on some installs (observed on a 3.5.4 sim container) the `ide` log stops growing
  for hours even though scripts run fine;
- it is multiplexed with broker/RPC DEBUG lines, so keyword filtering is painful.

The console WebSocket gives you exactly what the script printed, in order, per script.

## Endpoint

PyIDE (`pyide.service`) serves the web IDE plus a WebSocket per script:

```
http://<robot>:21006/                                   # IDE UI
http://<robot>:21006/editor                             # editor page
ws://<robot>:21006/api/v1/ws/pythonConsole?taskId=<script name>
```

`taskId` here is **not** the navigation task id. It is the script's service name as
PyIDE knows it, which is the script path relative to `scripts/`:

```bash
# list currently registered script services
curl -s "http://<robot>:21006/api/v1/ide/get_task_id_list"
# -> {"type":"response","id":null,"code":0,"data":["tasks/v3/standard/module/straddleLiftFork.py"]}

curl -s "http://<robot>:21006/api/v1/ide/get_task_info_dict"
# -> {"...": {"alive": true, "cmd": ["python3","-u","/opt/.data/rbk/resources/scripts/..."],
#             "isFirstQueryHistoryRecord": true}}
```

`get_task_info_dict.alive` is also the cheapest "is the script process up" probe.
The openapi spec lives at `http://<host>:21006/api/v1/openapi.json`; the UI's swagger
page is `/docs`.

## Reading It Without Third-Party Packages

The script interpreter inside the robot image is often Python 3.8 with **no**
`websocket-client`, and the current wheel is 3.9+ only. Do not install anything;
save this stdlib-only client as `/tmp/mini_ws.py` on the robot (or inside the
container):

```python
# /tmp/mini_ws.py - stdlib-only WebSocket client for PyIDE pythonConsole
import base64
import os
import socket
import struct
import time


class MiniWs:
    def __init__(self, url, timeout=5.0):
        assert url.startswith("ws://")
        rest = url[len("ws://"):]
        host_port, _, path = rest.partition("/")
        host, _, port = host_port.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.sock.settimeout(timeout)
        self._buf = b""
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET /%s HTTP/1.1\r\nHost: %s:%s\r\n"
               "Upgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
               % (path, host, port, key))
        self.sock.sendall(req.encode())
        data = b""
        while b"\r\n\r\n" not in data:
            data += self.sock.recv(4096)
        head, _, self._buf = data.partition(b"\r\n\r\n")
        if b"101" not in head.split(b"\r\n")[0]:
            raise RuntimeError("handshake failed: %s" % head[:80])

    def _exact(self, n):
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("connection closed")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def recv(self, timeout=None):
        if timeout is not None:
            self.sock.settimeout(timeout)
        while True:
            b1, b2 = self._exact(2)
            opcode, length = b1 & 0x0F, b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._exact(8))[0]
            payload = self._exact(length) if length else b""
            if opcode == 0x8:
                raise RuntimeError("server closed")
            if opcode in (0x9, 0xA):
                continue                      # ping / pong: ignore
            return payload.decode("utf-8", "replace")


def tail_console(script_name, duration, host="127.0.0.1", port=21006):
    ws = MiniWs("ws://%s:%d/api/v1/ws/pythonConsole?taskId=%s" % (host, port, script_name))
    end = time.monotonic() + duration
    lines = []
    while time.monotonic() < end:
        try:
            msg = ws.recv(timeout=max(0.2, end - time.monotonic()))
        except (socket.timeout, TimeoutError):
            continue
        lines.append(msg)
    return lines
```

Run it from `/tmp`, never from inside the scripts directory (see the
`SCRIPTS_DIR` trap in [standalone-probes.md](standalone-probes.md)):

```bash
cd /tmp && "$RT" -c '
import sys; sys.path.insert(0, "/tmp")
from mini_ws import tail_console
for line in tail_console("tasks/v3/standard/module/straddleLiftFork.py", 15):
    print(line[:300])'
```

Observed payload shape (one message per batch, `\r\n` separated inside):

```
**** [program success] ****
[syspy] RBK_VERSION=3, RBK_FULL_VERSION=3.5.4.0226, RBK_SIMULATION=True
log: setTaskConfig()
log: FallingDown detect enabled
2026-10-22 12:01:49.368 | log: {'event': 'taskBuild', 'taskId': '1', 'total': 1,
    'actions': [{'actionId': 'AutoPreSequence-...', 'actionType': 'AutoPreSequence', ...}]}
2026-10-22 12:02:06.565 | log: {'event': 'actionStateChanged', 'actionId': '...',
    'actionType': 'RunMotor', 'status': 'finished', 'elapsedMs': 7709}
```

The `**** [program success] ****` / `context close` lines mean PyIDE reaped the
**previous** script run and just started a new one; everything after them belongs to
the new task.

## Subscribe Before Submitting

The console only streams live. If you submit the task first and connect afterwards,
the first `taskBuild` / `AutoPreSequence` lines are gone. Correct order:

1. read `get_task_id_list` to learn the script name;
2. open the WebSocket in a background thread;
3. submit `/navigate` or `/multiPathNavigate`;
4. stop the tail after the task reaches a terminal state.

## What It Is Good For

| Question | Console line |
| --- | --- |
| Did the script even start? | `**** [program success] ****` then `setTaskConfig()` |
| Did autoPre dispatch? | `taskBuild ... 'actionType': 'AutoPreSequence'` |
| When did pre-motion run? | `actionStateChanged ... RunMotor ... finished elapsedMs=…` |
| Did the script wait for MF? | `auto-pre FINISHED reported, waiting startAction` then `auto-pre startAction latched` |
| When did the fork action enqueue? | `actionStateChanged ... GoPathWithContactDi ... status: running` |
| Why did the task fail? | the last `error`/trace line before `context close` |

Pair it with `ptcat -g rbk.nav.MoveFactory -n AutoPre…` (see
[tracing.md](tracing.md)) to compare script behaviour against what MF did.

## Pitfalls

- Wrong `taskId` silently gives a socket that never emits: always confirm the name
  from `get_task_id_list` first.
- Only one active run per script name; a second `run_python_program` replaces the
  first and the console switches to the new process.
- The console is stdout only. `Trace.log(..., output_console=False)` (most numeric
  channels: `fork.motor`, `fork.policy`, `fork.report`) **never** appears here —
  read those with `ptcat`.
- `get_task_info_dict` may keep the entry after the script exits; trust
  `alive` and the `**** [program success] ****` marker, not the list membership.
- If the robot is reached from another host, pass `host=` (container IP for the
  sim, robot IP on site); the default `127.0.0.1` only works from inside.
