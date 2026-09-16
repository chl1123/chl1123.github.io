# -*- coding: utf-8 -*-
# @Date : 2026/04/10
# @Author : codex
# @Coding : none
# @Update : 简化为纯类工具，不含状态机、参数系统和main
# @Project: CKY-DG RS485 称重功能封装

import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from syspy import Trace
from syspy.comms.modbus import ModbusRtuProto


class ScaleProtocol(ABC):
    """称重设备统一接口（RS485/CAN 等协议共用）。

    工厂 create_scale(protocol, **kwargs) 按协议名返回具体实现；业务层
    （如 WeightDropMonitor、后续标准车型的称重 action）只依赖本接口，
    不关心底层物理协议，从而兼容瑞博特 CAN、CKY-DG RS485 等模块。
    """

    @abstractmethod
    def open(self):
        ...

    @abstractmethod
    def close(self):
        ...

    @abstractmethod
    def read_weight(self) -> Dict:
        ...

    def read_weight_samples(self, sample_count: int = 10, sample_interval: float = 0.1) -> Dict:
        """协议无关的多次采样；具体协议可按需覆盖。"""
        sample_count = int(sample_count)
        if sample_count <= 0:
            raise ValueError("sample_count must > 0")
        samples: List[Dict] = []
        for index in range(sample_count):
            samples.append(self.read_weight())
            if index < sample_count - 1 and sample_interval > 0:
                time.sleep(float(sample_interval))
        average_value = sum(float(sample["value"]) for sample in samples) / len(samples)
        return {
            "sampleCount": len(samples),
            "averageValue": average_value,
            "last": samples[-1],
            "samples": samples,
        }

    @abstractmethod
    def tare(self):
        ...

    @abstractmethod
    def zero(self):
        ...


