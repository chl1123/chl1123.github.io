import message_header_pb2 as _message_header_pb2
import message_recogresult_pb2 as _message_recogresult_pb2
import message_calibration_pb2 as _message_calibration_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgDataPackage(_message.Message):
    __slots__ = ["cloudData", "header", "irData", "rgbData"]
    CLOUDDATA_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    IRDATA_FIELD_NUMBER: ClassVar[int]
    RGBDATA_FIELD_NUMBER: ClassVar[int]
    cloudData: _message_recogresult_pb2.msgPointCloud
    header: _message_header_pb2.msgHeader
    irData: _message_calibration_pb2.msgImage
    rgbData: _message_calibration_pb2.msgImage
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., cloudData: Optional[Union[_message_recogresult_pb2.msgPointCloud, Mapping]] = ..., rgbData: Optional[Union[_message_calibration_pb2.msgImage, Mapping]] = ..., irData: Optional[Union[_message_calibration_pb2.msgImage, Mapping]] = ...) -> None: ...
