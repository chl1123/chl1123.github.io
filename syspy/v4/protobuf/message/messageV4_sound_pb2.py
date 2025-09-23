import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor.FileDescriptor(
    name="messageV4_sound.proto",
    package="rbk4.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x15messageV4_sound.proto\x12\rrbk4.protocol"R\n\x0fMessageV4_Sound\x12\x0e\n\x06status\x18\x01 \x01(\x05\x12\x12\n\nsound_name\x18\x02 \x01(\t\x12\x0c\n\x04loop\x18\x03 \x01(\x08\x12\r\n\x05count\x18\x04 \x01(\x05b\x06proto3'
    ),
)
_MESSAGEV4_SOUND = _descriptor.Descriptor(
    name="MessageV4_Sound",
    full_name="rbk4.protocol.MessageV4_Sound",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="status",
            full_name="rbk4.protocol.MessageV4_Sound.status",
            index=0,
            number=1,
            type=5,
            cpp_type=1,
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
            name="sound_name",
            full_name="rbk4.protocol.MessageV4_Sound.sound_name",
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
            name="loop",
            full_name="rbk4.protocol.MessageV4_Sound.loop",
            index=2,
            number=3,
            type=8,
            cpp_type=7,
            label=1,
            has_default_value=False,
            default_value=False,
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
            full_name="rbk4.protocol.MessageV4_Sound.count",
            index=3,
            number=4,
            type=5,
            cpp_type=1,
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
    serialized_start=40,
    serialized_end=122,
)
DESCRIPTOR.message_types_by_name["MessageV4_Sound"] = _MESSAGEV4_SOUND
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
MessageV4_Sound = _reflection.GeneratedProtocolMessageType(
    "MessageV4_Sound",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_SOUND, __module__="messageV4_sound_pb2"),
)
_sym_db.RegisterMessage(MessageV4_Sound)
