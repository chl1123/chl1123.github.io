import os
import signal
import sys
import syslog
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


def _log_to_syslog(message, level=syslog.LOG_ERR):
    try:
        syslog.openlog("battery_runner", syslog.LOG_PID, syslog.LOG_DAEMON)
        syslog.syslog(level, message)
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
    script = sys.argv[0] if sys.argv else "battery_script"
    restart_count = int(os.environ.get("BATTERY_RESTART_COUNT", "0") or "0")
    if restart_count > 0:
        _log_to_syslog(
            f"{script} recovered after crash (restart #{restart_count})",
            syslog.LOG_INFO,
        )

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
    except (KeyboardInterrupt, SystemExit) as e:
        _cleanup_client(client)
        _log_to_syslog(
            f"{script} exited via signal/SystemExit: {e!r}",
            syslog.LOG_INFO,
        )
    except Exception:
        _cleanup_client(client)
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        _log_to_syslog(f"{script} crashed, restarting in {restart_delay_s}s\n{tb}")
        print(f"Battery script crashed, restarting in {restart_delay_s}s")
        time.sleep(restart_delay_s)
        cmdline = _current_process_cmdline()
        os.environ["BATTERY_RESTART_COUNT"] = str(restart_count + 1)
        try:
            os.execvp(cmdline[0], cmdline)
        except OSError:
            tb = traceback.format_exc()
            sys.stderr.write(tb)
            _log_to_syslog(f"{script} execvp failed, exiting\n{tb}")
            os._exit(1)
    finally:
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)
