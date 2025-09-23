import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor.FileDescriptor(
    name="messageV4_initstate.proto",
    package="rbk4.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x19messageV4_initstate.proto\x12\rrbk4.protocol"\x99\x02\n\x13MessageV4_InitState\x127\n\x05state\x18\x01 \x01(\x0e2(.rbk4.protocol.MessageV4_InitState.State\x12:\n\x04next\x18\x02 \x03(\x0b2,.rbk4.protocol.MessageV4_InitState.NextEntry\x1aO\n\tNextEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x121\n\x05value\x18\x02 \x01(\x0b2".rbk4.protocol.MessageV4_InitState:\x028\x01"<\n\x05State\x12\x0b\n\x07WAITING\x10\x00\x12\r\n\tEXECUTING\x10\x01\x12\x0b\n\x07SUCCESS\x10\x02\x12\n\n\x06FAILED\x10\x03b\x06proto3'
    ),
)
_MESSAGEV4_INITSTATE_STATE = _descriptor.EnumDescriptor(
    name="State",
    full_name="rbk4.protocol.MessageV4_InitState.State",
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name="WAITING", index=0, number=0, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="EXECUTING", index=1, number=1, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="SUCCESS", index=2, number=2, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="FAILED", index=3, number=3, serialized_options=None, type=None
        ),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=266,
    serialized_end=326,
)
_sym_db.RegisterEnumDescriptor(_MESSAGEV4_INITSTATE_STATE)
_MESSAGEV4_INITSTATE_NEXTENTRY = _descriptor.Descriptor(
    name="NextEntry",
    full_name="rbk4.protocol.MessageV4_InitState.NextEntry",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="key",
            full_name="rbk4.protocol.MessageV4_InitState.NextEntry.key",
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
            name="value",
            full_name="rbk4.protocol.MessageV4_InitState.NextEntry.value",
            index=1,
            number=2,
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
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=_b("8\x01"),
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=185,
    serialized_end=264,
)
_MESSAGEV4_INITSTATE = _descriptor.Descriptor(
    name="MessageV4_InitState",
    full_name="rbk4.protocol.MessageV4_InitState",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="state",
            full_name="rbk4.protocol.MessageV4_InitState.state",
            index=0,
            number=1,
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
            name="next",
            full_name="rbk4.protocol.MessageV4_InitState.next",
            index=1,
            number=2,
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
    nested_types=[_MESSAGEV4_INITSTATE_NEXTENTRY],
    enum_types=[_MESSAGEV4_INITSTATE_STATE],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=45,
    serialized_end=326,
)
_MESSAGEV4_INITSTATE_NEXTENTRY.fields_by_name["value"].message_type = (
    _MESSAGEV4_INITSTATE
)
_MESSAGEV4_INITSTATE_NEXTENTRY.containing_type = _MESSAGEV4_INITSTATE
_MESSAGEV4_INITSTATE.fields_by_name["state"].enum_type = _MESSAGEV4_INITSTATE_STATE
_MESSAGEV4_INITSTATE.fields_by_name["next"].message_type = (
    _MESSAGEV4_INITSTATE_NEXTENTRY
)
_MESSAGEV4_INITSTATE_STATE.containing_type = _MESSAGEV4_INITSTATE
DESCRIPTOR.message_types_by_name["MessageV4_InitState"] = _MESSAGEV4_INITSTATE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
MessageV4_InitState = _reflection.GeneratedProtocolMessageType(
    "MessageV4_InitState",
    (_message.Message,),
    dict(
        NextEntry=_reflection.GeneratedProtocolMessageType(
            "NextEntry",
            (_message.Message,),
            dict(
                DESCRIPTOR=_MESSAGEV4_INITSTATE_NEXTENTRY,
                __module__="messageV4_initstate_pb2",
            ),
        ),
        DESCRIPTOR=_MESSAGEV4_INITSTATE,
        __module__="messageV4_initstate_pb2",
    ),
)
_sym_db.RegisterMessage(MessageV4_InitState)
_sym_db.RegisterMessage(MessageV4_InitState.NextEntry)
_MESSAGEV4_INITSTATE_NEXTENTRY._options = None
