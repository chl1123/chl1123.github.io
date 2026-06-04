#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMX512 RS485 simulator with Tkinter renderer.

========================
中文使用说明（启动方法）
========================

用途：
1) 创建一个虚拟串口（PTY）来接收 DMX512 串口数据。
2) 使用 Tkinter 窗口模拟灯珠显示（支持 car/line/grid/ring 布局）。

推荐启动步骤（与 BehavFactory 联调）：
1) 先停止 rbk（避免 BehavFactory 已经占用并固定了旧串口 fd）。
2) 启动本脚本并创建串口映射，例如：
   sudo python3 tasks/v3/standard/example/dmx512_serial_sim.py \
     --led-count 4 --channel-map 0,2,3,1 --layout car --show-values \
     --mock-link /dev/RS485_0
3) 观察脚本输出：
   - [dmx-sim] symlink: /dev/RS485_0 -> /dev/pts/xx
   - [dmx-sim] receive from virtual serial: /dev/pts/xx
4) 再启动 rbk；此时 BehavFactory 往 /dev/RS485_0 发送的数据会进入模拟器并在 UI 渲染。

快速自测（不依赖外部发送端）：
python3 tasks/v3/standard/example/dmx512_serial_sim.py --demo-send --show-values
"""

import argparse
import colorsys
import math
import os
import pty
import select
import signal
import sys
import threading
import time
import tty
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple


def _parse_channel_map(text: str) -> Tuple[int, int, int, int]:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError(f"channel-map must have 4 items, got: {text}")
    values = tuple(int(p) for p in parts)
    if sorted(values) != [0, 1, 2, 3]:
        raise ValueError(f"channel-map must be a permutation of 0,1,2,3, got: {values}")
    return values  # type: ignore[return-value]


@dataclass
class LedRGBA:
    r: int
    g: int
    b: int
    w: int


class DmxFrameParser:
    """Parse fixed-length DMX frames from a PTY byte stream.

    真正的 DMX512 依赖 break + MAB 做帧边界，而 PTY 流里看不到这个边界。
    payload 内部本来就会大量出现 0x00，所以不能再把 start code 0 当作可靠分隔符。
    对联调场景，我们约定发送端按固定长度持续写帧，这里直接按长度切块即可。
    """

    def __init__(self, led_count: int):
        self.expected_len = 1 + 4 * int(led_count)
        self._buffer = bytearray()

    def feed(self, data: bytes) -> List[bytes]:
        if not data:
            return []
        self._buffer.extend(data)
        out: List[bytes] = []

        while len(self._buffer) >= self.expected_len:
            frame = bytes(self._buffer[: self.expected_len])
            del self._buffer[: self.expected_len]
            out.append(frame)

        return out


def _decode_frame(frame: bytes, led_count: int, channel_map: Sequence[int]) -> List[LedRGBA]:
    leds: List[LedRGBA] = []
    for i in range(led_count):
        base = 1 + i * 4
        if base + 3 >= len(frame):
            break
        r = frame[base + channel_map[0]]
        g = frame[base + channel_map[1]]
        b = frame[base + channel_map[2]]
        w = frame[base + channel_map[3]]
        leds.append(LedRGBA(r=r, g=g, b=b, w=w))
    return leds


def _encode_frame(leds: Sequence[LedRGBA], channel_map: Sequence[int]) -> bytes:
    raw = bytearray(1 + 4 * len(leds))
    raw[0] = 0
    for i, led in enumerate(leds):
        base = 1 + i * 4
        chan = [0, 0, 0, 0]
        chan[channel_map[0]] = int(led.r) & 0xFF
        chan[channel_map[1]] = int(led.g) & 0xFF
        chan[channel_map[2]] = int(led.b) & 0xFF
        chan[channel_map[3]] = int(led.w) & 0xFF
        raw[base : base + 4] = bytes(chan)
    return bytes(raw)


def _format_leds_for_log(leds: Sequence[LedRGBA]) -> str:
    if not leds:
        return "[]"
    return " ".join(
        f"L{i + 1}(R{led.r:3d},G{led.g:3d},B{led.b:3d},W{led.w:3d})"
        for i, led in enumerate(leds)
    )


def _mix_rgbw_for_display(led: LedRGBA) -> Tuple[int, int, int]:
    # Convert RGBW to display RGB: white channel adds equally to RGB.
    r = min(255, led.r + led.w)
    g = min(255, led.g + led.w)
    b = min(255, led.b + led.w)
    return r, g, b


def _color_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _set_raw(fd: int) -> None:
    try:
        tty.setraw(fd)
    except Exception:
        pass


class PtyDmxReceiver:
    def __init__(
        self,
        master_fd: int,
        led_count: int,
        channel_map: Sequence[int],
        on_frame: Callable[[List[LedRGBA], bytes], None],
        *,
        print_rgbw: bool = False,
        print_interval_ms: int = 200,
    ):
        self.master_fd = master_fd
        self.channel_map = tuple(channel_map)
        self.on_frame = on_frame
        self.parser = DmxFrameParser(led_count)
        self.led_count = int(led_count)
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.frame_count = 0
        self.print_rgbw = bool(print_rgbw)
        self.print_interval_sec = max(0.0, float(print_interval_ms) / 1000.0)
        self._last_print_time = 0.0
        self._last_print_signature: Optional[Tuple[Tuple[int, int, int, int], ...]] = None

    def start(self) -> None:
        if self.thread is not None:
            return
        self.thread = threading.Thread(target=self._run, daemon=True, name="dmx_rx")
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)

    def _maybe_print_frame(self, leds: Sequence[LedRGBA], frame: bytes) -> None:
        if not self.print_rgbw:
            return

        signature = tuple((led.r, led.g, led.b, led.w) for led in leds)
        now = time.monotonic()
        if now - self._last_print_time < self.print_interval_sec:
            return
        if signature == self._last_print_signature and self.print_interval_sec > 0.0:
            return

        self._last_print_time = now
        self._last_print_signature = signature
        print(
            f"[dmx-sim] frame={self.frame_count} bytes={len(frame)} "
            f"rgbw={_format_leds_for_log(leds)}",
            flush=True,
        )

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
                if not r:
                    continue
                data = os.read(self.master_fd, 4096)
                if not data:
                    time.sleep(0.005)
                    continue
                frames = self.parser.feed(data)
                for frame in frames:
                    leds = _decode_frame(frame, self.led_count, self.channel_map)
                    self.frame_count += 1
                    self._maybe_print_frame(leds, frame)
                    self.on_frame(leds, frame)
            except OSError:
                break
            except Exception:
                time.sleep(0.01)


class DemoDmxSender:
    """Internal demo sender, useful when no external sender is connected."""

    def __init__(
        self,
        write_fd: int,
        led_count: int,
        channel_map: Sequence[int],
        fps: float = 30.0,
    ):
        self.write_fd = write_fd
        self.led_count = int(led_count)
        self.channel_map = tuple(channel_map)
        self.fps = max(1.0, float(fps))
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.thread is not None:
            return
        self.thread = threading.Thread(target=self._run, daemon=True, name="dmx_demo_tx")
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)

    def _run(self) -> None:
        step = 1.0 / self.fps
        while not self.stop_event.is_set():
            now = time.time()
            leds: List[LedRGBA] = []
            for i in range(self.led_count):
                hue = (now * 0.12 + i / max(1, self.led_count)) % 1.0
                rr, gg, bb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                w = int((math.sin(now * 2.8 + i * 0.8) + 1.0) * 30.0)
                leds.append(
                    LedRGBA(
                        r=int(rr * 255),
                        g=int(gg * 255),
                        b=int(bb * 255),
                        w=max(0, min(255, w)),
                    )
                )
            frame = _encode_frame(leds, self.channel_map)
            try:
                os.write(self.write_fd, frame)
            except OSError:
                break
            time.sleep(step)


class DmxTkRenderer:
    def __init__(
        self,
        led_count: int,
        *,
        layout: str = "car",
        fps: float = 30.0,
        show_values: bool = True,
        title: str = "DMX512 RS485 Simulator",
    ):
        try:
            import tkinter as tk
        except Exception as exc:
            raise RuntimeError(f"Tkinter unavailable: {exc}") from exc

        self.tk = tk
        self.led_count = int(led_count)
        self.layout = str(layout).strip().lower()
        self.fps = max(5.0, float(fps))
        self.show_values = bool(show_values)
        self.title = title

        self._lock = threading.Lock()
        self._target: List[LedRGBA] = [LedRGBA(0, 0, 0, 0) for _ in range(self.led_count)]
        self._display: List[List[float]] = [[0.0, 0.0, 0.0, 0.0] for _ in range(self.led_count)]
        self._last_frame_time = 0.0
        self._frame_counter = 0
        self._closed = False

        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.geometry("920x520")
        self.root.configure(bg="#14181f")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.canvas = tk.Canvas(self.root, width=900, height=460, bg="#1f2430", highlightthickness=0)
        self.canvas.pack(padx=10, pady=(10, 2), fill="both", expand=True)
        self.status_var = tk.StringVar(value="Waiting for DMX frame...")
        self.status = tk.Label(
            self.root,
            textvariable=self.status_var,
            fg="#e8eef5",
            bg="#14181f",
            anchor="w",
            font=("TkDefaultFont", 10),
        )
        self.status.pack(fill="x", padx=10, pady=(0, 8))

        self._led_items: List[int] = []
        self._label_items: List[int] = []
        self._value_items: List[int] = []
        self._init_scene()

    def _positions(self, width: int, height: int) -> List[Tuple[float, float]]:
        n = self.led_count
        if n <= 0:
            return []

        if self.layout == "line":
            margin = 70
            span = max(10.0, width - 2 * margin)
            return [(margin + span * i / max(1, n - 1), height * 0.52) for i in range(n)]

        if self.layout == "grid":
            cols = int(math.ceil(math.sqrt(n)))
            rows = int(math.ceil(n / cols))
            x_gap = width / (cols + 1)
            y_gap = height / (rows + 1)
            out: List[Tuple[float, float]] = []
            for i in range(n):
                r = i // cols
                c = i % cols
                out.append(((c + 1) * x_gap, (r + 1) * y_gap))
            return out

        if self.layout == "car" and n == 4:
            cx, cy = width * 0.5, height * 0.5
            dx, dy = width * 0.22, height * 0.22
            return [
                (cx - dx, cy - dy),  # left front
                (cx - dx, cy + dy),  # left rear
                (cx + dx, cy - dy),  # right front
                (cx + dx, cy + dy),  # right rear
            ]

        # fallback: ring layout
        cx, cy = width * 0.5, height * 0.5
        radius = min(width, height) * 0.34
        out = []
        for i in range(n):
            ang = -math.pi / 2 + 2 * math.pi * i / n
            out.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
        return out

    def _init_scene(self) -> None:
        self.canvas.delete("all")
        w = max(600, self.canvas.winfo_width() or 900)
        h = max(320, self.canvas.winfo_height() or 460)
        pos = self._positions(w, h)

        self._led_items.clear()
        self._label_items.clear()
        self._value_items.clear()

        if self.layout == "car" and self.led_count == 4:
            self.canvas.create_rectangle(w * 0.28, h * 0.30, w * 0.72, h * 0.70, outline="#394559", width=2)
            self.canvas.create_text(w * 0.50, h * 0.25, text="front", fill="#607087", font=("TkDefaultFont", 10))

        for i, (x, y) in enumerate(pos):
            rr = 34
            oval = self.canvas.create_oval(
                x - rr,
                y - rr,
                x + rr,
                y + rr,
                fill="#0a0d12",
                outline="#58677d",
                width=2,
            )
            label = self.canvas.create_text(
                x,
                y - rr - 14,
                text=f"LED {i + 1}",
                fill="#c9d3df",
                font=("TkDefaultFont", 10, "bold"),
            )
            values = self.canvas.create_text(
                x,
                y + rr + 14,
                text="R0 G0 B0 W0",
                fill="#8ea0b6",
                font=("TkDefaultFont", 9),
            )
            self._led_items.append(oval)
            self._label_items.append(label)
            self._value_items.append(values)

    def on_frame(self, leds: List[LedRGBA], _raw: bytes) -> None:
        with self._lock:
            for i in range(self.led_count):
                if i < len(leds):
                    self._target[i] = leds[i]
                else:
                    self._target[i] = LedRGBA(0, 0, 0, 0)
            self._last_frame_time = time.time()
            self._frame_counter += 1

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def _tick(self) -> None:
        if self._closed:
            return

        with self._lock:
            target = [LedRGBA(x.r, x.g, x.b, x.w) for x in self._target]
            last_ts = self._last_frame_time
            fc = self._frame_counter

        # smooth transition for nicer animation
        smooth = 0.35
        for i in range(self.led_count):
            self._display[i][0] += (target[i].r - self._display[i][0]) * smooth
            self._display[i][1] += (target[i].g - self._display[i][1]) * smooth
            self._display[i][2] += (target[i].b - self._display[i][2]) * smooth
            self._display[i][3] += (target[i].w - self._display[i][3]) * smooth

            shown = LedRGBA(
                int(max(0, min(255, self._display[i][0]))),
                int(max(0, min(255, self._display[i][1]))),
                int(max(0, min(255, self._display[i][2]))),
                int(max(0, min(255, self._display[i][3]))),
            )
            fill_hex = _color_to_hex(_mix_rgbw_for_display(shown))
            outline = _color_to_hex((120 + shown.w // 2, 120 + shown.w // 2, 130 + shown.w // 2))
            self.canvas.itemconfigure(self._led_items[i], fill=fill_hex, outline=outline)

            if self.show_values:
                txt = f"R{shown.r:3d} G{shown.g:3d} B{shown.b:3d} W{shown.w:3d}"
                self.canvas.itemconfigure(self._value_items[i], text=txt, state="normal")
            else:
                self.canvas.itemconfigure(self._value_items[i], state="hidden")

        now = time.time()
        age_ms = int((now - last_ts) * 1000) if last_ts > 0 else -1
        if age_ms < 0:
            status = f"Frames: {fc} | waiting for first DMX frame..."
        else:
            stale = "STALE" if age_ms > 500 else "LIVE"
            status = f"Frames: {fc} | Last frame age: {age_ms} ms | {stale}"
        self.status_var.set(status)

        interval_ms = int(1000.0 / self.fps)
        self.root.after(interval_ms, self._tick)

    def run(self) -> None:
        self.root.update_idletasks()
        self._init_scene()
        self._tick()
        self.root.mainloop()


def _install_symlink(target: str, link_path: Optional[str]) -> None:
    if not link_path:
        return
    try:
        if os.path.lexists(link_path):
            os.remove(link_path)
        os.symlink(target, link_path)
        print(f"[dmx-sim] symlink: {link_path} -> {target}")
    except Exception as exc:
        print(f"[dmx-sim] WARN: failed to create symlink {link_path}: {exc}")


def _write_text_file(path: Optional[str], text: str) -> None:
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[dmx-sim] wrote: {path}")
    except Exception as exc:
        print(f"[dmx-sim] WARN: failed to write {path}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="DMX512 RS485 simulator + Tkinter renderer")
    parser.add_argument("--led-count", type=int, default=4, help="虚拟灯珠数量")
    parser.add_argument("--channel-map", type=str, default="0,2,3,1", help="通道映射顺序，例如 0,2,3,1")
    parser.add_argument("--layout", type=str, default="car", choices=["car", "line", "grid", "ring"], help="UI 布局")
    parser.add_argument("--fps", type=float, default=30.0, help="渲染帧率")
    parser.add_argument("--show-values", action="store_true", help="显示每颗灯的 RGWB 数值")
    parser.add_argument("--print-rgbw", action="store_true", help="终端打印收到的逐灯 RGBW 数据")
    parser.add_argument("--print-interval-ms", type=int, default=200, help="终端打印最小间隔（毫秒）")
    parser.add_argument("--mock-link", type=str, default="/tmp/ttyS8", help="给发送端使用的软链接路径（如 /dev/RS485_0）")
    parser.add_argument("--port-file", type=str, default="", help="可选：将生成的从串口路径写入文件")
    parser.add_argument("--demo-send", action="store_true", help="内部启用演示发送（彩色动画）")
    args = parser.parse_args()

    led_count = max(1, int(args.led_count))
    channel_map = _parse_channel_map(args.channel_map)

    master_fd, slave_fd = pty.openpty()
    _set_raw(master_fd)
    _set_raw(slave_fd)
    slave_path = os.ttyname(slave_fd)

    _install_symlink(slave_path, args.mock_link)
    _write_text_file(args.port_file.strip() or None, slave_path)
    print(f"[dmx-sim] receive from virtual serial: {slave_path}")
    print("[dmx-sim] tip: 请将 DMX 发送端串口设置为上方 symlink 或 slave 路径。")
    print("[dmx-sim] tip: 若联调 BehavFactory，请先启动本脚本，再启动 rbk。")

    renderer = DmxTkRenderer(
        led_count=led_count,
        layout=args.layout,
        fps=args.fps,
        show_values=bool(args.show_values),
    )

    receiver = PtyDmxReceiver(
        master_fd,
        led_count,
        channel_map,
        renderer.on_frame,
        print_rgbw=bool(args.print_rgbw),
        print_interval_ms=max(0, int(args.print_interval_ms)),
    )
    receiver.start()

    demo_sender: Optional[DemoDmxSender] = None
    if args.demo_send:
        demo_sender = DemoDmxSender(slave_fd, led_count, channel_map, fps=30.0)
        demo_sender.start()
        print("[dmx-sim] demo sender enabled.")

    def _handle_signal(_sig, _frame):
        renderer.close()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        renderer.run()
    finally:
        receiver.stop()
        if demo_sender is not None:
            demo_sender.stop()
        try:
            os.close(master_fd)
        except Exception:
            pass
        try:
            os.close(slave_fd)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
