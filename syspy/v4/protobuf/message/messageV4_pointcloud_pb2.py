import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
from . import message_header_pb2 as message__header__pb2

DESCRIPTOR = _descriptor.FileDescriptor(
    name="messageV4_pointcloud.proto",
    package="rbk4.protocol",
    syntax="proto3",
    serialized_options=None,
    serialized_pb=_b(
        '\n\x1amessageV4_pointcloud.proto\x12\rrbk4.protocol\x1a\x14message_header.proto"°\x01\n\x14MessageV4_PointCloud\x12\'\n\x06header\x18\x01 \x01(\x0b2\x17.rbk.protocol.msgHeader\x12\r\n\x05width\x18\x02 \x01(\r\x12\x0e\n\x06height\x18\x03 \x01(\r\x12\x10\n\x08is_dense\x18\x04 \x01(\x08\x120\n\x04type\x18\x05 \x01(\x0e2".rbk4.protocol.MessageV4_CloudType\x12\x0c\n\x04data\x18\x06 \x01(\x0c"[\n\x15MessageV4_SensorPoint\x12\t\n\x01x\x18\x01 \x01(\x01\x12\t\n\x01y\x18\x02 \x01(\x01\x12\t\n\x01z\x18\x03 \x01(\x01\x12\x13\n\x0bis_obstacle\x18\x04 \x01(\x08\x12\x0c\n\x04rssi\x18\x05 \x01(\x01"¯\x03\n\x1cMessageV4_SensorPointCluster\x12\'\n\x06header\x18\x01 \x01(\x0b2\x17.rbk.protocol.msgHeader\x12>\n\x04type\x18\x02 \x01(\x0e20.rbk4.protocol.MessageV4_SensorPointCluster.Type\x12\n\n\x02id\x18\x03 \x01(\t\x123\n\x05point\x18\x04 \x03(\x0b2$.rbk4.protocol.MessageV4_SensorPoint"ä\x01\n\x04Type\x12\x0e\n\nUltrasonic\x10\x00\x12\t\n\x05Laser\x10\x01\x12\x0f\n\x0bFallingdown\x10\x02\x12\r\n\tCollision\x10\x03\x12\x0c\n\x08Infrared\x10\x04\x12\x10\n\x0cVirtualPoint\x10\x05\x12\x0f\n\x0bAPIObstacle\x10\x06\x12\x11\n\rReservedPoint\x10\x07\x12\x10\n\x0cDiUltrasonic\x10\x08\x12\x0f\n\x0bDepthCamera\x10\t\x12\x17\n\x13ReservedDepthCamera\x10\n\x12\x10\n\x0cDistanceNode\x10\x0b\x12\x0f\n\x0bADCollision\x10\x0c"¥\x01\n\x1aMessageV4_SensorPointCloud\x12C\n\x0eglobal_cluster\x18\x01 \x03(\x0b2+.rbk4.protocol.MessageV4_SensorPointCluster\x12B\n\rlocal_cluster\x18\x02 \x03(\x0b2+.rbk4.protocol.MessageV4_SensorPointCluster*n\n\x13MessageV4_CloudType\x12\r\n\tPOINT_XYZ\x10\x00\x12\x0e\n\nPOINT_XYZI\x10\x01\x12\x10\n\x0cPOINT_XYZRGB\x10\x02\x12\x11\n\rPOINT_XYZRGBA\x10\x03\x12\x13\n\x0fPOINT_XYZNORMAL\x10\x04b\x06proto3'
    ),
    dependencies=[message__header__pb2.DESCRIPTOR],
)
_MESSAGEV4_CLOUDTYPE = _descriptor.EnumDescriptor(
    name="MessageV4_CloudType",
    full_name="rbk4.protocol.MessageV4_CloudType",
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name="POINT_XYZ", index=0, number=0, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="POINT_XYZI", index=1, number=1, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="POINT_XYZRGB", index=2, number=2, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="POINT_XYZRGBA", index=3, number=3, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="POINT_XYZNORMAL",
            index=4,
            number=4,
            serialized_options=None,
            type=None,
        ),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=941,
    serialized_end=1051,
)
_sym_db.RegisterEnumDescriptor(_MESSAGEV4_CLOUDTYPE)
MessageV4_CloudType = enum_type_wrapper.EnumTypeWrapper(_MESSAGEV4_CLOUDTYPE)
POINT_XYZ = 0
POINT_XYZI = 1
POINT_XYZRGB = 2
POINT_XYZRGBA = 3
POINT_XYZNORMAL = 4
_MESSAGEV4_SENSORPOINTCLUSTER_TYPE = _descriptor.EnumDescriptor(
    name="Type",
    full_name="rbk4.protocol.MessageV4_SensorPointCluster.Type",
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name="Ultrasonic", index=0, number=0, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Laser", index=1, number=1, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Fallingdown", index=2, number=2, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Collision", index=3, number=3, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Infrared", index=4, number=4, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="VirtualPoint", index=5, number=5, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="APIObstacle", index=6, number=6, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="ReservedPoint", index=7, number=7, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="DiUltrasonic", index=8, number=8, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="DepthCamera", index=9, number=9, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="ReservedDepthCamera",
            index=10,
            number=10,
            serialized_options=None,
            type=None,
        ),
        _descriptor.EnumValueDescriptor(
            name="DistanceNode", index=11, number=11, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="ADCollision", index=12, number=12, serialized_options=None, type=None
        ),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=543,
    serialized_end=771,
)
_sym_db.RegisterEnumDescriptor(_MESSAGEV4_SENSORPOINTCLUSTER_TYPE)
_MESSAGEV4_POINTCLOUD = _descriptor.Descriptor(
    name="MessageV4_PointCloud",
    full_name="rbk4.protocol.MessageV4_PointCloud",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="header",
            full_name="rbk4.protocol.MessageV4_PointCloud.header",
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
            name="width",
            full_name="rbk4.protocol.MessageV4_PointCloud.width",
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
            name="height",
            full_name="rbk4.protocol.MessageV4_PointCloud.height",
            index=2,
            number=3,
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
            name="is_dense",
            full_name="rbk4.protocol.MessageV4_PointCloud.is_dense",
            index=3,
            number=4,
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
            name="type",
            full_name="rbk4.protocol.MessageV4_PointCloud.type",
            index=4,
            number=5,
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
            name="data",
            full_name="rbk4.protocol.MessageV4_PointCloud.data",
            index=5,
            number=6,
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
    serialized_start=68,
    serialized_end=244,
)
_MESSAGEV4_SENSORPOINT = _descriptor.Descriptor(
    name="MessageV4_SensorPoint",
    full_name="rbk4.protocol.MessageV4_SensorPoint",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="x",
            full_name="rbk4.protocol.MessageV4_SensorPoint.x",
            index=0,
            number=1,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="y",
            full_name="rbk4.protocol.MessageV4_SensorPoint.y",
            index=1,
            number=2,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="z",
            full_name="rbk4.protocol.MessageV4_SensorPoint.z",
            index=2,
            number=3,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="is_obstacle",
            full_name="rbk4.protocol.MessageV4_SensorPoint.is_obstacle",
            index=3,
            number=4,
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
            name="rssi",
            full_name="rbk4.protocol.MessageV4_SensorPoint.rssi",
            index=4,
            number=5,
            type=1,
            cpp_type=5,
            label=1,
            has_default_value=False,
            default_value=float(0),
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
    serialized_start=246,
    serialized_end=337,
)
_MESSAGEV4_SENSORPOINTCLUSTER = _descriptor.Descriptor(
    name="MessageV4_SensorPointCluster",
    full_name="rbk4.protocol.MessageV4_SensorPointCluster",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="header",
            full_name="rbk4.protocol.MessageV4_SensorPointCluster.header",
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
            name="type",
            full_name="rbk4.protocol.MessageV4_SensorPointCluster.type",
            index=1,
            number=2,
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
            name="id",
            full_name="rbk4.protocol.MessageV4_SensorPointCluster.id",
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
            name="point",
            full_name="rbk4.protocol.MessageV4_SensorPointCluster.point",
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
    ],
    extensions=[],
    nested_types=[],
    enum_types=[_MESSAGEV4_SENSORPOINTCLUSTER_TYPE],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=340,
    serialized_end=771,
)
_MESSAGEV4_SENSORPOINTCLOUD = _descriptor.Descriptor(
    name="MessageV4_SensorPointCloud",
    full_name="rbk4.protocol.MessageV4_SensorPointCloud",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="global_cluster",
            full_name="rbk4.protocol.MessageV4_SensorPointCloud.global_cluster",
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
        ),
        _descriptor.FieldDescriptor(
            name="local_cluster",
            full_name="rbk4.protocol.MessageV4_SensorPointCloud.local_cluster",
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
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=774,
    serialized_end=939,
)
_MESSAGEV4_POINTCLOUD.fields_by_name["header"].message_type = (
    message__header__pb2._MSGHEADER
)
_MESSAGEV4_POINTCLOUD.fields_by_name["type"].enum_type = _MESSAGEV4_CLOUDTYPE
_MESSAGEV4_SENSORPOINTCLUSTER.fields_by_name["header"].message_type = (
    message__header__pb2._MSGHEADER
)
_MESSAGEV4_SENSORPOINTCLUSTER.fields_by_name["type"].enum_type = (
    _MESSAGEV4_SENSORPOINTCLUSTER_TYPE
)
_MESSAGEV4_SENSORPOINTCLUSTER.fields_by_name["point"].message_type = (
    _MESSAGEV4_SENSORPOINT
)
_MESSAGEV4_SENSORPOINTCLUSTER_TYPE.containing_type = _MESSAGEV4_SENSORPOINTCLUSTER
_MESSAGEV4_SENSORPOINTCLOUD.fields_by_name["global_cluster"].message_type = (
    _MESSAGEV4_SENSORPOINTCLUSTER
)
_MESSAGEV4_SENSORPOINTCLOUD.fields_by_name["local_cluster"].message_type = (
    _MESSAGEV4_SENSORPOINTCLUSTER
)
DESCRIPTOR.message_types_by_name["MessageV4_PointCloud"] = _MESSAGEV4_POINTCLOUD
DESCRIPTOR.message_types_by_name["MessageV4_SensorPoint"] = _MESSAGEV4_SENSORPOINT
DESCRIPTOR.message_types_by_name["MessageV4_SensorPointCluster"] = (
    _MESSAGEV4_SENSORPOINTCLUSTER
)
DESCRIPTOR.message_types_by_name["MessageV4_SensorPointCloud"] = (
    _MESSAGEV4_SENSORPOINTCLOUD
)
DESCRIPTOR.enum_types_by_name["MessageV4_CloudType"] = _MESSAGEV4_CLOUDTYPE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
MessageV4_PointCloud = _reflection.GeneratedProtocolMessageType(
    "MessageV4_PointCloud",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_POINTCLOUD, __module__="messageV4_pointcloud_pb2"),
)
_sym_db.RegisterMessage(MessageV4_PointCloud)
MessageV4_SensorPoint = _reflection.GeneratedProtocolMessageType(
    "MessageV4_SensorPoint",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_SENSORPOINT, __module__="messageV4_pointcloud_pb2"),
)
_sym_db.RegisterMessage(MessageV4_SensorPoint)
MessageV4_SensorPointCluster = _reflection.GeneratedProtocolMessageType(
    "MessageV4_SensorPointCluster",
    (_message.Message,),
    dict(
        DESCRIPTOR=_MESSAGEV4_SENSORPOINTCLUSTER, __module__="messageV4_pointcloud_pb2"
    ),
)
_sym_db.RegisterMessage(MessageV4_SensorPointCluster)
MessageV4_SensorPointCloud = _reflection.GeneratedProtocolMessageType(
    "MessageV4_SensorPointCloud",
    (_message.Message,),
    dict(DESCRIPTOR=_MESSAGEV4_SENSORPOINTCLOUD, __module__="messageV4_pointcloud_pb2"),
)
_sym_db.RegisterMessage(MessageV4_SensorPointCloud)
