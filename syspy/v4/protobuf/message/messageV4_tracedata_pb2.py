import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor.FileDescriptor(
    name="messageV4_tracedata.proto",
    package="rbk4.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x19messageV4_tracedata.proto\x12\rrbk4.protocol"U\n\x13MessageV4_TraceData\x12\x11\n\ttimestamp\x18\x01 \x01(\t\x12\x0e\n\x06plugin\x18\x02 \x01(\t\x12\r\n\x05topic\x18\x03 \x01(\t\x12\x0c\n\x04data\x18\x04 \x01(\x0cb\x06proto3'
    ),
)
_MESSAGEV4_TRACEDATA = _descriptor.Descriptor(
    name="MessageV4_TraceData",
    full_name="rbk4.protocol.MessageV4_TraceData",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="timestamp",
            full_name="rbk4.protocol.MessageV4_TraceData.timestamp",
            index=0,
            number=1,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=_b("").decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="plugin",
            full_name="rbk4.protocol.MessageV4_TraceData.plugin",
            index=1,
            number=2,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=_b("").decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="topic",
            full_name="rbk4.protocol.MessageV4_TraceData.topic",
            index=2,
            number=3,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=_b("").decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="data",
            full_name="rbk4.protocol.MessageV4_TraceData.data",
            index=3,
            number=4,
            type=12,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=_b(""),
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
    serialized_start=44,
    serialized_end=129,
)
DESCRIPTOR.message_types_by_name["MessageV4_TraceData"] = _MESSAGEV4_TRACEDATA
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
MessageV4_TraceData = _reflection.GeneratedProtocolMessageType(
    "MessageV4_TraceData",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_TRACEDATA, __module__="messageV4_tracedata_pb2"),
)
_sym_db.RegisterMessage(MessageV4_TraceData)
