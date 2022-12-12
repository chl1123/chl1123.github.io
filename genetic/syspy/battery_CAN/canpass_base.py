import sys
from google.protobuf.json_format import MessageToJson
import syspy.lib.pass_through as pt
import syspy.lib.rpc_client as rc
import syspy.lib.udp_debug as ud
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/battery_CAN/')
import CanFrame_pb2
import message_battery_pb2

DEFAULT_RPC_ADDR = "ipc:///tmp/CanPass_rpc.ipc"
DEFAULT_PASS_ADDR = "ipc:///tmp/CanPass_udp.ipc"

class canPassBase:
    def __init__(self):
        self.__pass = pt.passThrough()
        self.__pass.connect(DEFAULT_PASS_ADDR,"ECanFrame_pass_py")
        self.__rpc_client = rc.rpcClient()
        self.__rpc_client.connect(DEFAULT_RPC_ADDR)
        self.setCallBack()
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out

    def sendCanframe(self,channel,can_id,dlc,extend,can_string):
        """
        发送can信息至底层
        """
        self.__rpc_client.sendPassThroughCanFrame(channel,can_id,dlc,extend,can_string)

    def attachCanID(self,id_nums,can_id1,can_id2,can_id3,can_id4):
        """
        绑定多个can邮箱
        """
        self.__rpc_client.canPassThroughRxId(id_nums,can_id1,can_id2,can_id3,can_id4)

    def setCallBack(self):
        """
        设置回调，待子类实现handleData方法接收信息
        """
        if not self.handleData:
            print("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__pass.setCallBack(self.handleData)

    def recCanframe(self,msg):
        """
        接收信息并转化为can类型
        """
        rec_canframe = CanFrame_pb2.CanFrame()
        rec_canframe.ParseFromString(msg)
        return rec_canframe

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
        self.__rpc_client.setWarning(54001, "can Battery response time out")
        print("CAN Battery response time out")

    def clearTimeout(self):
        """
        清除电池通信超时警告,错误码为54001
        """
        self.__rpc_client.clearWarning(54001)
        print("clear can Battery response time out")

    def __del__(self):
        self.__pass.shoutDown()
        self.__rpc_client.close()
        self.__debug_out.close()
        print("CanPassBase exit.")

if __name__ == "__main__":
    pass

