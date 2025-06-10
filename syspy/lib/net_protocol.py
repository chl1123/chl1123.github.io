from .py_rpc import Service, default_plugin, call_service


@default_plugin("NetProtocol")
class NetProtocol(Service):

    @classmethod
    @call_service()
    def release(cls) -> int:
        """释放控制权

        Returns:
            int: 0=ok
        """
        pass

    @classmethod
    @call_service()
    def requireByNickName(cls, nick_name: str) -> int:
        """获取控制权

        Args:
            nick_name (str): 控制权所有者名称
        Returns:
            int: 0=ok, REDIUS_CONN_ERROR，SUBCHANNEL_ERROR, INIT_STATUS_ERROR, LOADMAP_STATUS_ERROR, RELOC_STATUS_ERROR
        """
        pass

    @classmethod
    @call_service()
    def require(cls) -> int:
        """获取控制权

        Returns:
            int: 0=ok, REDIUS_CONN_ERROR，SUBCHANNEL_ERROR, INIT_STATUS_ERROR, LOADMAP_STATUS_ERROR, RELOC_STATUS_ERROR
        """
        pass

    @classmethod
    @call_service()
    def setModbusData(cls, type: str, addr: int, data: list) -> bool:
        """在内部寄存器中写入数据

        Args:
            type (str): modbus 类型，取值为"0x"、"1x"、"3x"、"4x"
            addr (int): 写入时的寄存器起始地址
            data (list): 写入的数据
        Returns:
            bool: 是否写入成功。写入失败时所有数据都不写入。
        """
        pass

    @classmethod
    @call_service()
    def getModbusData(cls, type: str, addr: int, size: int) -> list:
        """在内部寄存器中读取数据

        Args:
            type (str): modbus 类型，取值为"0x"、"1x"、"3x"、"4x"
            addr (int): 读取时的寄存器起始地址
            size (int): 读取的数据长度
        Returns:
            list: 寄存器数据
        """
        pass

    @classmethod
    @call_service()
    def tcpUploadString(cls, jsonStr: str):
        """TCP响应

        Args:
            jsonStr (str): 响应内容
        """
        pass

    @classmethod
    @call_service()
    def robotInfo(cls) -> dict:
        """获取机器人信息"""
        pass
