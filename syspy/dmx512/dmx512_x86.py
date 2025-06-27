import logging

from syspy import Led
from syspy.protobuf import Message_Dmx512
from google.protobuf.json_format import MessageToJson

log = logging.getLogger("rbk.script")


class dmx512X86:
    def __init__(self):
        log.info("start x86 dmx512")

    def sendDmx512(self, dmx512_info: Message_Dmx512):
        type_exm = Message_Dmx512()
        if isinstance(dmx512_info, type(type_exm)):
            msg = MessageToJson(dmx512_info)
            Led.sendX86DmxInfo(msg)


if __name__ == "__main__":
    pass
