import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor.FileDescriptor(
    name="messageV4_smapinfo.proto",
    package="rbk4.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x18messageV4_smapinfo.proto\x12\rrbk4.protocol"5\n\x0fCurrentMapEntry\x12\x0b\n\x03md5\x18\x01 \x01(\t\x12\x15\n\rrelative_path\x18\x02 \x01(\t"\x7f\n\x12MessageV4_SmapInfo\x12\x13\n\x0bcurrent_map\x18\x01 \x01(\t\x12\x17\n\x0fcurrent_map_md5\x18\x02 \x01(\t\x12;\n\x13current_map_entries\x18\x03 \x03(\x0b2\x1e.rbk4.protocol.CurrentMapEntryb\x06proto3'
    ),
)
_CURRENTMAPENTRY = _descriptor.Descriptor(
    name="CurrentMapEntry",
    full_name="rbk4.protocol.CurrentMapEntry",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="md5",
            full_name="rbk4.protocol.CurrentMapEntry.md5",
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
            name="relative_path",
            full_name="rbk4.protocol.CurrentMapEntry.relative_path",
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
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=43,
    serialized_end=96,
)
_MESSAGEV4_SMAPINFO = _descriptor.Descriptor(
    name="MessageV4_SmapInfo",
    full_name="rbk4.protocol.MessageV4_SmapInfo",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="current_map",
            full_name="rbk4.protocol.MessageV4_SmapInfo.current_map",
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
            name="current_map_md5",
            full_name="rbk4.protocol.MessageV4_SmapInfo.current_map_md5",
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
            name="current_map_entries",
            full_name="rbk4.protocol.MessageV4_SmapInfo.current_map_entries",
            index=2,
            number=3,
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
    serialized_start=98,
    serialized_end=225,
)
_MESSAGEV4_SMAPINFO.fields_by_name["current_map_entries"].message_type = (
    _CURRENTMAPENTRY
)
DESCRIPTOR.message_types_by_name["CurrentMapEntry"] = _CURRENTMAPENTRY
DESCRIPTOR.message_types_by_name["MessageV4_SmapInfo"] = _MESSAGEV4_SMAPINFO
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
CurrentMapEntry = _reflection.GeneratedProtocolMessageType(
    "CurrentMapEntry",
    (_message.Message,),
    dict(DESCRIPTOR=_CURRENTMAPENTRY, __module__="messageV4_smapinfo_pb2"),
)
_sym_db.RegisterMessage(CurrentMapEntry)
MessageV4_SmapInfo = _reflection.GeneratedProtocolMessageType(
    "MessageV4_SmapInfo",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_SMAPINFO, __module__="messageV4_smapinfo_pb2"),
)
_sym_db.RegisterMessage(MessageV4_SmapInfo)
