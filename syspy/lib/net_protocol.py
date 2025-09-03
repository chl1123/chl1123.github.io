from abc import ABC
from syspy.core.rbk_rpc import Service, RBKVersionError
import struct
from typing import List, Any


class NetProtocolInterface(ABC, Service):

    @classmethod
    def release(cls) -> int:
        """释放控制权

        Returns:
            int: 0=ok
        """
        raise RBKVersionError()

    @classmethod
    def requireByNickName(cls, nick_name: str) -> int:
        """获取控制权

        Args:
            nick_name (str): 控制权所有者名称
        Returns:
            int: 0=ok, REDIUS_CONN_ERROR，SUBCHANNEL_ERROR, INIT_STATUS_ERROR, LOADMAP_STATUS_ERROR, RELOC_STATUS_ERROR
        """
        raise RBKVersionError()

    @classmethod
    def require(cls) -> int:
        """获取控制权

        Returns:
            int: 0=ok, REDIUS_CONN_ERROR，SUBCHANNEL_ERROR, INIT_STATUS_ERROR, LOADMAP_STATUS_ERROR, RELOC_STATUS_ERROR
        """
        raise RBKVersionError()

    @classmethod
    def setModbusData(cls, type: str, addr: int, data: list) -> bool:
        """在内部寄存器中写入数据

        Args:
            type (str): modbus 类型，取值为"0x"、"1x"、"3x"、"4x"
            addr (int): 写入时的寄存器起始地址
            data (list): 写入的数据
        Returns:
            bool: 是否写入成功。写入失败时所有数据都不写入。
        """
        raise RBKVersionError()

    @classmethod
    def getModbusData(cls, type: str, addr: int, size: int) -> list:
        """在内部寄存器中读取数据

        Args:
            type (str): modbus 类型，取值为"0x"、"1x"、"3x"、"4x"
            addr (int): 读取时的寄存器起始地址
            size (int): 读取的数据长度
        Returns:
            list: 寄存器数据
        """
        raise RBKVersionError()

    @classmethod
    def tcpUploadString(cls, jsonStr: str):
        """TCP响应

        Args:
            jsonStr (str): 响应内容
        """
        raise RBKVersionError()

    @classmethod
    def robotInfo(cls) -> dict:
        """获取机器人信息"""
        raise RBKVersionError()


from syspy import RBK_VERSION

if RBK_VERSION == 3:
    from syspy.v3.lib.net_protocol import NetProtocolV3

    NetProtocol: NetProtocolInterface = NetProtocolV3()
elif RBK_VERSION == 4:
    from syspy.v4.lib.net_protocol import NetProtocolV4

    NetProtocol: NetProtocolInterface = NetProtocolV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")


def parse_modbus(modbus_data: List[int], data_type: str, start_index: int = 0, length: int = 1) -> Any:
    """
    解析特定类型的数据

    Args:
        modbus_data (List[int]): 从NetProtocol.getModbusData获取的数据列表
        data_type (str): 数据类型 ('uint16', 'int16', 'uint32', 'int32', 'float', 'string')
        start_index (int): 起始寄存器索引
        length (int): 寄存器数量

    Returns:
        Any: 解析后的数据
    """
    if not modbus_data or start_index >= len(modbus_data):
        return None

    if data_type == 'uint16':
        return modbus_data[start_index]

    elif data_type == 'int16':
        return struct.unpack('>h', struct.pack('>H', modbus_data[start_index]))[0]

    elif data_type == 'uint32':
        if start_index + 1 >= len(modbus_data):
            return None
        return (modbus_data[start_index + 1] << 16) | modbus_data[start_index]

    elif data_type == 'int32':
        if start_index + 1 >= len(modbus_data):
            return None
        combined = (modbus_data[start_index + 1] << 16) | modbus_data[start_index]
        return struct.unpack('>i', struct.pack('>I', combined))[0]

    elif data_type == 'float':
        if start_index + 1 >= len(modbus_data):
            return None
        combined = (modbus_data[start_index + 1] << 16) | modbus_data[start_index]
        return struct.unpack('>f', struct.pack('>I', combined))[0]

    elif data_type == 'string':
        if start_index + length > len(modbus_data):
            return None
        # 提取指定范围的寄存器
        registers = modbus_data[start_index: start_index + length]
        return registers_to_string(registers)

    return None


def registers_to_string(registers: List[int]):
    """
    将寄存器列表转换为字符串

    Args:
        registers (List[int]): 寄存器值列表

    Returns:
        str: 转换后的字符串
    """
    result_str = ""

    for i, reg in enumerate(registers):
        # 高字节
        high_byte = (reg >> 8) & 0xFF
        # 低字节
        low_byte = reg & 0xFF

        # 处理高字节
        if high_byte == 0:  # 遇到null终止符
            break
        result_str += chr(high_byte)

        # 处理低字节
        if low_byte == 0:  # 遇到null终止符
            break
        result_str += chr(low_byte)

    # 去除可能的不可见字符并strip
    result_str = result_str.rstrip('\x00')  # 移除末尾的null字符
    return result_str
