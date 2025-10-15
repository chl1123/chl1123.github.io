from .pymodule import PyModule

# 导入消息模块, 避免报错
import syspy.v4.protobuf.message.messageV4_stampedtransform_pb2


def canTransformStatic(target_frame, source_frame, time_sec):
    return PyModule.canTransformStatic(target_frame, source_frame, time_sec)


def lookupTransformStatic(target_frame, source_frame, time_sec):
    return PyModule.lookupTransformStatic(target_frame, source_frame, time_sec)


def canTransform(target_frame, source_frame, time_sec):
    return PyModule.canTransform(target_frame, source_frame, time_sec)


def lookupTransform(target_frame, source_frame, time_sec):
    return PyModule.lookupTransform(target_frame, source_frame, time_sec)