class CkyDgScale(ScaleProtocol):
    """
    CKY-DG RS485(Modbus-RTU) 称重设备工具类

    功能：
    - 读取重量（单次/多次采样）
    - 去皮/清除去皮/清零
    - 读写寄存器（调试用途）
    """

    # 寄存器地址（文档地址减 40001）
    REG_DISPLAY_VALUE = 0x00  # 40001
    REG_DECIMAL_POINT = 0x01  # 40002
    REG_UNIT = 0x02  # 40003
    REG_TARE = 0x11  # 40018
    REG_ZERO = 0x16  # 40023

    UNIT_MAP = {
        1: "MPa",
        2: "Kg",
        3: "T",
        4: "g",
        5: "N",
        6: "KN",
    }

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        timeout: float = 1.0,
        slave_id: int = 1,
    ):
        self.slave_id = int(slave_id)
        self.modbus = ModbusRtuProto(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout,
            verbose=False,
            auto_open=False,
        )
        self._opened = False
        # 简化调用方：实例化后默认直接可用
        self.open()

    def __del__(self):
        self.close()

    def open(self):
        """打开串口连接"""
        if not self._opened:
            self.modbus.open()
            self._opened = True

    def close(self):
        """关闭串口连接"""
        try:
            if self._opened:
                self.modbus.close()
        except Exception:
            pass
        finally:
            self._opened = False

    def set_slave_id(self, slave_id: int):
        """设置默认从站 ID"""
        self.slave_id = int(slave_id)

    def _slave(self, slave_id: Optional[int] = None) -> int:
        """获取实际使用的从站 ID"""
        return self.slave_id if slave_id is None else int(slave_id)

    # ------------------------ 调试通用接口（私有） ------------------------
    def _read_registers(self, address: int, count: int = 1, slave_id: Optional[int] = None) -> Tuple[int, ...]:
        """读取保持寄存器"""
        return self.modbus.read_holding_registers(int(address), int(count), self._slave(slave_id))

    def _write_register(self, address: int, value: int, slave_id: Optional[int] = None) -> Tuple[int, int]:
        """写单个保持寄存器"""
        return self.modbus.write_single_register(int(address), int(value), self._slave(slave_id))

    def _read_all(self, slave_id: Optional[int] = None) -> Tuple[int, ...]:
        """读取 0x00~0x17 共 24 个保持寄存器"""
        return self._read_registers(0x00, 0x18, slave_id)

    # ------------------------ 称重业务接口 ------------------------
    def read_weight_once(self, slave_id: Optional[int] = None) -> Dict:
        """
        读取一次重量信息：
        - 0x00：原始值（16位有符号）
        - 0x01：小数点位
        - 0x02：单位编码
        """
        regs = self._read_registers(self.REG_DISPLAY_VALUE, 3, slave_id)
        raw = ModbusRtuProto.u16_to_i16(regs[0])
        decimal_point = int(regs[1])
        unit_code = int(regs[2])
        value = raw / (10 ** decimal_point) if decimal_point >= 0 else float(raw)
        return {
            "raw": raw,
            "decimalPoint": decimal_point,
            "value": value,
            "unitCode": unit_code,
            "unit": self.UNIT_MAP.get(unit_code, f"unknown({unit_code})"),
        }

    def read_weight_samples(
        self,
        sample_count: int = 10,
        sample_interval: float = 0.1,
        slave_id: Optional[int] = None,
    ) -> Dict:
        """多次采样读取重量，并返回均值和样本"""
        sample_count = int(sample_count)
        if sample_count <= 0:
            raise ValueError("sample_count must > 0")

        samples: List[Dict] = []
        for i in range(sample_count):
            samples.append(self.read_weight_once(slave_id))
            if i < sample_count - 1 and sample_interval > 0:
                time.sleep(float(sample_interval))

        average_value = sum(s["value"] for s in samples) / len(samples)
        return {
            "sampleCount": len(samples),
            "averageValue": average_value,
            "last": samples[-1],
            "samples": samples,
        }

    def read_weight(self, slave_id: Optional[int] = None) -> Dict:
        """ScaleProtocol 统一接口：读取一次重量（归一化为含 value/unit 的字典）"""
        return self.read_weight_once(slave_id)

    def tare(self, slave_id: Optional[int] = None) -> Tuple[int, int]:
        """去皮：写 0x11 = 1"""
        return self._write_register(self.REG_TARE, 1, slave_id)

    def clear_tare(self, slave_id: Optional[int] = None) -> Tuple[int, int]:
        """清除去皮：写 0x11 = 2"""
        return self._write_register(self.REG_TARE, 2, slave_id)

    def zero(self, slave_id: Optional[int] = None) -> Tuple[int, int]:
        """清零：写 0x16 = 0x0011"""
        return self._write_register(self.REG_ZERO, 0x0011, slave_id)


# ============================================================================
# 瑞搏特/朗科 AGV 称重仪表 CAN 协议实现
# 协议见《AGV应用CAN通讯规约》：CAN2.0A，11bit ID，小端；波特率默认 125k。
#   0x180|node  仪表循环发重量(200ms)
#   0x200|node  主机发命令
#   0x280|node  仪表应答
# 传输层：默认走 syspy/comms/can_comm.py（socketcan）；若 /etc/srcname 含
#        SRC2000 则回退到 syspy/lib/can_frame.py + pass_through（脚本透传）。
# ============================================================================

def _read_srcname() -> str:
    try:
        with open("/etc/srcname") as f:
            return f.readline().strip()
    except Exception:
        return ""


def _can_data_hex(data) -> str:
    return " ".join(f"{byte:02X}" for byte in bytes(data))


class _CanFrame:
    """统一帧结构：id(int) + data(bytes)"""

    __slots__ = ("id", "data")

    def __init__(self, id: int, data: bytes):
        self.id = id
        self.data = data


