import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor.FileDescriptor(
    name="message_header.proto",
    package="rbk.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x14message_header.proto\x12\x0crbk.protocol"L\n\tmsgHeader\x12\x0f\n\x07pubNsec\x18\x01 \x01(\x04\x12\x10\n\x08dataNsec\x18\x02 \x01(\x04\x12\x0b\n\x03seq\x18\x03 \x01(\x04\x12\x0f\n\x07frameID\x18\x04 \x01(\tb\x06proto3'
    ),
)
_MSGHEADER = _descriptor.Descriptor(
    name="msgHeader",
    full_name="rbk.protocol.msgHeader",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="pubNsec",
            full_name="rbk.protocol.msgHeader.pubNsec",
            index=0,
            number=1,
            type=4,
            cpp_type=4,
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
            name="dataNsec",
            full_name="rbk.protocol.msgHeader.dataNsec",
            index=1,
            number=2,
            type=4,
            cpp_type=4,
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
            name="seq",
            full_name="rbk.protocol.msgHeader.seq",
            index=2,
            number=3,
            type=4,
            cpp_type=4,
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
            name="frameID",
            full_name="rbk.protocol.msgHeader.frameID",
            index=3,
            number=4,
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
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=38,
    serialized_end=114,
)
DESCRIPTOR.message_types_by_name["msgHeader"] = _MSGHEADER
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
msgHeader = _reflection.GeneratedProtocolMessageType(
    "msgHeader",
    (_message.Message,),
    dict(DESCRIPTOR=_MSGHEADER, __module__="message_header_pb2"),
)
_sym_db.RegisterMessage(msgHeader)
