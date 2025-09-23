import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor.FileDescriptor(
    name="message_calibstatus.proto",
    package="rbk.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x19message_calibstatus.proto\x12\x0crbk.protocol"£\x01\n\x13Message_CalibStatus\x12=\n\x06status\x18\x07 \x01(\x0e2-.rbk.protocol.Message_CalibStatus.CalibStatus\x12\x0c\n\x04desc\x18\x08 \x01(\t"?\n\x0bCalibStatus\x12\x08\n\x04None\x10\x00\x12\x0b\n\x07Running\x10\x01\x12\r\n\tCompleted\x10\x02\x12\n\n\x06Failed\x10\x03b\x06proto3'
    ),
)
_MESSAGE_CALIBSTATUS_CALIBSTATUS = _descriptor.EnumDescriptor(
    name="CalibStatus",
    full_name="rbk.protocol.Message_CalibStatus.CalibStatus",
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name="None", index=0, number=0, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Running", index=1, number=1, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Completed", index=2, number=2, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Failed", index=3, number=3, serialized_options=None, type=None
        ),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=144,
    serialized_end=207,
)
_sym_db.RegisterEnumDescriptor(_MESSAGE_CALIBSTATUS_CALIBSTATUS)
_MESSAGE_CALIBSTATUS = _descriptor.Descriptor(
    name="Message_CalibStatus",
    full_name="rbk.protocol.Message_CalibStatus",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="status",
            full_name="rbk.protocol.Message_CalibStatus.status",
            index=0,
            number=7,
            type=14,
            cpp_type=8,
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
            name="desc",
            full_name="rbk.protocol.Message_CalibStatus.desc",
            index=1,
            number=8,
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
    enum_types=[_MESSAGE_CALIBSTATUS_CALIBSTATUS],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=44,
    serialized_end=207,
)
_MESSAGE_CALIBSTATUS.fields_by_name["status"].enum_type = (
    _MESSAGE_CALIBSTATUS_CALIBSTATUS
)
_MESSAGE_CALIBSTATUS_CALIBSTATUS.containing_type = _MESSAGE_CALIBSTATUS
DESCRIPTOR.message_types_by_name["Message_CalibStatus"] = _MESSAGE_CALIBSTATUS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
Message_CalibStatus = _reflection.GeneratedProtocolMessageType(
    "Message_CalibStatus",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGE_CALIBSTATUS, __module__="message_calibstatus_pb2"),
)
_sym_db.RegisterMessage(Message_CalibStatus)