class _CanTransport(ABC):
    """CAN 传输层统一接口（屏蔽 socketcan / 透传 差异）"""

    def __init__(self):
        self._callback = None

    def set_callback(self, fn):
        self._callback = fn

    def _dispatch(self, frame: _CanFrame):
        if self._callback:
            self._callback(frame)

    @abstractmethod
    def open(self):
        ...

    @abstractmethod
    def attach(self, *ids):
        ...

    @abstractmethod
    def send(self, can_id: int, data):
        ...

    @abstractmethod
    def close(self):
        ...


def _make_socket_can_comm_class():
    """延迟构建修复版 CanComm 子类（避免非 CAN 用户也加载 python-can）。

    CanComm 原实现在 __init__ 里、self.bus 仍为 None 时调用 attach_can_ids，
    而后者会 self.bus.set_filters -> AttributeError。这里改为由 open() 驱动。
    """

    from syspy.comms.can_comm import CanComm

    class _SocketCanComm(CanComm):
        def __init__(self, channel, bitrate):
            self.channel = channel
            self.bitrate = bitrate
            self.bus = None
            self.can_ids = []

        def close(self):
            if self.bus is not None:
                try:
                    self.bus.shutdown()
                except Exception:
                    pass
                self.bus = None

    return _SocketCanComm


class _SocketCanTransport(_CanTransport):
    """socketcan 后端（syspy/comms/can_comm.py）"""

    def __init__(self, channel, bitrate):
        super().__init__()
        self._comm = _make_socket_can_comm_class()(channel, bitrate)
        self._stop = threading.Event()
        self._thread = None

    def open(self):
        if self._comm.open() is False:
            raise RuntimeError("open CAN bus %s failed" % self._comm.channel)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            msg = self._comm.recv()
            if msg is None:
                continue
            self._dispatch(_CanFrame(msg.arbitration_id, bytes(msg.data)))

    def attach(self, *ids):
        self._comm.attach_can_ids(*ids)

    def send(self, can_id: int, data):
        if isinstance(data, (bytes, bytearray)):
            data = list(data)
        import can
        self._comm.send(can.Message(arbitration_id=can_id, data=data, is_extended_id=False, dlc=len(data)))

    def close(self):
        self._stop.set()
        self._comm.close()


class _PassThroughTransport(_CanTransport):
    """SRC2000 脚本透传后端（syspy/lib/can_frame.py + pass_through.py）"""

    DEFAULT_PASS_ADDR = "ipc:///tmp/CanPass_udp.ipc"

    def __init__(self, channel):
        super().__init__()
        channel_text = str(channel).strip().lower()
        if channel_text.startswith("can"):
            # SocketCAN names are zero-based, while SRC2000 pass-through
            # channels use the physical port numbers 1, 2, ...
            self.channel = int(channel_text[3:]) + 1
        else:
            self.channel = int(channel_text)
        Trace.log(
            f"SRC2000 pass-through channel source={channel!r}, physical={self.channel}",
            name="scale.can",
        )
        try:
            import syspy.lib.pass_through as pt
            from syspy.lib.can_frame import Can
            from syspy.v3.protobuf.message import CanFrame_pb2
        except Exception as e:
            raise RuntimeError("pass-through CAN 依赖不可用: %s" % e)
        self._pt = pt
        self._Can = Can
        self._CanFrame_pb2 = CanFrame_pb2
        self._pass = None

    def _on_pass(self, raw):
        try:
            cf = self._CanFrame_pb2.CanFrame()
            cf.ParseFromString(raw)
            self._dispatch(_CanFrame(cf.id, bytes(cf.data)))
        except Exception as exc:
            Trace.log(f"pass-through frame parse failed: {exc}", name="scale.can.err")

    def open(self):
        self._pass = self._pt.passThrough("can")
        self._pass.canConnect(self.DEFAULT_PASS_ADDR, "RuibotScale_pass")
        Trace.log(
            f"open SRC2000 pass-through channel={self.channel}, address={self.DEFAULT_PASS_ADDR}",
            name="scale.can",
        )
        if self._callback:
            self._pass.setCallBack(self._on_pass)

    def attach(self, *ids):
        valid = [int(i) for i in ids if i]
        id_nums = len(valid)
        padded = (valid[:5] + [0] * 5)[:5]
        self._Can.canPassThroughRxId(self.channel, id_nums, *padded)
        Trace.log(
            f"subscribe channel={self.channel}, ids={[f'0x{can_id:X}' for can_id in valid]}",
            name="scale.can",
        )

    def send(self, can_id: int, data):
        if isinstance(data, (bytes, bytearray)):
            data = list(data)
        s = " ".join("%02x" % b for b in data)
        Trace.log(
            f"tx channel={self.channel}, id=0x{can_id:X}, dlc={len(data)}, data={_can_data_hex(data)}",
            name="scale.can",
        )
        self._Can.sendPassThroughCanFrame(self.channel, can_id, len(data), False, s)

    def close(self):
        if self._pass:
            try:
                self._pass.close()
            except Exception:
                pass
            self._pass = None


