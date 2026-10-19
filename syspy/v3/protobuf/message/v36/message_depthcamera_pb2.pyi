from . import message_header_pb2 as _message_header_pb2
from . import message_recogresult_pb2 as _message_recogresult_pb2
from . import message_calibration_pb2 as _message_calibration_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgDataPackage(_message.Message):
    __slots__ = ["cloudData", "header", "irData", "rgbData"]
    CLOUDDATA_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    IRDATA_FIELD_NUMBER: _ClassVar[int]
    RGBDATA_FIELD_NUMBER: _ClassVar[int]
    cloudData: _message_recogresult_pb2.msgPointCloud
    header: _message_header_pb2.msgHeader
    irData: _message_calibration_pb2.msgImage
    rgbData: _message_calibration_pb2.msgImage
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., cloudData: _Optional[_Union[_message_recogresult_pb2.msgPointCloud, _Mapping]] = ..., rgbData: _Optional[_Union[_message_calibration_pb2.msgImage, _Mapping]] = ..., irData: _Optional[_Union[_message_calibration_pb2.msgImage, _Mapping]] = ...) -> None: ...
