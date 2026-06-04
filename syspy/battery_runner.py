import os
import signal
import subprocess
import sys
import time
import traceback
from typing import Callable, Optional


def _cleanup_client(client):
    if client is None:
        return
    close = getattr(client, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


def _current_process_cmdline():
    try:
        with open("/proc/self/cmdline", "rb") as f:
            raw = f.read().rstrip(b"\0")
    except Exception:
        raw = b""

    if raw:
        cmdline = [part.decode("utf-8") for part in raw.split(b"\0") if part]
        if cmdline:
            return cmdline

    return [sys.executable] + sys.argv


def run_battery_script(factory: Callable[[], object], *, init_hook: Optional[Callable[[], None]] = None, restart_delay_s: float = 2.0):
    def _handle_signal(signum, frame):
        raise SystemExit(128 + signum)

    old_sigint = signal.getsignal(signal.SIGINT)
    old_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    client = None
    try:
        if init_hook is not None:
            init_hook()
        client = factory()
        client.loop()
    except (KeyboardInterrupt, SystemExit):
        _cleanup_client(client)
    except Exception:
        _cleanup_client(client)
        traceback.print_exc()
        print(f"Battery script crashed, restarting in {restart_delay_s}s")
        time.sleep(restart_delay_s)
        cmdline = _current_process_cmdline()
        subprocess.Popen(cmdline, cwd=os.getcwd(), close_fds=True, start_new_session=True)
        os._exit(1)
    finally:
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)