class _PollingTransport(_CanTransport):
    """SRC2000 CAN 轮询后端（不走 ipc:///tmp/CanPass_udp.ipc 回调）。

    `ipc:///tmp/CanPass_udp.ipc` 目前是电池脚本独占的透传通道，称重脚本再连
    上去也收不到帧（只能有一个消费者）。参照 `tasks/v3/standard/module/
    cleanRobotManage.py` 的做法：用 `Can.getData()` 周期轮询 DSP 的最新 CAN
    报文、在脚本侧按 id 过滤，接收不再依赖 IPC 回调。

    注意：`Can.getData()` 是“最新一帧”快照而非队列，所以接收线程需要以较高
    频率持续轮询并把感兴趣的 id 缓存下来，避免漏帧。
    """

    DEFAULT_POLL_INTERVAL = 0.005  # 5ms，贴近透传实时性

    def __init__(self, channel, poll_interval: float = DEFAULT_POLL_INTERVAL):
        super().__init__()
        channel_text = str(channel).strip().lower()
        if channel_text.startswith("can"):
            # SocketCAN 名字是 0 基，DSP 透传通道是 1 基物理口
            self.channel = int(channel_text[3:]) + 1
        else:
            self.channel = int(channel_text)
        self.poll_interval = max(float(poll_interval), 0.001)
        Trace.log(
            f"SRC2000 poll channel source={channel!r}, physical={self.channel}",
            name="scale.can",
        )
        try:
            from syspy.lib.can_frame import Can
        except Exception as e:
            raise RuntimeError("poll CAN 依赖不可用: %s" % e)
        self._Can = Can
        self._stop = threading.Event()
        self._thread = None
        self._ids = set()
        self._frames = []
        self._latest_by_id = {}
        self._poll_errors = 0
        self._last_delivered = None

    # -------------------- 生命周期 --------------------
    def open(self):
        Trace.log(
            f"open SRC2000 poll channel={self.channel}, "
            f"api=Can.getData, interval={self.poll_interval}s",
            name="scale.can",
        )

    def attach(self, *ids):
        valid = [int(i) for i in ids if i]
        self._ids = set(valid)
        # 订阅邮箱：poll 模式其实靠本地过滤，绑定失败也不影响。
        padded = (valid[:5] + [0] * 5)[:5]
        try:
            self._Can.canPassThroughRxId(self.channel, len(valid), *padded)
        except Exception as exc:
            Trace.log(f"canPassThroughRxId failed (poll 模式忽略): {exc}", name="scale.can.err")
        Trace.log(
            f"poll subscribe channel={self.channel}, ids={[f'0x{can_id:X}' for can_id in valid]}",
            name="scale.can",
        )
        self._start_polling()

    def _start_polling(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="scaleCanPoll", daemon=True)
        self._thread.start()

    def _run(self):
        import base64

        while not self._stop.is_set():
            try:
                data = self._Can.getData()
                if isinstance(data, dict) and data:
                    self._handle_snapshot(data, base64)
                self._poll_errors = 0
            except Exception as exc:
                self._poll_errors += 1
                if self._poll_errors == 1 or self._poll_errors % 200 == 0:
                    Trace.log(f"poll Can.getData failed: {exc}", name="scale.can.err")
            time.sleep(self.poll_interval)

    def _handle_snapshot(self, data, base64_mod):
        try:
            can_id = int(data.get("id", 0))
            channel = int(data.get("channel", 0) or 0)
            raw = data.get("data", "") or b""
            if isinstance(raw, (bytes, bytearray)):
                payload = bytes(raw)
            else:
                payload = base64_mod.b64decode(raw)
        except Exception as exc:
            Trace.log(f"poll frame parse failed: {exc}", name="scale.can.err")
            return
        if channel and channel != self.channel:
            return
        if self._ids and can_id not in self._ids:
            return
        # getData 是快照，同一帧会重复返回；按 (id, data) 去重避免刷屏。
        marker = (can_id, payload)
        if marker == self._last_delivered:
            return
        self._last_delivered = marker
        self._latest_by_id[can_id] = payload
        self._frames.append((can_id, payload))
        self._dispatch(_CanFrame(can_id, payload))

    def frames(self):
        return list(self._frames)

    def latest(self):
        return dict(self._latest_by_id)

    def send(self, can_id: int, data):
        if isinstance(data, (bytes, bytearray)):
            data = list(data)
        s = " ".join("%02x" % b for b in data)
        Trace.log(
            f"tx channel={self.channel}, id=0x{can_id:X}, dlc={len(data)}, data={_can_data_hex(data)}",
            name="scale.can",
        )
        # 与 cleanRobotManage 一致：poll 模式用 sendCanFrame。
        self._Can.sendCanFrame(self.channel, can_id, len(data), False, s)

    def close(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None


class RuibotScale(ScaleProtocol):
    """瑞搏特/朗科 AGV 称重仪表 CAN 设备类。

    使用方式：
        scale = create_scale("ruibot", channel="can0", bitrate=125000, node_id=0x0A)
        scale.open()
        w = scale.read_weight()          # {"value": kg, "unit": "Kg", "total":.., ...}
        scale.zero()                     # 执行系统零点(0x31)
        scale.calibrate_load(500.0)      # 整车加载标定(0x23)
        scale.close()

    说明：
    - 重量由仪表以 200ms 周期循环上报（0x180|node），read_weight 返回最近一帧。
    - 标定/配置走命令帧(0x200|node)+应答(0x280|node)；0x11~0x14 需重新上电生效。
    - 协议无“去皮(tare)”指令，tare() 抛出 NotImplementedError。
    """

    NODE_ID_DEFAULT = 0x0A
    CMD_READ = 0x01
    CMD_WRITE = 0x02
    ACK_OK = 0x06
    ACK_ERR = 0x15

    C_BAUDRATE = 0x11
    C_NODE_ID = 0x12
    C_CYCLIC = 0x13
    C_ZERO_CALIB = 0x21
    C_LOAD_CALIB = 0x23
    C_SYS_ZERO = 0x31

    def __init__(self, channel="can0", bitrate=125000, node_id=NODE_ID_DEFAULT, transport=None):
        self.channel = channel
        self.bitrate = int(bitrate)
        self.node_id = int(node_id)
        self.cyclic_id = 0x180 | self.node_id
        self.cmd_id = 0x200 | self.node_id
        self.ack_id = 0x280 | self.node_id

        self._transport = self._make_transport(transport)
        self._lock = threading.Lock()
        self._latest_weight = None
        self._ack_event = threading.Event()
        self._ack_buf = {}
        self._closed = True

    def _make_transport(self, transport):
        if transport is not None and not isinstance(transport, str):
            required = ("set_callback", "open", "attach", "send", "close")
            if all(hasattr(transport, name) for name in required):
                return transport
            raise TypeError("invalid CAN transport object")
        if transport in ("socketcan", "can_comm"):
            return _SocketCanTransport(self.channel, self.bitrate)
        if transport in ("poll", "polling"):
            return _PollingTransport(self.channel)
        if transport in ("pass", "passthrough", "can_frame"):
            return _PassThroughTransport(self.channel)
        # 自动判定：SRC2000 默认走 Can.getData() 轮询（CanPass_udp.ipc 被电池脚本独占，
        # 透传回调在称重脚本里收不到帧），其余走 socketcan。
        src = _read_srcname()
        if src and "SRC2000" in src:
            return _PollingTransport(self.channel)
        return _SocketCanTransport(self.channel, self.bitrate)

    # -------------------- ScaleProtocol --------------------
    def open(self):
        Trace.log(
            f"open scale channel={self.channel}, bitrate={self.bitrate}, node=0x{self.node_id:X}, "
            f"cyclic=0x{self.cyclic_id:X}, ack=0x{self.ack_id:X}, transport={type(self._transport).__name__}",
            name="scale.can",
        )
        self._transport.set_callback(self._on_frame)
        self._transport.open()
        self._transport.attach(self.cyclic_id, self.ack_id)
        self._closed = False

    def close(self):
        if not self._closed:
            try:
                self._transport.close()
            finally:
                self._closed = True

    def read_weight(self, timeout: float = 1.0) -> Dict:
        Trace.log(
            f"read weight waits for cyclic frame id=0x{self.cyclic_id:X}; no CAN frame is transmitted",
            name="scale.can",
        )
        deadline = time.time() + timeout
        while self._latest_weight is None and time.time() < deadline:
            time.sleep(0.01)
        with self._lock:
            if self._latest_weight is None:
                Trace.log(f"read weight timeout id=0x{self.cyclic_id:X}", name="scale.can.err")
                raise RuntimeError("未收到循环重量帧(0x%X)" % self.cyclic_id)
            measurement = dict(self._latest_weight)
            Trace.log(f"read weight result={measurement}", name="scale.can")
            return measurement

    def tare(self):
        raise NotImplementedError("瑞搏特 CAN 协议无去皮(tare)指令；可用 zero()/calibrate_*()")

    def zero(self):
        """执行系统零点（0x31，平时修正空车零点）"""
        self._send_command(self.CMD_WRITE, self.C_SYS_ZERO, b"")
        return True

    # -------------------- 标定/配置 --------------------
    def calibrate_zero(self):
        """整车空载零点标定（0x21），返回零点细分值(float)"""
        ack = self._send_command(self.CMD_WRITE, self.C_ZERO_CALIB, b"")
        return self._unpack_float(ack, 2)

    def calibrate_load(self, kg: float):
        """整车加载标定（0x23），写入加载点重量(kg)，返回增益系数(float)"""
        ack = self._send_command(self.CMD_WRITE, self.C_LOAD_CALIB, self._pack_float(kg))
        return self._unpack_float(ack, 2)

    def set_cyclic(self, enable: bool):
        """启动/停止循环发送（0x13）。注意：0x11~0x14 需重新上电才生效。"""
        self._send_command(self.CMD_WRITE, self.C_CYCLIC, bytes([1 if enable else 0]))

    def read_baudrate(self):
        ack = self._send_command(self.CMD_READ, self.C_BAUDRATE, b"")
        return ack[2] if ack and len(ack) > 2 else None

    # -------------------- 内部 --------------------
    def _send_command(self, op, cmd, payload=b"", timeout: float = 2.0):
        data = bytes([op, cmd]) + bytes(payload)
        data = data + b"\x00" * (8 - len(data))
        self._ack_event.clear()
        self._ack_buf.pop(cmd, None)
        Trace.log(
            f"send scale command op=0x{op:X}, cmd=0x{cmd:X}, id=0x{self.cmd_id:X}, data={_can_data_hex(data)}",
            name="scale.can",
        )
        self._transport.send(self.cmd_id, data)
        if not self._ack_event.wait(timeout):
            Trace.log(
                f"command timeout cmd=0x{cmd:X}, expected_ack=0x{self.ack_id:X}",
                name="scale.can.err",
            )
            raise TimeoutError("瑞搏特称重仪表未应答命令 0x%X" % cmd)
        ack = self._ack_buf.get(cmd)
        if ack and len(ack) >= 1 and ack[0] == self.ACK_ERR:
            raise RuntimeError("瑞搏特称重仪表否定应答命令 0x%X" % cmd)
        return ack

    def _on_frame(self, frame: _CanFrame):
        frame_type = "cyclic" if frame.id == self.cyclic_id else ("ack" if frame.id == self.ack_id else "other")
        Trace.log(
            f"rx type={frame_type}, id=0x{frame.id:X}, dlc={len(frame.data)}, data={_can_data_hex(frame.data)}",
            name="scale.can",
        )
        if frame.id == self.cyclic_id:
            with self._lock:
                self._latest_weight = self._parse_cyclic(frame.data)
        elif frame.id == self.ack_id:
            data = frame.data
            if len(data) >= 2 and data[0] in (self.ACK_OK, self.ACK_ERR):
                self._ack_buf[data[1]] = data
                self._ack_event.set()

    @staticmethod
    def _parse_cyclic(data):
        data = bytes(data)
        if len(data) < 8:
            data = data + b"\x00" * (8 - len(data))
        total = int.from_bytes(data[0:2], "little", signed=True)
        s1 = int.from_bytes(data[2:4], "little", signed=True)
        s2 = int.from_bytes(data[4:6], "little", signed=True)
        status = int.from_bytes(data[6:8], "little", signed=False)
        return {
            "value": float(total),
            "unit": "Kg",
            "total": total,
            "sensor1": s1,
            "sensor2": s2,
            "status": status,
            "overload": bool(status & 0x40),
            "eepromFail": bool(status & 0x80),
            "eccState": status & 0x03,
        }

    @staticmethod
    def _pack_float(v: float) -> bytes:
        import struct
        return struct.pack("<f", float(v))

    @staticmethod
    def _unpack_float(ack, offset) -> Optional[float]:
        if ack and len(ack) >= offset + 4:
            import struct
            return struct.unpack("<f", bytes(ack[offset:offset + 4]))[0]
        return None


def create_scale(protocol: str, **kwargs):
    """按协议名创建称重设备实例。

    protocol:
        "ckyDg" / "cky" / "modbus" / "rs485" -> CkyDgScale (RS485/Modbus)
        "ruibot" / "ruibo" / "can"           -> RuibotScale (CAN)
    kwargs 透传给具体实现：
        CkyDgScale: port/baudrate/slave_id ...
        RuibotScale: channel/bitrate/node_id/transport
    """
    p = (protocol or "").lower()
    if p in ("ckydg", "cky", "modbus", "rs485"):
        return CkyDgScale(**kwargs)
    if p in ("ruibot", "ruibo", "can"):
        return RuibotScale(**kwargs)
    raise ValueError("未知称重协议: %r (支持 ckyDg / ruibot)" % protocol)


def weight_to_kg(value, unit) -> float:
    """把协议返回的常用重量单位归一为 kg。"""
    if value is None or unit is None:
        raise ValueError("weight value/unit is missing")
    numeric_value = float(value)
    unit_text = str(unit).strip().lower()
    if unit_text == "kg":
        return numeric_value
    if unit_text == "g":
        return numeric_value / 1000.0
    if unit_text == "t":
        return numeric_value * 1000.0
    raise ValueError("unsupported weight unit: %r" % unit)
