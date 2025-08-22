import logging
from google.protobuf.json_format import MessageToJson
from syspy import Led, RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.protobuf.message import message_dmx512_pb2
if RBK_VERSION == 4:
    from syspy.v4.include.protocol import messageV4_dmx512_pb2 as message_dmx512_pb2

log = logging.getLogger("rbk.script")


class dmx512X86:
    def __init__(self):
        log.info("start x86 dmx512")

    def sendDmx512(self, dmx512_info):
        type_exm = message_dmx512_pb2.Message_Dmx512()
        if isinstance(dmx512_info, type(type_exm)):
            msg = MessageToJson(dmx512_info)
            Led.sendX86DmxInfo(msg)


if __name__ == "__main__":
    pass
