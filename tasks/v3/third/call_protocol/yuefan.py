"""越凡 RS485 接收器协议实现。

与 door_protocol.yuefan / elevator_protocol.yuefan 同构:
  - 由 RBK 框架通过 syspy 的 Module / ScriptParam 加载和执行;
  - 通过 syspy.comms.lora_comm 收发:
      自查询走 LoraRpcTransport.transact + LoraMatchSpec (需要等应答帧);
      应答发送器走 LoraRpcTransport.submit_send (单向 ACK, 不等回包);
      被动监听 (发送器呼叫/取消) 由 BehavFactory 的 RX topic 订阅推给脚本。
  - 设备用 protocol.device 指定 (默认 Lora-000)。

本脚本扮演「接收器」。业务流程:
  1. 接收器自查询 (0x0940): 取回接收器自身的地址与信道并打印;
     发送器必须先知道这两个值才能发起呼叫。
  2. 监听发送器呼叫指令 (0x0950, src=0x84 -> dest=0x96);
  3. 收到呼叫后向发送器回复应答 (0x0950, src=0x96 -> dest=0x84);
  4. 应答后触发地图查询与导航: LoRa 呼叫指令仅作为信号, 触发 map.py 查询
     筛选站点, 再交由 navigation.py 执行外部导航任务。

被动监听说明: RPC 传输没有本地串口句柄, 无法自己读总线。收到的帧由
RPC/BehavFactory 侧推给脚本, 经 feed_frame() 进 _frame_queue, _listen()
再按有界窗口消费。串口模式 (LoraSerialTransport) 下仍直接读 transport.serial。
"""

import json
import os
import queue
import struct
import sys
import threading
import time
from typing import Optional

from syspy import Module, ScriptParam, ScriptStatus, Trace
from syspy.script_data import ScriptData
from syspy.comms.lora_comm import (
    LoraFrame,
    LoraFrameCodec,
    LoraFrameStream,
    LoraMatchSpec,
    LoraOperation,
    LoraRpcTransport,
    LoraRxFilter,
    LoraTransportError,
)
from syspy.utils.param_server import ParamType

try:
    from .base import (
        CallRequest,
        ProtocolRejected,
        ProtocolUnavailable,
        ReceiverInfo,
        Rs485Protocol,
    )
except (ImportError, ValueError):
    # RBK 也会直接启动协议文件以生成输入描述符。
    # 两层 dirname: call_protocol -> third。要让 third.call_protocol.xxx 这种
    # 绝对导入成立, 加进 sys.path 的必须是 third 所在的那一层。
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from third.call_protocol.base import (
        CallRequest,
        ProtocolRejected,
        ProtocolUnavailable,
        ReceiverInfo,
        Rs485Protocol,
    )

try:
    from .map_clone import query_call_buttons, resolve_scene
    from .navigation import RbkNavigateClient, is_navigation_busy
    from .network_file import update_lora_endpoint
except (ImportError, ValueError):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from third.call_protocol.map_clone import query_call_buttons, resolve_scene
    from third.call_protocol.navigation import RbkNavigateClient, is_navigation_busy
    from third.call_protocol.network_file import update_lora_endpoint


# 默认 LoRa 设备名 (BehavFactory 侧的资源名), 与 LoraRpcTransport 默认值一致。
DEFAULT_DEVICE = "Lora-000"

# 外部导航服务的地址 (与 navigation.py 中 __main__ 的默认值一致)。
NAVIGATION_HOST = "192.168.192.7"

# 查询导航任务状态时的超时(秒)。刻意短: 只是确认忙不忙, 不能把 serve 循环卡住。
BUSY_CHECK_TIMEOUT = 2.0

# # 兜底 workspace, 站点未携带 workspace 字段时使用 (与 navigation.py 默认值一致)。
# DEFAULT_WORKSPACE = "4F"

# serve 常驻循环里, 每一轮监听呼叫的限时时长。有界轮询代替"一直阻塞到收到呼叫
# 为止", 让每一轮很快返回, main() 才能把任务状态交还为 FINISHED/NONE, 监听阶段
# 不会一直占着 RUNNING 状态。
SERVE_POLL_TIMEOUT = 1.0

# 导航阻塞期间, 每次检查 LoRa 的监听窗口。绕开长读阻塞 (serial 超时 0.05s),
# 用有界窗口让 cancel 检查能被 wait_until_idle 的每拍轮询驱动。
CANCEL_POLL_TIMEOUT = 0.3

# 收到 call_value 等于该值时, 取消当前导航。
CANCEL_CALL_VALUE = 3

script_param = ScriptParam(__file__)


class ConfigParams:
    """越凡 RS485 接收器实例配置, 随设备绑定而不是随单次操作下发。"""

    builder = script_param.builderConfig()
    with builder.GROUPS():
        with builder.GROUP(key="protocol", name="Protocol", desc="Yuefan RS485 receiver configuration"):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                with builder.CHILD(
                        key="device", name="LoRa device",
                        desc="BehavFactory LoRa device name used for RPC transactions"):
                    builder.TYPE(ParamType.STRING)
                    builder.TAG("protocol:instance")
                    builder.DEFAULTVALUE("Lora-000")
                with builder.CHILD(
                        key="timeout", name="Response timeout", desc="LoRa response timeout"):
                    builder.TYPE(ParamType.FLOAT)
                    builder.TAG("protocol:instance")
                    builder.DEFAULTVALUE(2.0, min_value=0.1, max_value=30.0)
                    builder.UNIT("s")
                with builder.CHILD(key="retries", name="Request retries", desc="LoRa request retry count"):
                    builder.TYPE(ParamType.INT)
                    builder.TAG("protocol:instance")
                    builder.DEFAULTVALUE(3, min_value=1, max_value=10)
                with builder.CHILD(
                        key="listenTimeout", name="Listen timeout",
                        desc="Seconds to wait for a sender call (0 = wait forever)"):
                    builder.TYPE(ParamType.FLOAT)
                    builder.TAG("protocol:instance")
                    builder.DEFAULTVALUE(0.0, min_value=0.0, max_value=3600.0)
                    builder.UNIT("s")
    builder.save(merge=True)


