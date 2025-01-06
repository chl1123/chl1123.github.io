import sys
from google.protobuf.json_format import MessageToJson, Parse
import syspy.lib.udp_debug as ud
from syspy import Led

# sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
# sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/protobuf')
DEFAULT_RPC_ADDR = "ipc:///tmp/python2dsp_dmx512.ipc"

sys.path.append('/opt/.data/rbk/resources/scripts/')

from syspy.protobuf.messsage import Message_Dmx512, Message_MoveStatus, Message_Battery, Message_NavSpeed

class dmx512X86():
    def __init__(self,rpc_client):
        self.rpc_client = rpc_client
        # self.__debug_out = ud.udpDebug()
        # sys.stdout = self.__debug_out
        print("start dmx512")


    def sendDmx512(self, dmx512_info):
        type_exm = Message_Dmx512()
        if (isinstance(dmx512_info, type(type_exm))):
            Led.sendX86DmxInfo(dmx512_info.model_dump_json())

    def createDmx512Message(self):
        return Message_Dmx512()

    def createMoveStatusMessage(self):
        return Message_MoveStatus()

    def createBatteryMessage(self):
        return Message_Battery()

    def createNavSpeedMessage(self):
        return Message_NavSpeed()

    def __del__(self):
        self.rpc_client.close()

if __name__ == "__main__":
    pass