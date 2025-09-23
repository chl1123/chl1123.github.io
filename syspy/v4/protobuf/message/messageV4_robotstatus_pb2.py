import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
from . import messageV4_smapinfo_pb2 as messageV4__smapinfo__pb2

DESCRIPTOR = _descriptor.FileDescriptor(
    name="messageV4_robotstatus.proto",
    package="rbk4.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x1bmessageV4_robotstatus.proto\x12\rrbk4.protocol\x1a\x18messageV4_smapinfo.proto"\x83\x01\n\x15MessageV4_RobotStatus\x124\n\tsmap_info\x18\x01 \x01(\x0b2!.rbk4.protocol.MessageV4_SmapInfo\x12\x10\n\x08abnormal\x18\x02 \x01(\t\x12\x11\n\tmodel_md5\x18\x03 \x01(\t\x12\x0f\n\x07app_md5\x18\x04 \x01(\tb\x06proto3'
    ),
    dependencies=[messageV4__smapinfo__pb2.DESCRIPTOR],
)
_MESSAGEV4_ROBOTSTATUS = _descriptor.Descriptor(
    name="MessageV4_RobotStatus",
    full_name="rbk4.protocol.MessageV4_RobotStatus",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="smap_info",
            full_name="rbk4.protocol.MessageV4_RobotStatus.smap_info",
            index=0,
            number=1,
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
            name="abnormal",
            full_name="rbk4.protocol.MessageV4_RobotStatus.abnormal",
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
            name="model_md5",
            full_name="rbk4.protocol.MessageV4_RobotStatus.model_md5",
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
            name="app_md5",
            full_name="rbk4.protocol.MessageV4_RobotStatus.app_md5",
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
    serialized_start=73,
    serialized_end=204,
)
_MESSAGEV4_ROBOTSTATUS.fields_by_name["smap_info"].message_type = (
    messageV4__smapinfo__pb2._MESSAGEV4_SMAPINFO
)
DESCRIPTOR.message_types_by_name["MessageV4_RobotStatus"] = _MESSAGEV4_ROBOTSTATUS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
MessageV4_RobotStatus = _reflection.GeneratedProtocolMessageType(
    "MessageV4_RobotStatus",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_ROBOTSTATUS, __module__="messageV4_robotstatus_pb2"),
)
_sym_db.RegisterMessage(MessageV4_RobotStatus)
