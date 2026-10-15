# -*- coding: utf-8 -*-
"""写入 RBK 网络配置文件 default.ssys 的 loraAddress/loraChannel 字段。

external 查询接收器当前的 LoRa 地址/信道不再走 RPC (queryReceiverInfo 已移除),
改为脚本自查询成功后把这两个值写进 default.ssys, 外部直接读文件。

default.ssys 是 RBK 核心网络模块的配置文件 (见 syspy/config.py 的
RBK_NETWORK_FILE), 核心进程也会并发读写它, 所以写入必须:
  1. 用 default.ssys.lock 做跨进程互斥 (fcntl.flock 排他锁);
  2. 持锁期间读最新内容、原地更新两个字段、其余字段原样保留;
  3. 原子替换写回 (同目录临时文件 + fsync + os.replace + fsync 目录),
     不让任何读者看到写了一半的文件。
"""
import fcntl
import json
import os
import stat
import tempfile

NETWORK_FILE = "/opt/.data/rbk/resources/network/default.ssys"
NETWORK_LOCK_FILE = NETWORK_FILE + ".lock"


def _read_network_file():
    """读 default.ssys 当前内容; 不存在或解析失败按空 dict 处理。"""
    try:
        with open(NETWORK_FILE, "r", encoding="utf-8") as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as error:
        print("读取 {} 失败, 按空内容处理: {}".format(NETWORK_FILE, error), flush=True)
        return {}


def _atomic_write_json(data):
    """同目录临时文件 + fsync + os.replace + fsync 目录, 原子替换写回。

    手法与 syspy/utils/param_server.py 的 _atomic_write_text 一致, 这里单独
    实现一份是因为那个函数是 param_server 内部私有实现、只接受已序列化好的
    文本且不处理锁, 没必要跨模块耦合一个带下划线前缀的私有函数。
    """
    directory = os.path.dirname(NETWORK_FILE) or "."
    target_mode = 0o644
    try:
        target_mode = stat.S_IMODE(os.stat(NETWORK_FILE).st_mode)
    except FileNotFoundError:
        pass

    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(
        prefix=".{}.".format(os.path.basename(NETWORK_FILE)), suffix=".tmp",
        dir=directory,
    )
    try:
        os.fchmod(fd, target_mode)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, NETWORK_FILE)
        temporary = None

        directory_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd is not None:
            os.close(fd)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def update_lora_endpoint(address: int, channel: int) -> bool:
    """把 loraAddress/loraChannel 写入 default.ssys, 跨进程互斥 + 原子替换。

    只在值变化时真正写盘, 且"是否变化"基于持锁后读到的最新磁盘内容判断,
    不用内存里缓存的旧值比较 —— 否则会跟核心进程的并发写入产生竞态误判。

    Returns:
        True 表示发生了写入; False 表示值未变化或写入失败 (失败只打日志,
        不向上抛异常 —— 这只是查询信道/地址的辅助能力, 不该拖累 serve 主流程)。
    """
    try:
        with open(NETWORK_LOCK_FILE, "a+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                data = _read_network_file()
                if data.get("loraAddress") == address and data.get("loraChannel") == channel:
                    return False
                data["loraAddress"] = address
                data["loraChannel"] = channel
                _atomic_write_json(data)
                print("已写入 {}: loraAddress={} loraChannel={}".format(
                    NETWORK_FILE, address, channel), flush=True)
                return True
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception as error:
        print("写入 {} 失败: {}".format(NETWORK_FILE, error), flush=True)
        return False
