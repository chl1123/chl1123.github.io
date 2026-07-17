import logging
from google.protobuf.json_format import MessageToJson
from syspy import Trace
from syspy import RBK_VERSION
from syspy.led import _send_sim_dmx512_payload, _send_x86_dmx_info
from syspy.sim import sim_only
if RBK_VERSION == 3:
    from syspy.v3.protobuf.message import message_dmx512_pb2
if RBK_VERSION == 4:
    from syspy.v4.protobuf.message import messageV4_dmx512_pb2 as message_dmx512_pb2

log = logging.getLogger("rbk.script")


def _mock_send_dmx512(_self, dmx512_info):
    type_exm = message_dmx512_pb2.msgDmx512()
    if not isinstance(dmx512_info, type(type_exm)):
        return

    payload = (MessageToJson(dmx512_info, preserving_proto_field_name=False) + "\n").encode("utf-8")
    if _send_sim_dmx512_payload(payload):
        Trace.log("mock send dmx512 to simulator", name="DMX512.sim")
    else:
        Trace.log("mock send dmx512 failed: no simulator port", name="DMX512.sim")


class dmx512PassLib:
    def __init__(self):
        Trace.log("start passThrough dmx512")

    @sim_only(on_sim=_mock_send_dmx512)
    def sendDmx512(self, dmx512_info):
        type_exm = message_dmx512_pb2.msgDmx512()
        if isinstance(dmx512_info, type(type_exm)):
            msg = MessageToJson(dmx512_info)
            _send_x86_dmx_info(msg)


if __name__ == "__main__":
    pass
