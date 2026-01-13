import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
from . import message_header_pb2 as message__header__pb2

DESCRIPTOR = _descriptor.FileDescriptor(
    name="messageV4_rfid.proto",
    package="rbk4.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x14messageV4_rfid.proto\x12\rrbk4.protocol\x1a\x14message_header.proto"j\n\x12MessageV4_RFIDNode\x12\n\n\x02id\x18\x01 \x01(\r\x12\r\n\x05count\x18\x02 \x01(\r\x12\'\n\x06header\x18\x03 \x01(\x0b2\x17.rbk.protocol.msgHeader\x12\x10\n\x08strength\x18\x04 \x01(\r"G\n\x0eMessageV4_RFID\x125\n\nrfid_nodes\x18\x01 \x03(\x0b2!.rbk4.protocol.MessageV4_RFIDNodeb\x06proto3'
    ),
    dependencies=[message__header__pb2.DESCRIPTOR],
)
_MESSAGEV4_RFIDNODE = _descriptor.Descriptor(
    name="MessageV4_RFIDNode",
    full_name="rbk4.protocol.MessageV4_RFIDNode",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="id",
            full_name="rbk4.protocol.MessageV4_RFIDNode.id",
            index=0,
            number=1,
            type=13,
            cpp_type=3,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="count",
            full_name="rbk4.protocol.MessageV4_RFIDNode.count",
            index=1,
            number=2,
            type=13,
            cpp_type=3,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="header",
            full_name="rbk4.protocol.MessageV4_RFIDNode.header",
            index=2,
            number=3,
            type=11,
            cpp_type=10,
            label=1,
            has_default_value=False,
            default_value=None,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="strength",
            full_name="rbk4.protocol.MessageV4_RFIDNode.strength",
            index=3,
            number=4,
            type=13,
            cpp_type=3,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=61,
    serialized_end=167,
)
_MESSAGEV4_RFID = _descriptor.Descriptor(
    name="MessageV4_RFID",
    full_name="rbk4.protocol.MessageV4_RFID",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="rfid_nodes",
            full_name="rbk4.protocol.MessageV4_RFID.rfid_nodes",
            index=0,
            number=1,
            type=11,
            cpp_type=10,
            label=3,
            has_default_value=False,
            default_value=[],
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        )
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=169,
    serialized_end=240,
)
_MESSAGEV4_RFIDNODE.fields_by_name["header"].message_type = (
    message__header__pb2._MSGHEADER
)
_MESSAGEV4_RFID.fields_by_name["rfid_nodes"].message_type = _MESSAGEV4_RFIDNODE
DESCRIPTOR.message_types_by_name["MessageV4_RFIDNode"] = _MESSAGEV4_RFIDNODE
DESCRIPTOR.message_types_by_name["MessageV4_RFID"] = _MESSAGEV4_RFID
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
MessageV4_RFIDNode = _reflection.GeneratedProtocolMessageType(
    "MessageV4_RFIDNode",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_RFIDNODE, __module__="messageV4_rfid_pb2"),
)
_sym_db.RegisterMessage(MessageV4_RFIDNode)
MessageV4_RFID = _reflection.GeneratedProtocolMessageType(
    "MessageV4_RFID",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_RFID, __module__="messageV4_rfid_pb2"),
)
_sym_db.RegisterMessage(MessageV4_RFID)
