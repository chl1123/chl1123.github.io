import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
from . import message_header_pb2 as message__header__pb2
from . import messageV4_image_pb2 as messageV4__image__pb2
from . import messageV4_stampedtransform_pb2 as messageV4__stampedtransform__pb2
from . import messageV4_cameraintrinsic_pb2 as messageV4__cameraintrinsic__pb2

DESCRIPTOR = _descriptor.FileDescriptor(
    name="messageV4_recognizeresult.proto",
    package="rbk4.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x1fmessageV4_recognizeresult.proto\x12\rrbk4.protocol\x1a\x14message_header.proto\x1a\x15messageV4_image.proto\x1a messageV4_stampedtransform.proto\x1a\x1fmessageV4_cameraintrinsic.proto"ª\x02\n\x16MessageV4_PercepResAPI\x12\x12\n\nclass_name\x18\x01 \x01(\t\x12\n\n\x02ID\x18\x02 \x01(\t\x129\n\x0btranslation\x18\x03 \x01(\x0b2$.rbk4.protocol.MessageV4_Translation\x123\n\x08rotation\x18\x04 \x01(\x0b2!.rbk4.protocol.MessageV4_Rotation\x121\n\tresultImg\x18\x05 \x01(\x0b2\x1e.rbk4.protocol.MessageV4_Image\x12\x0c\n\x04info\x18\x06 \x01(\t\x12\x16\n\x0ereco_file_name\x18\x07 \x01(\t\x12\'\n\x06header\x18\x08 \x01(\x0b2\x17.rbk.protocol.msgHeader"R\n\x19MessageV4_AllPercepResAPI\x125\n\x06result\x18\x01 \x03(\x0b2%.rbk4.protocol.MessageV4_PercepResAPI"\x81\x01\n\x12MessageV4_GraspRes\x12&\n\x04type\x18\x01 \x01(\x0e2\x18.rbk4.protocol.GraspType\x125\n\tgrasp_pos\x18\x02 \x01(\x0b2".rbk4.protocol.MessageV4_Extrinsic\x12\x0c\n\x04info\x18\x03 \x01(\t"Æ\x01\n\x15MessageV4_GraspResAPI\x12\'\n\x06header\x18\x01 \x01(\x0b2\x17.rbk.protocol.msgHeader\x12\x12\n\nclass_name\x18\x02 \x01(\t\x12\n\n\x02ID\x18\x03 \x01(\t\x121\n\x06grasps\x18\x04 \x03(\x0b2!.rbk4.protocol.MessageV4_GraspRes\x121\n\tresultImg\x18\x06 \x01(\x0b2\x1e.rbk4.protocol.MessageV4_Image"P\n\x18MessageV4_AllGraspResAPI\x124\n\x06result\x18\x01 \x03(\x0b2$.rbk4.protocol.MessageV4_GraspResAPI*3\n\tGraspType\x12\t\n\x05Grasp\x10\x00\x12\x08\n\x04Push\x10\x01\x12\x08\n\x04Pull\x10\x02\x12\x07\n\x03Hug\x10\x03b\x06proto3'
    ),
    dependencies=[
        message__header__pb2.DESCRIPTOR,
        messageV4__image__pb2.DESCRIPTOR,
        messageV4__stampedtransform__pb2.DESCRIPTOR,
        messageV4__cameraintrinsic__pb2.DESCRIPTOR,
    ],
)
_GRASPTYPE = _descriptor.EnumDescriptor(
    name="GraspType",
    full_name="rbk4.protocol.GraspType",
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name="Grasp", index=0, number=0, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Push", index=1, number=1, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Pull", index=2, number=2, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Hug", index=3, number=3, serialized_options=None, type=None
        ),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=962,
    serialized_end=1013,
)
_sym_db.RegisterEnumDescriptor(_GRASPTYPE)
GraspType = enum_type_wrapper.EnumTypeWrapper(_GRASPTYPE)
Grasp = 0
Push = 1
Pull = 2
Hug = 3
_MESSAGEV4_PERCEPRESAPI = _descriptor.Descriptor(
    name="MessageV4_PercepResAPI",
    full_name="rbk4.protocol.MessageV4_PercepResAPI",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="class_name",
            full_name="rbk4.protocol.MessageV4_PercepResAPI.class_name",
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
            name="ID",
            full_name="rbk4.protocol.MessageV4_PercepResAPI.ID",
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
            name="translation",
            full_name="rbk4.protocol.MessageV4_PercepResAPI.translation",
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
            name="rotation",
            full_name="rbk4.protocol.MessageV4_PercepResAPI.rotation",
            index=3,
            number=4,
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
            name="resultImg",
            full_name="rbk4.protocol.MessageV4_PercepResAPI.resultImg",
            index=4,
            number=5,
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
            name="info",
            full_name="rbk4.protocol.MessageV4_PercepResAPI.info",
            index=5,
            number=6,
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
            name="reco_file_name",
            full_name="rbk4.protocol.MessageV4_PercepResAPI.reco_file_name",
            index=6,
            number=7,
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
            name="header",
            full_name="rbk4.protocol.MessageV4_PercepResAPI.header",
            index=7,
            number=8,
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
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=163,
    serialized_end=461,
)
_MESSAGEV4_ALLPERCEPRESAPI = _descriptor.Descriptor(
    name="MessageV4_AllPercepResAPI",
    full_name="rbk4.protocol.MessageV4_AllPercepResAPI",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="result",
            full_name="rbk4.protocol.MessageV4_AllPercepResAPI.result",
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
    serialized_start=463,
    serialized_end=545,
)
_MESSAGEV4_GRASPRES = _descriptor.Descriptor(
    name="MessageV4_GraspRes",
    full_name="rbk4.protocol.MessageV4_GraspRes",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="type",
            full_name="rbk4.protocol.MessageV4_GraspRes.type",
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
            name="grasp_pos",
            full_name="rbk4.protocol.MessageV4_GraspRes.grasp_pos",
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
        _descriptor.FieldDescriptor(
            name="info",
            full_name="rbk4.protocol.MessageV4_GraspRes.info",
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
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=548,
    serialized_end=677,
)
_MESSAGEV4_GRASPRESAPI = _descriptor.Descriptor(
    name="MessageV4_GraspResAPI",
    full_name="rbk4.protocol.MessageV4_GraspResAPI",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="header",
            full_name="rbk4.protocol.MessageV4_GraspResAPI.header",
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
            name="class_name",
            full_name="rbk4.protocol.MessageV4_GraspResAPI.class_name",
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
            name="ID",
            full_name="rbk4.protocol.MessageV4_GraspResAPI.ID",
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
            name="grasps",
            full_name="rbk4.protocol.MessageV4_GraspResAPI.grasps",
            index=3,
            number=4,
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
        _descriptor.FieldDescriptor(
            name="resultImg",
            full_name="rbk4.protocol.MessageV4_GraspResAPI.resultImg",
            index=4,
            number=6,
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
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=680,
    serialized_end=878,
)
_MESSAGEV4_ALLGRASPRESAPI = _descriptor.Descriptor(
    name="MessageV4_AllGraspResAPI",
    full_name="rbk4.protocol.MessageV4_AllGraspResAPI",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="result",
            full_name="rbk4.protocol.MessageV4_AllGraspResAPI.result",
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
    serialized_start=880,
    serialized_end=960,
)
_MESSAGEV4_PERCEPRESAPI.fields_by_name["translation"].message_type = (
    messageV4__stampedtransform__pb2._MESSAGEV4_TRANSLATION
)
_MESSAGEV4_PERCEPRESAPI.fields_by_name["rotation"].message_type = (
    messageV4__stampedtransform__pb2._MESSAGEV4_ROTATION
)
_MESSAGEV4_PERCEPRESAPI.fields_by_name["resultImg"].message_type = (
    messageV4__image__pb2._MESSAGEV4_IMAGE
)
_MESSAGEV4_PERCEPRESAPI.fields_by_name["header"].message_type = (
    message__header__pb2._MSGHEADER
)
_MESSAGEV4_ALLPERCEPRESAPI.fields_by_name["result"].message_type = (
    _MESSAGEV4_PERCEPRESAPI
)
_MESSAGEV4_GRASPRES.fields_by_name["type"].enum_type = _GRASPTYPE
_MESSAGEV4_GRASPRES.fields_by_name["grasp_pos"].message_type = (
    messageV4__cameraintrinsic__pb2._MESSAGEV4_EXTRINSIC
)
_MESSAGEV4_GRASPRESAPI.fields_by_name["header"].message_type = (
    message__header__pb2._MSGHEADER
)
_MESSAGEV4_GRASPRESAPI.fields_by_name["grasps"].message_type = _MESSAGEV4_GRASPRES
_MESSAGEV4_GRASPRESAPI.fields_by_name["resultImg"].message_type = (
    messageV4__image__pb2._MESSAGEV4_IMAGE
)
_MESSAGEV4_ALLGRASPRESAPI.fields_by_name["result"].message_type = _MESSAGEV4_GRASPRESAPI
DESCRIPTOR.message_types_by_name["MessageV4_PercepResAPI"] = _MESSAGEV4_PERCEPRESAPI
DESCRIPTOR.message_types_by_name["MessageV4_AllPercepResAPI"] = (
    _MESSAGEV4_ALLPERCEPRESAPI
)
DESCRIPTOR.message_types_by_name["MessageV4_GraspRes"] = _MESSAGEV4_GRASPRES
DESCRIPTOR.message_types_by_name["MessageV4_GraspResAPI"] = _MESSAGEV4_GRASPRESAPI
DESCRIPTOR.message_types_by_name["MessageV4_AllGraspResAPI"] = _MESSAGEV4_ALLGRASPRESAPI
DESCRIPTOR.enum_types_by_name["GraspType"] = _GRASPTYPE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
MessageV4_PercepResAPI = _reflection.GeneratedProtocolMessageType(
    "MessageV4_PercepResAPI",
    (_message.Message,),
    dict(
        DESCRIPTOR=_MESSAGEV4_PERCEPRESAPI, __module__="messageV4_recognizeresult_pb2"
    ),
)
_sym_db.RegisterMessage(MessageV4_PercepResAPI)
MessageV4_AllPercepResAPI = _reflection.GeneratedProtocolMessageType(
    "MessageV4_AllPercepResAPI",
    (_message.Message,),
    dict(
        DESCRIPTOR=_MESSAGEV4_ALLPERCEPRESAPI,
        __module__="messageV4_recognizeresult_pb2",
    ),
)
_sym_db.RegisterMessage(MessageV4_AllPercepResAPI)
MessageV4_GraspRes = _reflection.GeneratedProtocolMessageType(
    "MessageV4_GraspRes",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_GRASPRES, __module__="messageV4_recognizeresult_pb2"),
)
_sym_db.RegisterMessage(MessageV4_GraspRes)
MessageV4_GraspResAPI = _reflection.GeneratedProtocolMessageType(
    "MessageV4_GraspResAPI",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_GRASPRESAPI, __module__="messageV4_recognizeresult_pb2"),
)
_sym_db.RegisterMessage(MessageV4_GraspResAPI)
MessageV4_AllGraspResAPI = _reflection.GeneratedProtocolMessageType(
    "MessageV4_AllGraspResAPI",
    (_message.Message,),
    dict(
        DESCRIPTOR=_MESSAGEV4_ALLGRASPRESAPI, __module__="messageV4_recognizeresult_pb2"
    ),
)
_sym_db.RegisterMessage(MessageV4_AllGraspResAPI)