class InputParams:
    """RS485 接收器操作输入。实例参数由 ConfigParams 管理。"""

    builder = script_param.builderInput()
    with builder.GROUPS():
        with builder.GROUP(key="operation", name="Operation", desc="RS485 receiver operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            with builder.CHILDREN():
                with builder.CHILD(
                        key="serve", name="Query self then serve calls",
                        desc="Self-query for address/channel, then answer sender calls"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(
                        key="querySelf", name="Query receiver address/channel",
                        desc="Send a 0x0940 self-query and print the response"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(
                        key="monitor", name="Monitor bus frames",
                        desc="Listen passively and print all frames; send nothing"):
                    builder.TYPE(ParamType.ARRAY)
    builder.save()


def _lookup(data, key, default=None):
    if not isinstance(data, dict):
        return default
    if key in data:
        return data[key]
    value = data
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def _protocol_args(config):
    config = dict(config or {})
    site = config.get("protocolSite") or {}
    if not site and isinstance(config.get("jsonObject"), dict):
        site = config
    data = site.get("jsonObject", site) if isinstance(site, dict) else {}
    if not isinstance(data, dict):
        data = {}
    flat = config

    def value(*keys, default=None):
        for key in keys:
            candidate = _lookup(flat, key, None)
            if candidate not in (None, ""):
                return candidate
            candidate = _lookup(data, key, None)
            if candidate not in (None, ""):
                return candidate
        return default

    device = str(value("device", "protocol.device", default=DEFAULT_DEVICE)).strip()
    timeout = float(value("timeout", "protocol.timeout", default=2.0))
    retries = int(value("retries", "protocol.retries", default=3))
    listen_timeout = float(value("listenTimeout", "protocol.listenTimeout", default=0.0))
    if not device:
        raise ValueError("device must not be empty")
    if not 0.1 <= timeout <= 30.0:
        raise ValueError("timeout must be in range 0.1..30")
    if not 1 <= retries <= 10:
        raise ValueError("retries must be in range 1..10")
    if listen_timeout < 0:
        raise ValueError("listenTimeout must not be negative")
    return device, timeout, retries, listen_timeout


# 当前活动协议对象, 供 feed_frame()/drain_frames() 这类模块级被动监听钩子定位。
_active_protocol = None


def _log_frame(direction, raw, device=None):
    """frame_logger 钩子: 打印总线上实际收发的原始帧。

    TX 在发送前回调; RX 在解码后回调 (校验失败的坏帧在 RPC 侧不可见)。
    device 用于标明这条打印来自哪个 LoRa 设备。
    """
    device_tag = "{} ".format(device) if device else ""
    line = "LoRa {}[{}]: {}".format(direction, device_tag.rstrip(), raw.hex(" ").upper())
    print(line, flush=True)
    try:
        Trace.log({"event": "loraFrame", "device": device, "dir": direction, "raw": raw.hex()},
                  name="rs485_protocol.err")
    except Exception:
        pass


def make_frame_logger(device):
    """绑定具体设备的 frame_logger 工厂, 让每条收发帧都带上设备名。"""
    def _logger(direction, raw):
        _log_frame(direction, raw, device=device)
    return _logger


def drain_frames():
    """被动监听钩子: 取走当前协议对象已缓存的被动收帧。

    RPC/BehavFactory 收到总线帧后经 feed_frame() 入队; 这里按数组一次取走。
    返回 list[(LoraFrame, meta)], 无新帧时返回 []。
    """
    protocol = _active_protocol
    if protocol is None:
        return []
    return protocol.drain_frames()


def feed_frame(frame, meta=None):
    """把 BehavFactory 推来的一帧交给当前协议对象。返回帧是否被接受。

    传入 LoraFrame 或原始 bytes (完整帧, 含 add16) 均可。meta 携带 RX topic
    订阅事件的 sequence/device_generation (串口直读路径没有, 传 None 即可)。
    """
    protocol = _active_protocol
    if protocol is None:
        return False
    return protocol.feed_frame(frame, meta=meta)


# 订阅线程状态。serve 是常驻进程, 订阅线程与进程同生共死, 不做精细启停编排。
_rx_stop_event = None
_rx_thread = None
# 当前订阅线程绑定的 protocol 实例。会话重建 (_serve_session.clear() 后
# 重新 run_query_self()) 会产生新的 protocol 对象, 若只看线程存活就直接
# 幂等跳过, 旧线程会继续往已经不再使用的旧 protocol 里喂帧, 新 protocol
# 永远收不到呼叫。必须额外比对绑定对象, 不一致时先停旧线程再起新的。
_rx_bound_protocol = None


def _transport_supports_subscribe(transport):
    """传输是否支持 subscribe_rx (只有 LoraRpcTransport 有; 串口传输自己读总线)。"""
    return callable(getattr(transport, "subscribe_rx", None))


def _make_rx_client_id(device, info):
    """按 LoraRxFilter.md 的推荐格式拼 clientId。

    clientId 只是逻辑订阅标识, 不写入 LoRa 帧、不做安全凭证; 呼叫器侧两个
    端点因为不做端点过滤, 用 0 占位, 机器人侧取自查询结果便于诊断对号。
    """
    robot_address = getattr(info, "address", 0) or 0
    robot_channel = getattr(info, "channel", 0) or 0
    return "call-button:{}:0:0:{}:{}".format(device, robot_address, robot_channel)


def _rx_subscription_loop(protocol, client_id, rx_filter, stop_event):
    """订阅线程主体: 持续消费 RX topic, 把帧喂给 serve 正在用的协议对象。

    只调模块级 feed_frame() (它转发给 _active_protocol), 绝不在本线程里调
    create_protocol() —— 那会覆盖 _active_protocol, 把 serve 的协议对象顶掉。
    """
    transport = protocol.transport
    try:
        for received in transport.subscribe_rx(
            client_id=client_id,
            filter=rx_filter,
            stop_event=stop_event,
        ):
            protocol.feed_frame(received.frame, meta={
                "sequence": received.sequence,
                "device_generation": received.device_generation,
            })
    except Exception as error:
        # 线程静默死掉会退回"收不到帧但没人知道为什么"的状态, 必须留日志。
        print("LoRa RX 订阅线程已退出: {}".format(error), flush=True)
        try:
            Trace.log({"event": "loraRxSubscribeFailed", "error": str(error),
                       "clientId": client_id}, name="rs485_protocol.err")
        except Exception:
            pass


def _start_rx_subscription(protocol, info=None):
    """启动 RX topic 订阅线程 (幂等)。串口传输或已启动时直接返回。

    被动监听在 RPC 路径下没有本地串口可读, 必须靠订阅 BehavFactory 的
    /rbk/behav/lora/rx topic 把帧推进 _frame_queue, _listen() 才有帧可取。
    """
    global _rx_stop_event, _rx_thread, _rx_bound_protocol

    if protocol is None:
        return False
    transport = getattr(protocol, "transport", None)
    if not _transport_supports_subscribe(transport):
        print("传输 {} 不支持 subscribe_rx, 跳过 RX 订阅".format(
            type(transport).__name__), flush=True)
        return False
    if (_rx_thread is not None and _rx_thread.is_alive()
            and _rx_bound_protocol is protocol):
        return True

    # 走到这里说明: 线程从未起过, 或者线程还活着但绑定的是上一轮会话的
    # 旧 protocol (典型场景: wait_for_call 异常 -> _serve_session.clear() ->
    # 下一轮重新自查询建出新 protocol)。先通知旧线程退出, 它会在下一次
    # events.get(timeout=...) 超时后经 subscribe_rx 的 finally 自行
    # unsubscribe_lora_rx, 这里不等待, 避免阻塞当前调用路径。
    if _rx_thread is not None and _rx_thread.is_alive() and _rx_stop_event is not None:
        print("订阅线程绑定的 protocol 已更换, 通知旧订阅线程退出", flush=True)
        _rx_stop_event.set()

    # 不做任何过滤: 所有 RX topic 帧都进队列, 交给协议层的 _is_call() 与
    # _match_site_by_call() 判断。注意 LoraRxFilter 在无字段时仍会丢掉
    # data 区不足 7 字节的帧 (见 lora_comm.py 的 __call__), 这是库的行为,
    # 对呼叫帧无影响 —— 呼叫帧 data 区至少 8 字节。
    rx_filter = LoraRxFilter()
    client_id = _make_rx_client_id(protocol.device, info)
    # 应答路径拼 ack_id 要用同一个 client_id, 存到 protocol 上避免重算。
    protocol._rx_client_id = client_id

    _rx_stop_event = threading.Event()
    _rx_thread = threading.Thread(
        target=_rx_subscription_loop,
        args=(protocol, client_id, rx_filter, _rx_stop_event),
        name="lora_rx_subscribe",
        daemon=True,
    )
    _rx_bound_protocol = protocol
    print("启动 LoRa RX 订阅: clientId={}  filter={}".format(
        client_id, rx_filter.to_topic_dict()), flush=True)
    try:
        Trace.log({"event": "loraRxSubscribe", "clientId": client_id,
                   "filter": rx_filter.to_topic_dict()}, name="rs485_protocol.err")
    except Exception:
        pass
    _rx_thread.start()
    return True


def create_protocol(config, device=None, timeout=None, retries=None):
    """Create a Yuefan RS485 receiver protocol from a device configuration."""
    configured_device, configured_timeout, configured_retries, listen_timeout = _protocol_args(config)
    device = configured_device if device is None else str(device).strip()

    print("LoRa 使用设备: {}".format(device), flush=True)
    try:
        Trace.log({"event": "loraDevice", "device": device}, name="rs485_protocol.err")
    except Exception:
        pass

    timeout = configured_timeout if timeout is None else float(timeout)
    retries = configured_retries if retries is None else int(retries)
    transport = LoraRpcTransport(
        device=device, timeout=timeout, retries=retries, frame_logger=make_frame_logger(device)
    )
    protocol = YuefanReceiverProtocol(transport, listen_timeout=listen_timeout)
    global _active_protocol
    _active_protocol = protocol
    return protocol


class YuefanReceiverProtocol(Rs485Protocol):
    """越凡接收器协议: 自查询地址/信道, 监听并应答发送器呼叫。"""

    PROTOCOL_VERSION = 0x03
    RECEIVER_ADDRESS = 0x96   # 本机 (接收器) 在帧头中的地址
    MODULE_ADDRESS = 0x11     # 自查询时的模块地址
    SENDER_ADDRESS = 0x84     # 发送器 (呼叫器) 在帧头中的地址
    MESSAGE_TYPE = 0x05
    CMD_QUERY = 0x0940        # 接收器自查询 / 返回
    CMD_CALL = 0x0950         # 发送器呼叫 / 接收器应答
    # 自查询数据区: version(1) + 全0 共 10 字节。
    QUERY_DATA = b"\x03" + b"\x00" * 9
    _POWER_NAME = {0x00: "30dBm", 0x01: "27dBm", 0x02: "24dBm", 0x03: "21dBm"}

    def __init__(self, transport, listen_timeout: float = 0.0):
        self.transport = transport
        self.listen_timeout = float(listen_timeout)
        self._stream = LoraFrameStream()
        # 被动收帧缓冲: RPC 传输没有本地串口, 收帧由 BehavFactory 推给
        # feed_frame(), 先入这里, _listen() 再按有界窗口取走。队列元素是
        # (LoraFrame, meta) 二元组, meta 携带 RX topic 订阅事件的
        # sequence/device_generation, 用于应答时拼 ack_id。
        self._frame_queue = queue.Queue()
        # _start_rx_subscription() 启动订阅线程时回填, 应答路径拼 ack_id
        # 要用同一个 client_id。
        self._rx_client_id = ""

    @property
    def device(self):
        return getattr(self.transport, "device", None) or ""

    def _open_and_report(self):
        """打通传输 (RPC 传输无串口可开, 只是确认设备可用)。"""
        opener = getattr(self.transport, "open", None)
        if callable(opener):
            opener()

    def feed_frame(self, frame, meta=None):
        """把 BehavFactory 推来的一帧放进收帧缓冲。返回是否接受。

        传入 LoraFrame 或原始 bytes (完整帧, 含 add16) 均可; 坏帧/无法解码
        的原始字节直接丢弃。meta 为 None 时存 {} (串口直读路径没有游标信息)。
        """
        if meta is None:
            meta = {}
        if frame is None:
            return False
        if isinstance(frame, (bytes, bytearray)):
            for raw in self._stream.feed(bytes(frame)):
                try:
                    frame = LoraFrameCodec.decode(raw)
                except ValueError:
                    continue
                self._frame_queue.put((frame, meta))
                return True
            return False
        if isinstance(frame, LoraFrame):
            self._frame_queue.put((frame, meta))
            return True
        return False

    def drain_frames(self):
        """取走当前缓冲的全部帧。返回 list[(LoraFrame, meta)]。"""
        frames = []
        while True:
            try:
                frames.append(self._frame_queue.get_nowait())
            except queue.Empty:
                return frames

    # ---------------- 1. 接收器自查询 ----------------

    def query_self(self) -> ReceiverInfo:
        """发送 0x0940 自查询, 解析出接收器自身的地址与信道。

        自查询: AA A1 40 09 11 96 05 00 0A 03 00*9 + ADD16
        返回:   AA A1 40 09 96 11 05 00 0B <ver> .. <addr:2> <chan> <power> .. + ADD16
        """
        request = LoraFrame(
            command=self.CMD_QUERY,
            destination=self.MODULE_ADDRESS,
            source=self.RECEIVER_ADDRESS,
            message_type=self.MESSAGE_TYPE,
            message_attr=0,
            data=self.QUERY_DATA,
        )
        self._open_and_report()

        # LoraRpcTransport 只接受 LoraMatchSpec (它需要可序列化后发给
        # BehavFactory); LoraMatchSpec 自身可调用, 串口传输同样兼容。
        matches = LoraMatchSpec(
            command=self.CMD_QUERY,
            destination=self.RECEIVER_ADDRESS,
            source=self.MODULE_ADDRESS,
            operation=LoraOperation.QUERY,
        )

        try:
            response = self.transport.transact(request, matches)
        except LoraTransportError as error:
            raise ProtocolUnavailable(str(error)) from error

        if response.message_attr:
            raise ProtocolRejected(
                "接收器自查询被拒绝 0x{:04X}: error=0x{:02X}".format(
                    self.CMD_QUERY, response.message_attr
                )
            )
        if len(response.data) < 8:
            raise ProtocolUnavailable("接收器自查询应答数据区过短")

        data = response.data
        tx_power = data[7]
        return ReceiverInfo(
            address=struct.unpack("<H", data[4:6])[0],
            channel=data[6],
            tx_power=tx_power,
            tx_power_name=self._POWER_NAME.get(tx_power, "unknown"),
            protocol_version=data[0],
        )

    # ---------------- 2. 监听发送器呼叫 ----------------

    def _listen(self, timeout: Optional[float] = None):
        """被动监听, 持续取帧; 每收到一个完整帧就打印 (含坏帧/非呼叫帧)。

        逐帧 yield (LoraFrame, meta) 二元组; frame 已通过 LoraFrameCodec.decode
        校验, meta 携带 RX topic 订阅事件的 sequence/device_generation (串口
        直读路径没有游标信息, 统一给 {})。
        RPC 传输没有本地串口, 收帧由 BehavFactory 经 feed_frame() 推进缓冲;
        串口传输 (LoraSerialTransport) 则直接读 bus。
        timeout 为 None 时用实例配置; <= 0 表示一直等。
        """
        if timeout is None:
            timeout = self.listen_timeout
        self._open_and_report()
        serial_port = getattr(self.transport, "serial", None)
        device_name = self.device
        # 不清空 self._stream: 有界轮询 (run_serve 的 SERVE_POLL_TIMEOUT) 在
        # 每轮开头清空会让跨轮询边界、尚未收完整的一帧被丢弃, 导致偶发丢呼叫。
        # 该流只由本 _listen 填充与读取, 放在这里每次都会跨轮保留残余字节。
        deadline = None if timeout <= 0 else time.monotonic() + timeout

        while deadline is None or time.monotonic() < deadline:
            if serial_port is None:
                # RPC 路径: 收帧由 BehavFactory 推进 _frame_queue, 这里按有界
                # 窗口取走; 空窗时短暂让出 CPU, 不做忙等。
                frames = self.drain_frames()
                if not frames:
                    time.sleep(0.01)
                    continue
                for frame, meta in frames:
                    yield frame, meta
                continue

            waiting = serial_port.in_waiting
            chunk = serial_port.read(waiting if waiting else 1)
            if not chunk:
                continue
            for raw in self._stream.feed(chunk):
                _log_frame("RX", raw, device=device_name)
                try:
                    yield LoraFrameCodec.decode(raw), {}
                except ValueError:
                    # 坏帧: 已经打印过原始字节, 跳过继续等。
                    continue

    def wait_for_call(self, timeout: Optional[float] = None) -> Optional[CallRequest]:
        """被动监听发送器呼叫帧 (0x0950, src=0x84 -> dest=0x96)。"""
        for frame, meta in self._listen(timeout):
            if self._is_call(frame):
                return self._parse_call(frame, LoraFrameCodec.encode(frame), meta)
            print("RS485 收到非呼叫帧: cmd=0x{:04X} src=0x{:02X} dst=0x{:02X}".format(
                frame.command, frame.source, frame.destination), flush=True)
        return None

    def _is_call(self, frame: LoraFrame) -> bool:
        return (
            frame.command == self.CMD_CALL
            and frame.destination == self.RECEIVER_ADDRESS
            and frame.source == self.SENDER_ADDRESS
            and len(frame.data) >= 8
        )

    @staticmethod
    def _parse_call(frame: LoraFrame, raw: bytes, meta=None) -> CallRequest:
        """呼叫数据区: ver(1) + 发送器地址(2) + 发送器信道(1)
        + 接收器地址(2) + 接收器信道(1) + 呼叫值(1) + 预留。

        meta 携带 RX topic 订阅事件的 sequence/device_generation, 用于应答
        时拼 ack_id; 串口直读路径没有这两个字段, 传 None 即可。
        """
        meta = meta or {}
        data = frame.data
        return CallRequest(
            sender_address=struct.unpack("<H", data[1:3])[0],
            sender_channel=data[3],
            receiver_address=struct.unpack("<H", data[4:6])[0],
            receiver_channel=data[6],
            call_value=data[7],
            raw=raw,
            sequence=meta.get("sequence"),
            device_generation=meta.get("device_generation"),
        )

    def monitor(self, timeout: Optional[float] = None) -> int:
        """纯监听: 打印总线上所有帧 (不发送任何指令)。返回收到的帧数。"""
        count = 0
        deadline = None if timeout is None or timeout <= 0 else time.monotonic() + timeout
        while deadline is None or time.monotonic() < deadline:
            try:
                for frame, _meta in self._listen(timeout):
                    count += 1
                    print("RS485 帧: cmd=0x{:04X} src=0x{:02X} dst=0x{:02X} msgAttr=0x{:02X} data={}".format(
                        frame.command, frame.source, frame.destination,
                        frame.message_attr, frame.data.hex(" ").upper()), flush=True)
            except Exception as exc:
                print("监听出错: {}".format(exc), flush=True)
                break
        return count

    # ---------------- 3. 应答发送器 ----------------

    def reply_to_sender(self, call: CallRequest) -> bytes:
        """向发送器回复应答帧 (0x0950, src=0x96 -> dest=0x84)。

        应答数据区 = 呼叫帧数据区前 4 字节 (回显发送器地址/信道) + 3 字节 0。
        参考: AA A1 50 09 84 96 05 00 07 00 02 00 04 00 00 00 D0 02

        应答是单向的: 发送器不会再回帧。RPC 传输下改走 submit_send() ——
        只提交不轮询, 不需要 matcher, 也不等回包 (按 LoraRxFilter.md 的
        ACK 用法); 之前用 transact()+CONTROL 会先等满整套超时 (约 8.7s)
        才被判定为"预期超时", 这段时间会把 run_serve 的下一轮监听拖住。
        """
        data = (
            bytes([0x00])
            + struct.pack("<H", call.sender_address)
            + bytes([call.sender_channel & 0xFF])
            + b"\x00\x00\x00"
        )
        reply = LoraFrame(
            command=self.CMD_CALL,
            destination=self.SENDER_ADDRESS,
            source=self.RECEIVER_ADDRESS,
            message_type=self.MESSAGE_TYPE,
            message_attr=0,
            data=data,
        )
        raw = LoraFrameCodec.encode(reply)
        self._open_and_report()

        serial_port = getattr(self.transport, "serial", None)
        if serial_port is None:
            _log_frame("TX", raw, device=self.device)
            ack_id = self._make_ack_id(call)
            try:
                self.transport.submit_send(reply, request_id=ack_id)
            except LoraTransportError as error:
                print("应答提交失败 (ackId={}): {}".format(ack_id, error), flush=True)
            return raw

        _log_frame("TX", raw, device=self.device)
        serial_port.write(raw)
        serial_port.flush()
        return raw

    def _make_ack_id(self, call: CallRequest) -> str:
        """按 LoraRxFilter.md 的格式拼 ack_id。

        同一事件 (同一 sequence) 重试提交时 ack_id 必须保持不变, 所以直接
        用订阅事件的 device_generation/sequence 拼, 而不是每次重新生成。
        call 来自串口直读路径, 或者先于本次订阅起来之前收到的帧时,
        sequence/device_generation 会是 None —— 这种情况下退化成占位值
        并打日志, 而不是让 f-string 里悄悄出现字面量 "None"。
        """
        client_id = self._rx_client_id or self.device
        sequence = call.sequence
        device_generation = call.device_generation
        if sequence is None or device_generation is None:
            print("ACK 缺少 sequence/deviceGeneration (clientId={}), "
                  "回退占位 ackId".format(client_id), flush=True)
            sequence = sequence if sequence is not None else "none"
            device_generation = device_generation if device_generation is not None else "none"
        return "ack:{}:{}:{}".format(client_id, device_generation, sequence)


script_param.addAction(
    action_name="Query self then serve calls",
    policy={},
    args={"operation": "serve"},
    config={},
)
script_param.addAction(
    action_name="Query receiver address/channel",
    policy={},
    args={"operation": "querySelf"},
    config={},
)
script_param.addAction(
    action_name="Monitor bus frames",
    policy={},
    args={"operation": "monitor"},
    config={},
)
script_param.saveAction()


def _json_object(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    if not isinstance(value, dict):
        return {}
    nested = value.get("jsonObject")
    return nested if isinstance(nested, dict) else value


def _instance_config(args):
    args = args if isinstance(args, dict) else {}
    candidates = [
        args.get("protocol.instance"),
        args.get("protocolInstance"),
        args.get("protocolSite"),
        args.get("config"),
    ]
    try:
        candidates.append(Module.getTaskConfig())
    except Exception:
        pass
    for candidate in candidates:
        data = _json_object(candidate)
        if data and ("port" in data or "protocol.port" in data):
            return data
    return args


def _publish(key, payload):
    try:
        ScriptData.set(key, payload)
    except Exception:
        pass


def run_query_self(raw_args):
    """步骤 1: 自查询并显示接收器地址与信道。"""
    protocol = create_protocol(_instance_config(raw_args))
    try:
        info = protocol.query_self()
    except (ProtocolUnavailable, ProtocolRejected) as error:
        print("检测结果NG: 未收到接收器响应 ({})".format(error), flush=True)
        try:
            Trace.log({"event": "rs485QuerySelfFailed", "error": str(error)},
                      name="rs485_protocol.err")
        except Exception:
            pass
        _publish("rs485ReceiverInfo", {"pass": False, "error": str(error)})
        raise

    print("接收器地址={} 信道={} 发射功率={}".format(
        info.address, info.channel, info.tx_power_name), flush=True)
    print("检测结果PASS", flush=True)
    _publish("rs485ReceiverInfo", info.as_dict())
    return protocol, info


# serve 常驻循环内的会话缓存: 自查询只做一次, 后续每一轮 run_serve 调用直接复用
# 同一个 protocol/info, 不重复自查询。main() 的 while True 每 ~0.1s 驱动一次
# 任务状态机, 这里用进程内全局态在多次调用间保持 protocol, 而不是每轮重连。
_serve_session = {}


def _get_serve_session(raw_args):
    protocol = _serve_session.get("protocol")
    info = _serve_session.get("info")
    if protocol is not None and info is not None:
        return protocol, info
    # 首次构建。注意: main() 在 setStatus(FINISHED) 后会清空任务参数,
    # 异常重建时单靠本轮 raw_args 取不到 port/config, 因此把构建用到的
    # 参数字典一并缓存下来, 重建时沿用首次那份。
    build_args = _serve_session.get("build_args") or raw_args
    protocol, info = run_query_self(build_args)
    _serve_session["protocol"] = protocol
    _serve_session["info"] = info
    _serve_session["build_args"] = build_args
    print("自查询完成, 进入常驻监听循环 (接收器地址={} 信道={})...".format(
        info.address, info.channel), flush=True)
    # 把当前地址/信道写进 default.ssys, 供外部直接读文件查询 (替代旧的
    # queryReceiverInfo RPC 接口); 只在值变化时真正写盘, 失败只打日志。
    update_lora_endpoint(info.address, info.channel)
    # RPC 路径下没有本地串口可读, 必须靠 RX topic 订阅把帧推进 _frame_queue。
    # 挂在这里是因为此刻 protocol 与 info 都已就绪, 且这段每会话只跑一次,
    # 天然幂等; 放 main() 里则要额外判断, 且每 0.1s 一轮会重复进这个分支。
    _start_rx_subscription(protocol, info)
    return protocol, info


def _iter_cancel_call(protocol):
    """有界监听, 逐次检查是否收到取消呼叫 (call_value == 3)。

    复用 protocol 的 _stream: 不清空, 跨次检查保留半帧, 避免丢呼叫。
    """
    return protocol._listen(timeout=CANCEL_POLL_TIMEOUT)


def _find_cancel_call(protocol):
    """在 cancel 监听窗口内读取, 返回匹配 call_value=3 的 CallRequest, 否则 None。"""
    for frame, meta in _iter_cancel_call(protocol):
        if not protocol._is_call(frame):
            continue
        call = protocol._parse_call(frame, LoraFrameCodec.encode(frame), meta)
        if call.call_value == CANCEL_CALL_VALUE:
            return call
    return None


def _site_lora_ids(site):
    """取出站点绑定的发送器 (信道, 地址), 缺失时返回 (None, None)。

    地图侧 CallButton 站点用 loraAddress/loraChannel 记录该呼叫器绑定的
    发送器; 两个字段都按整数比较, 避免地图里存成字符串导致匹配不上。
    """

    def to_int(key):
        value = _site_field(site, key)
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return to_int("loraChannel"), to_int("loraAddress")


def _site_field(site, key):
    """站点字段读取: 先查顶层, 再查 jsonObject 扩展层。

    站点列表不一定会把 loraAddress/loraChannel 提到顶层, 扩展字段可能
    只存在于 jsonObject 里。
    """
    if not isinstance(site, dict):
        return None
    value = site.get(key)
    if value not in (None, ""):
        return value
    json_object = site.get("jsonObject")
    if isinstance(json_object, str):
        json_object = _json_object(json_object)
    if isinstance(json_object, dict):
        value = json_object.get(key)
        if value not in (None, ""):
            return value
    return None


def _match_site_by_call(site_list, call):
    """按发送器的地址/信道挑出绑定的呼叫器站点, 没有匹配则返回 None。

    呼叫帧里的发送器地址 (= loraAddress) 和信道 (= loraChannel) 唯一标识
    是哪个呼叫器被按下, 站点绑定后才知道该去哪个点; 因此不能按"第一个
    站点"兜底, 未绑定的发送器一律不触发导航。
    """
    address = call.sender_address
    channel = call.sender_channel & 0xFF
    for site in site_list:
        site_channel, site_address = _site_lora_ids(site)
        if site_address == address and site_channel == channel:
            return site
    return None


def trigger_navigation(call, protocol=None):
    """LoRa 呼叫后的处理流程: 查询筛选站点 -> 选定目标 -> 外部导航。

    呼叫指令仅作为信号, 导航站点由 map.py 查询筛选出的结果决定, 但必须
    是绑定了该发送器 (地址 + 信道) 的那个站点。
    导航阻塞期间持续监听 LoRa: 若收到 call_value=3 的取消呼叫, 发 3003
    取消当前导航任务 (无需传参) 并停止等待, 释放导航控制权。
    """
    site_list = query_call_buttons()
    if not site_list:
        print("未筛选出可用的呼叫器站点, 跳过导航", flush=True)
        return

    site = _match_site_by_call(site_list, call)
    if site is None:
        print("未找到绑定发送器地址={} 信道={} 的呼叫器站点, 跳过导航".format(
            call.sender_address, call.sender_channel & 0xFF), flush=True)
        _publish("rs485CallUnbound", {
            "senderAddress": call.sender_address,
            "senderChannel": call.sender_channel & 0xFF,
            "siteCount": len(site_list),
        })
        return

    # target_id = site.get("instanceName") or site.get("pointName")
    target_id = site.get("pointName")
    workspace = site.get("workspace")
    if not workspace:
        # 单楼层场景站点没有 workspace, 说明 tasks 里不需要该字段; 跨楼层则用
        # 场景解析出的 workspace 补上。解析不出来(地图不可用)时同样不下发该
        # 字段, 而不是硬塞一个兜底 workspace —— 猜错楼层比不传更糟。
        scene_workspace = ""
        try:
            mode, scene_workspace, _map_name = resolve_scene()
        except Exception as error:
            print("解析地图场景失败: {}".format(error), flush=True)
            mode = ""
        if mode == "crossFloor":
            workspace = scene_workspace
        elif mode == "singleFloor":
            workspace = ""
        else:
            print("地图场景无法判定, 本次导航不携带 workspace", flush=True)
            workspace = ""
    print("选定导航站点: {} ({})".format(
        target_id, "workspace={}".format(workspace) if workspace else "单楼层不传 workspace"),
        flush=True)

    # 外部导航: 使用 navigation.py 的客户端。navigate 会阻塞直到机器人到位,
    # 结束后交给 __del__ 释放控制权。
    bot = RbkNavigateClient(NAVIGATION_HOST)
    try:
        cancel_check = None
        if protocol is not None:
            def cancel_check():
                cancel_call = _find_cancel_call(protocol)
                if cancel_call is None:
                    return False
                print("收到取消导航呼叫 (发送器地址={} 信道={})".format(
                    cancel_call.sender_address, cancel_call.sender_channel), flush=True)
                # 先确认给发送方, 让它停止重发, 避免残留帧在导航结束后被空闲
                # 监听当成新叫号再次触发导航。
                protocol.reply_to_sender(cancel_call)
                bot.cancel()
                return True

        bot.navigate(target_id, workspace, cancel_check=cancel_check)
        # bot.navigate("LM8", "4F", cancel_check=cancel_check)
    finally:
        bot = None


def run_serve(raw_args):
    """步骤 1(仅一次) + 循环 [限时监听呼叫 -> 应答 -> 触发外部导航]。

    自查询只做一次 (见 _get_serve_session)。每次调用只做一小段有界监听
    (SERVE_POLL_TIMEOUT), 而不是阻塞到收到呼叫为止; 由 main() 的常驻循环
    反复调用本函数驱动这个"循环监听"。没收到呼叫时快速返回, 让 main() 把
    任务状态交还为 FINISHED/NONE, 监听阶段本身不占据任务状态; 只有真正收
    到呼叫、进入应答+导航这段处理时间才算是在执行任务。
    """
    protocol, _info = _get_serve_session(raw_args)

    try:
        call = protocol.wait_for_call(timeout=SERVE_POLL_TIMEOUT)
    except Exception:
        # 轮询出错 (如串口异常): 丢弃缓存的会话, 让下一轮重新自查询/重建连接,
        # 而不是反复用一个可能已经坏掉的 protocol。异常继续向上抛给 main(),
        # 走既有的 FAILED -> NONE -> 重试 流程。
        _serve_session.clear()
        raise
    if call is None:
        # 本轮没有呼叫: 静默返回, 避免每轮轮询都刷屏。
        return

    if call.call_value == CANCEL_CALL_VALUE:
        # call_value=3 是"取消当前导航"的指令, 本身不应触发新的导航任务。
        # 若把取消帧当成普通叫号, 导航停止后发送方重发的取消帧会落到空闲
        # 监听里被 _is_call 命中, 导致"取消后又跑了一次导航"。这里只应答
        # (让发送方停止重发) 并返回, 不触发导航。
        # 取消呼叫不受"忙碌不响应"约束: 它本来就是用来打断在跑的任务的。
        print("收到取消呼叫 (call_value=3, 不触发导航): 发送器地址={} 信道={}".format(
            call.sender_address, call.sender_channel), flush=True)
        protocol.reply_to_sender(call)
        _publish("rs485Call", {"received": True, "cancel": True, **call.as_dict()})
        return

    # 任务运行中不响应新的呼叫: 已在执行任务时按下呼叫器, 不应打断当前任务去
    # 接受新目标。判据是导航服务的 runningStatus (见 is_navigation_busy), 而不是
    # Module.getStatus() —— 后者只反映本脚本自己的生命周期, main() 每轮都把状态
    # 交还 FINISHED/NONE, 拿不到"当下是否真的在跑任务"。
    # 这里连应答都不发: 应答意味着"已受理", 会让发送器停止重发, 但实际并不会
    # 派发导航, 用户看到的就是按了没反应。不响应 + 打印日志更符合预期。
    if is_navigation_busy(NAVIGATION_HOST, timeout=BUSY_CHECK_TIMEOUT):
        print("任务运行中, 忽略本次呼叫 (call_value={}, 发送器地址={} 信道={})".format(
            call.call_value, call.sender_address, call.sender_channel), flush=True)
        _publish("rs485CallBusy", dict(call.as_dict(), received=False, busy=True))
        return

    print("收到呼叫: 发送器地址={} 信道={} 呼叫值={}".format(
        call.sender_address, call.sender_channel, call.call_value), flush=True)
    payload = call.as_dict()
    payload["received"] = True
    _publish("rs485Call", payload)

    protocol.reply_to_sender(call)
    print("已应答发送器", flush=True)

    # 应答后触发地图查询筛选与外部导航 (按发送器地址/信道绑定站点)。
    trigger_navigation(call, protocol)


def run_monitor(raw_args, timeout=None):
    """纯监听: 打印总线上所有帧, 不发任何指令。"""
    protocol = create_protocol(_instance_config(raw_args))
    print("纯监听开始 (不发送任何帧)...", flush=True)
    count = protocol.monitor(timeout)
    print("监听结束, 共收到 {} 帧".format(count), flush=True)
    _publish("rs485Monitor", {"frames": count})


def _resolve_operation(raw_args):
    args = script_param.loadInput(_instance_config(raw_args))
    return str(args.get("operation", "")).strip() or "serve"


def _run_operation(raw_args):
    operation = _resolve_operation(raw_args)
    if operation == "querySelf":
        _protocol, info = run_query_self(raw_args)
        # 一次性自查询同样要同步 default.ssys, 不止 serve 常驻路径。
        update_lora_endpoint(info.address, info.channel)
    elif operation == "serve":
        run_serve(raw_args)
    elif operation == "monitor":
        run_monitor(raw_args)
    else:
        raise ValueError("unsupported RS485 operation: {}".format(operation))


def main():
    """由 RBK 框架按任务参数驱动; 与 door/elevator 的生命周期循环一致。"""
    Module.init()
    # init() 在 TASK 分支下由 __initTaskArgs 直接把状态置为 RUNNING, 但不发
    # scriptReport; 而 update_cmd 看到状态已是 RUNNING 会被 __updateCmd 的 1s
    # 等待挡住同样不报。结果整个启动过程 broker 一个 report 都收不到, 10s 后
    # 报 "no matching scriptReport"。这里在启动点主动上报一次当前状态, 让 broker
    # 立刻拿到匹配的 report。pickJack.py 是每拍 setStatus 上报, 我们在任务启动时
    # 补发这一次即可。getStatus() 若为 NONE 则 __reportData() 因无 taskId 直接
    # 返回, 是安全的空操作。
    Module.setStatus(Module.getStatus())

    # setStatus(FINISHED) 会清空 __task_params (module.py:424), 导致下一轮
    # getTaskArgs() 返回空 dict、_run_operation 不再被调用, serve 只监听第一个
    # 轮询窗口就停摆。因此 serve 常驻循环必须在任务参数被清空后仍能驱动自身,
    # 这里缓存任务参数: 任务不清除前以任务参数为准, 清空后以缓存为准。
    cached_args = None
    while True:
        try:
            status = Module.getStatus()
            if status in (ScriptStatus.NONE, ScriptStatus.RUNNING):
                raw_args = Module.getTaskArgs()
                if raw_args:
                    cached_args = raw_args
                active = cached_args
                if active:
                    operation = _resolve_operation(active)
                    if operation == "serve":
                        # serve 常驻监听: 每轮只做一段有界监听, 结束后把状态交还
                        # FINISHED -> NONE, 监听阶段不占据任务状态。下一轮循环用缓存
                        # 参数继续监听。出错则向外抛出 (run_serve 已清空会话), 由外层
                        # 记一次 FAILED; 终态回到 NONE 后下一轮用缓存参数重新自查询/建
                        # 连, 避免永久停摆。
                        run_serve(active)
                        Module.setStatus(ScriptStatus.FINISHED)
                    else:
                        # 一次性操作 (querySelf/monitor): 只执行一次, 之后清空缓存,
                        # 避免任务被 setStatus 清空参数后仍在 NONE 态反复重跑同一次操作。
                        try:
                            _run_operation(active)
                            Module.setStatus(ScriptStatus.FINISHED)
                        except Exception as error:
                            Trace.log({"event": "rs485OperationFailed", "error": str(error)},
                                      name="rs485_protocol.err")
                            Module.setStatus(ScriptStatus.FAILED)
                        print("RS485 一次性操作完成 ({}), 退出脚本".format(operation), flush=True)
                        time.sleep(0.2)
                        return
            elif status in (ScriptStatus.FINISHED, ScriptStatus.FAILED):
                Module.setStatus(ScriptStatus.NONE)
        except Exception as error:
            Trace.log({"event": "rs485LifecycleFailed", "error": str(error)},
                      name="rs485_protocol.err")
            Module.setStatus(ScriptStatus.FAILED)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
