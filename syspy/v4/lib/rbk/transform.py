from .pymodule import PyModule


def canTransformStatic(target_frame, source_frame, time_sec):
    return PyModule.canTransformStatic(target_frame, source_frame, time_sec)


def lookupTransformStatic(target_frame, source_frame, time_sec):
    return PyModule.lookupTransformStatic(target_frame, source_frame, time_sec)


def canTransform(target_frame, source_frame, time_sec):
    return PyModule.canTransform(target_frame, source_frame, time_sec)


def lookupTransform(target_frame, source_frame, time_sec):
    return PyModule.lookupTransform(target_frame, source_frame, time_sec)
