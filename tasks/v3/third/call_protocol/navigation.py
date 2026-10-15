import socket
import struct
import json
import time

PACK_FMT_STR = '!BBHLHHHBB'
HEADER_LEN = 16

SYNC_HEAD = 0x5A
PROTO_VERSION = 0x02
COMPRESS_NONE = 0
CTRL_FLAG_DEFAULT = 0x00

NAVIGATE_MSG_TYPE = 3052
STATUS_MSG_TYPE = 1100
CANCEL_MSG_TYPE = 3003
TAKE_CONTROL_MSG_TYPE = 4005
RELEASE_CONTROL_MSG_TYPE = 4006

DEFAULT_WORKSPACE = "4F"


def build_working_tasks(target_id, workspace=DEFAULT_WORKSPACE):
    """构造导航任务负载: 目标站点由 map.py 查询筛选出的站点决定。

    单楼层场景没有 workspace 概念, 此时不传该字段 (而不是传空串或多层楼的
    兜底值), 让导航服务按当前地图解析目标站点。
    """
    task = {"targetId": target_id}
    if workspace:
        task["workspace"] = workspace
    return {"tasks": [task]}


def _msg_type_to_port(msgType):
    if 1000 <= msgType < 2000:
        return 19204
    if 3000 <= msgType < 4000:
        return 19206
    if 4000 <= msgType < 5000:
        return 19207
    raise ValueError(f"unsupported msgType: {msgType}")


def _recv_exact(sock, n, what="payload"):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError(
                f"connection closed while reading {what}: "
                f"got {len(buf)}/{n} bytes; partial={buf[:128]!r}"
            )
        buf += chunk
    return buf


def is_navigation_busy(ip, timeout=2.0):
    """只读查询导航服务当前是否正在执行任务 (不抢控制权)。

    与 RbkNavigateClient.wait_until_idle 用的是同一个判据:
    STATUS_MSG_TYPE 返回体里 navigation.runningStatus == 1 表示任务在跑。

    这里不构造 RbkNavigateClient, 因为它的 __init__ 会下发 4005 抢占控制权,
    呼叫器只是想确认"忙不忙", 抢控制权会干扰正在执行的任务。因此直接发一条
    状态查询。

    Args:
        ip:      导航服务地址。
        timeout: 建连/读写超时(秒)。刻意短于 rbk_call 默认的 60s, 免得导航
                 服务不可达时把 serve 循环卡住。

    Returns:
        True 表示有任务在跑; 查询失败(连不上/超时/返回格式异常)返回 False,
        即"宁可当成空闲", 避免导航服务临时不可达就让呼叫器彻底不响应。
    """
    port = _msg_type_to_port(STATUS_MSG_TYPE)
    header = struct.pack(
        PACK_FMT_STR,
        SYNC_HEAD,
        PROTO_VERSION,
        1,
        0,
        STATUS_MSG_TYPE,
        STATUS_MSG_TYPE,
        0,
        COMPRESS_NONE,
        CTRL_FLAG_DEFAULT,
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(float(timeout))
    try:
        sock.connect((ip, port))
        sock.sendall(header)
        head_data = _recv_exact(sock, HEADER_LEN, what="header")
        rsp = struct.unpack(PACK_FMT_STR, head_data)
        body_data = _recv_exact(sock, rsp[3], what="body") if rsp[3] > 0 else b''
    except Exception as error:
        print("查询导航任务状态失败 ({}), 视为空闲: {}".format(ip, error), flush=True)
        return False
    finally:
        sock.close()

    try:
        body = json.loads(body_data[rsp[6]:].decode("utf-8"))
        return int(body["navigation"]["runningStatus"]) == 1
    except Exception as error:
        print("解析导航任务状态失败, 视为空闲: {}".format(error), flush=True)
        return False


def rbk_call(ip, msgType, msg=None, seq=1, ctrl_flag=CTRL_FLAG_DEFAULT):
    port = _msg_type_to_port(msgType)

    if msg is None:
        body = b''
    elif isinstance(msg, (dict, list)):
        body = json.dumps(msg).encode('ascii')
    else:
        body = bytes(msg)

    route_len = len(body)
    body_total_len = route_len

    header = struct.pack(
        PACK_FMT_STR,
        SYNC_HEAD,
        PROTO_VERSION,
        seq,
        body_total_len,
        msgType,
        msgType,
        route_len,
        COMPRESS_NONE,
        ctrl_flag,
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(60)
    try:
        sock.connect((ip, port))
        sock.sendall(header + body)

        head_data = _recv_exact(sock, HEADER_LEN, what="header")
        rsp = struct.unpack(PACK_FMT_STR, head_data)
        rsp_body_total = rsp[3]
        rsp_route_len = rsp[6]

        body_data = _recv_exact(sock, rsp_body_total, what="body") if rsp_body_total > 0 else b''
    finally:
        sock.close()

    return body_data[rsp_route_len:]


class RbkNavigateClient:
    def __init__(self, ip, ctrl_flag=CTRL_FLAG_DEFAULT):
        self.ip = ip
        self.ctrl_flag = ctrl_flag
        self._seq = 0
        self.call(TAKE_CONTROL_MSG_TYPE, {"nickname": "lora_test_navigation"})

    def __del__(self):
        try:
            self.call(RELEASE_CONTROL_MSG_TYPE)
        except Exception:
            pass

    def call(self, msgType, msg=None):
        self._seq = (self._seq + 1) & 0xFFFF
        return rbk_call(self.ip, msgType, msg, seq=self._seq, ctrl_flag=self.ctrl_flag)

    def cancel(self):
        """取消当前导航任务 (3003, 无需传参)。"""
        return self.call(CANCEL_MSG_TYPE)

    def wait_until_idle(self, settle=1.0, poll_interval=0.01, cancel_check=None):
        time.sleep(settle)
        while json.loads(self.call(STATUS_MSG_TYPE).decode("utf-8"))["navigation"]["runningStatus"] == 1:
            if cancel_check is not None and cancel_check():
                return
            time.sleep(poll_interval)

    def navigate(self, target_id, workspace="", cancel_check=None):
        """下发导航任务: 单楼层传 workspace="" (不发送该字段), 跨楼层传所属 workspace。"""
        result = self.call(NAVIGATE_MSG_TYPE, build_working_tasks(target_id, workspace))
        print(result)
        self.wait_until_idle(cancel_check=cancel_check)
        return result


if __name__ == '__main__':
    bot = RbkNavigateClient("192.168.192.7")
    bot.navigate("LM3")
    # bot.cancel()