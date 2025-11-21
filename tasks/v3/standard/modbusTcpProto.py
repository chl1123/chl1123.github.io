import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp


class ModbusTcpProto:
    """
    modbus 协议封装
    """

    def __init__(self, host="192.168.192.5", port=502, timeout=3.0):
        self.host = host
        self.port = port
        self.master = modbus_tcp.TcpMaster(self.host, self.port)
        self.master.set_timeout(timeout)

    def __read_register(self, start_addr, num, slave=1):
        """
        4x
        读取寄存器
        :param start_addr:   读取的寄存器起始地址
        :param num:          读取的寄存器数量
        :param slave:        从机的 ID
        :return:             tuple
        """
        return self.master.execute(slave, cst.READ_HOLDING_REGISTERS, start_addr, num)

    def __write_single_register(self, start_addr, value, slave=1):
        """
        4x
        写寄存器
        :param start_addr:      写入的寄存器地址
        :param value:           写入的值
        :param slave:           从机 ID
        :return:                tuple
        """
        return self.master.execute(slave, cst.WRITE_SINGLE_REGISTER, start_addr, output_value=value)

    def __write_multi_register(self, start_addr, value, slave=1):
        """
        4x
        同时写多个寄存器
        :param value:           写入的值
        :param start_addr:      写入的开始地址
        :param slave:           从机 ID
        :return:                tuple
        """
        return self.master.execute(slave, cst.WRITE_MULTIPLE_REGISTERS, start_addr, output_value=value)

    def __read_coil(self, start_addr, num, slave=1):
        """
        0x
        :param start_addr:      读取的起始地址
        :param num:             读取的数量
        :param slave:           从机 ID
        :return:                tuple
        """
        return self.master.execute(slave, cst.READ_COILS, start_addr, num)

    def __write_single_coil(self, start_addr, value, slave=1):
        """
        0x
        写单个值到线圈
        :param value:               写入线圈寄存器的值 0 或 1
        :param start_addr:          写入线圈寄存器的地址
        :param slave:               从机 ID
        :return:                    tuple
        """
        return self.master.execute(slave, cst.WRITE_SINGLE_COIL, start_addr, output_value=value)

    def __write_multi_coil(self, start_addr, value, slave=1):
        """
        0x
        写多个值到线圈
        :param value:               写入线圈寄存器的值
        :param start_addr:          写入寄存器的地址
        :param slave:               从机 ID
        :return:                    tuple
        """
        return self.master.execute(slave, cst.WRITE_MULTIPLE_COILS, start_addr, output_value=value)

    def __read_input_register(self, start_addr, num, slave=1):
        """
        3x
        读取只读寄存器的值
        :param start_addr:      读取的寄存器地址
        :param num:             读取的地址数量
        :param slave:           从机ID
        :return:                tuple
        """
        return self.master.execute(slave, cst.READ_INPUT_REGISTERS, start_addr, num)

    def __read_inputs(self, start_addr, num, slave=1):
        """
        1x
        只读状态量
        :param start_addr:      读取状态量的地址
        :param num:             读取状态量的地址数量
        :param slave:           从机 ID
        :return:                tuple
        """
        return self.master.execute(slave, cst.READ_DISCRETE_INPUTS, start_addr, num)

    def write_go_target(self, addr, target, slave=1):
        """
        :param addr:            写入的寄存器地址
        :param target:          任务的目标站点
        :param slave:           从机 ID
        :return:                任务站点
        """
        # 到达导航任务点后写入寄存器任务点位置
        ret = self.__write_single_register(addr, target, slave)
        if ret[0] != target:
            print("write target to register error!")
            assert False
        return ret[0]

    def write_operation(self, addr, opt, slave=1):
        """
        :param addr:            写入寄存器的地址
        :param opt:             写入操作类型， 1 为取货， 2 为卸货
        :param slave:           从机 ID
        :return:
        """
        ret = self.__write_single_register(addr, opt, slave)
        if ret[0] != opt:
            print("write operation to register error!")
            assert False
        return ret[0]

    def read_arm_status(self, addr, slave=1):
        """
        获取手臂的复位姿态的状态
        :param addr:            需要读取的地址
        :param slave:           从机 ID
        :return:
        """
        return self.__read_coil(addr, 1, slave)[0]

    def read_target_status(self, addr, slave=1):
        """
        获取设备的完成状态          1 为任务完成， 0 为任务未完成
        :param addr:            需要读取的地址
        :param slave:           从机 ID
        :return:
        """
        return self.__read_coil(addr, 1, slave)[0]

    def write_from_to_register(self, addr_from, addr_to, _from, _to, slave=1):
        """
        把 from 和 to 的编号写入寄存器中
        :param addr_from:           from 写入的地址
        :param addr_to:             to 写入的地址
        :param _from:               from 的编号
        :param _to:                 to 的编号
        :param slave:               从机 ID
        :return:
        """
        # 写入 from
        ret = self.__write_single_register(addr_from, _from, slave)
        if ret[0] != _from:
            print("write _from to register error!")
            assert False
        # 写入 to
        ret = self.__write_single_register(addr_to, _to, slave)
        if ret[0] != _to:
            print("write _to to register error!")
            assert False


if __name__ == '__main__':
    p = ModbusTcpProto("127.0.0.1", 7788)
    # res = p.read_register(0, 10)
    # res = p.write_single_register(1, 1234)
    # res = p.write_single_coil(2, 11)
    # res = p.read_coil(0, 3)

    # coil
    # res = p.read_coil(1, 1, slave=1)
    # if res[0] == 1:
    #     print("status is finished!")
    # else:
    #     print("status is not finished!")
    # print(type(res))
    # print(res)
    # res = p.write_single_coil(9, 1, slave=1)
    # print(res)
    # res = p.write_multi_coil(0, [0, 1, 0, 1], slave=1)
    # print(res)
    # res = p.read_register(0, 10, slave=4)
    # print(res)
    # res = p.write_single_register(9, 10, slave=1)
    # print(res)
    # res = p.write_multi_register(0, [1.2346, 4, 6, 8, 90], slave=1)
    # print(res)
    # res = p.read_input_register(0, 10, slave=1)
    # print(res)
    # res = p.read_input_register(0, 10, slave=1)
    # print(res)
