import sys
from google.protobuf.json_format import MessageToJson
import syspy.lib.pass_through as pt
import syspy.lib.rpc_client as rc
import syspy.lib.rpc_server as rs
import syspy.battery.message_battery_pb2

DEFAULT_PASS_ADDR = "ipc:///tmp/python2dsp_udp.ipc"
DEFAULT_RPC_ADDR = "ipc:///tmp/python2dsp_rpc.ipc"
CODE_BATT_ERRO   = 54001

class batteryBase:
    def __init__(self):
        self.__pass = pt.passThrough()
        self.__pass.connect(DEFAULT_PASS_ADDR)
        self.__rpc_client = rc.rpcClient()
        self.__rpc_client.connect(DEFAULT_RPC_ADDR)
        self.__rpc_server = rs.rpcServer()
        self.__rpc_server.registerFunction(self.setChargeStateOn)
        self.__rpc_server.registerFunction(self.setChargeStateOff)
        self.setCallBack()

    def write(self, msg):
        """
        :param msg:查询报文列表
        """
        if(isinstance(msg, list)):
            self.__pass.send(bytes(msg))
        else:
            print("Write msg format error. please send a list")

    def send(self, msg:list):
        """
        :param msg: 查询报文的列表,为16进制
        :return:无
        """
        self.write(msg)
    
    def setCallBack(self):
        """
        子类需要实现handleData方法
        """
        if not self.handleData:
            print("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__pass.setCallBack(self.handleData)

    def publish(self, battery_info):
        """
        :param battery_info:传入Message_Battery对象
        """
        type_exm = message_battery_pb2.Message_Battery()
        if(isinstance(battery_info, type(type_exm))):
            msg = MessageToJson(battery_info)
            self.__rpc_client.publishBattery(msg)
        else:
            print("Publish battery info type error.")

    def createBatteryMessage(self):
        """
        :param battery_info:创建Message_Battery对象
        """
        return message_battery_pb2.Message_Battery()

    def setTimeout(self):
        """
        设置电池通信超时警告,错误码为54001
        """
        self.__rpc_client.setWarning(CODE_BATT_ERRO, "UART Battery response time out")

    def clearTimeout(self):
        """
        清除电池通信超时警告,错误码为54001
        """
        self.__rpc_client.clearWarning(CODE_BATT_ERRO)
    
    def setChargeStateOn(self):
        """
        设置需要充电标志
        """
        self.need_charge = True

    def setChargeStateOff(self):
        """
        设置不需要充电标志
        """
        self.need_charge = False

    def isNeedCharge(self):
        """
        返回是否需要充电标志
        """
        return self.need_charge

    def registerFunction(self, function, name = None):
        self.__rpc_server.registerFunction(function, name)

    def shoutDown(self):
        self.__rpc_server.shoutDown()
        self.__pass.shoutDown()

if __name__ == "__main__":
    pass