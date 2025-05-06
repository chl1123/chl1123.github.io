from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

import message_header_pb2 as _message_header_pb2

BAYER_BGGR16: PixelFormat
BAYER_BGGR8: PixelFormat
BAYER_GBRG16: PixelFormat
BAYER_GBRG8: PixelFormat
BAYER_GRBG16: PixelFormat
BAYER_GRBG8: PixelFormat
BAYER_RGGB16: PixelFormat
BAYER_RGGB8: PixelFormat
BGR16: PixelFormat
BGR8: PixelFormat
BGRA16: PixelFormat
BGRA8: PixelFormat
DESCRIPTOR: _descriptor.FileDescriptor
MONO16: PixelFormat
MONO8: PixelFormat
RGB16: PixelFormat
RGB8: PixelFormat
RGBA16: PixelFormat
RGBA8: PixelFormat
TYPE_16SC1: PixelFormat
TYPE_16SC2: PixelFormat
TYPE_16SC3: PixelFormat
TYPE_16SC4: PixelFormat
TYPE_16UC1: PixelFormat
TYPE_16UC2: PixelFormat
TYPE_16UC3: PixelFormat
TYPE_16UC4: PixelFormat
TYPE_32FC1: PixelFormat
TYPE_32FC2: PixelFormat
TYPE_32FC3: PixelFormat
TYPE_32FC4: PixelFormat
TYPE_32SC1: PixelFormat
TYPE_32SC2: PixelFormat
TYPE_32SC3: PixelFormat
TYPE_32SC4: PixelFormat
TYPE_64FC1: PixelFormat
TYPE_64FC2: PixelFormat
TYPE_64FC3: PixelFormat
TYPE_64FC4: PixelFormat
TYPE_8SC1: PixelFormat
TYPE_8SC2: PixelFormat
TYPE_8SC3: PixelFormat
TYPE_8SC4: PixelFormat
TYPE_8UC1: PixelFormat
TYPE_8UC2: PixelFormat
TYPE_8UC3: PixelFormat
TYPE_8UC4: PixelFormat
YUV422: PixelFormat


class Message_2DImage(_message.Message):
    """
    表示二维图像信息的模型类。

    Attributes:
        width (int): 图像的宽度，默认值为0。
        height (int): 图像的高度，默认值为0。
        data (bytes): 图像的数据，以字节形式存储，默认值为空字节串。
        encoding (str): 图像的编码格式，对应PixelFormat枚举类型，默认值为空字符串。
        base64Data (str): 图像的Base64编码数据，默认值为空字符串。
        fx (float): 相机的水平焦距，默认值为0.0。
        fy (float): 相机的垂直焦距，默认值为0.0。
        cx (float): 相机主点的x坐标，默认值为0.0。
        cy (float): 相机主点的y坐标，默认值为0.0。
    """
    __slots__ = ["base64Data", "cx", "cy", "data", "encoding", "fx", "fy", "height", "width"]
    BASE64DATA_FIELD_NUMBER: ClassVar[int]
    CX_FIELD_NUMBER: ClassVar[int]
    CY_FIELD_NUMBER: ClassVar[int]
    DATA_FIELD_NUMBER: ClassVar[int]
    ENCODING_FIELD_NUMBER: ClassVar[int]
    FX_FIELD_NUMBER: ClassVar[int]
    FY_FIELD_NUMBER: ClassVar[int]
    HEIGHT_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    base64Data: str
    cx: float
    cy: float
    data: bytes
    encoding: str
    fx: float
    fy: float
    height: int
    width: int

    def __init__(self, width: Optional[int] = ..., height: Optional[int] = ..., data: Optional[bytes] = ...,
                 encoding: Optional[str] = ..., base64Data: Optional[str] = ..., fx: Optional[float] = ...,
                 fy: Optional[float] = ..., cx: Optional[float] = ..., cy: Optional[float] = ...) -> None: ...


class Message_AllCameraCloud(_message.Message):
    """
    表示所有相机点云的模型。

    Attributes:
        allcloud (typing.List[Message_DepthCameraCloud]): 所有深度相机点云的列表，默认为空列表。
    """
    __slots__ = ["allcloud"]
    ALLCLOUD_FIELD_NUMBER: ClassVar[int]
    allcloud: _containers.RepeatedCompositeFieldContainer[Message_DepthCameraCloud]

    def __init__(self, allcloud: Optional[Iterable[Union[Message_DepthCameraCloud, Mapping]]] = ...) -> None: ...


class Message_DepthCameraCloud(_message.Message):
    """
    表示深度相机点云的模型。

    Attributes:
        header (typing.Optional[Message_Header]): 消息头部信息，可选，默认为 None。
        device_name (str): 设备名称，默认为空字符串。
        cloud (typing.List[Message_DepthCameraPoint]): 点云列表，默认为空列表。
        install (typing.Optional[Message_DepthCameraInstallInfo]): 相机安装信息，可选，默认为 None。
        device (typing.Optional[Message_DepthCameraDeviceInfo]): 相机设备信息，可选，默认为 None。
        image (typing.Optional[Message_2DImage]): 二维图像信息，可选，默认为 None。
        cloud_voxel (float): 点云体素大小，默认为 0.0。
    """
    __slots__ = ["cloud", "cloud_voxel", "device", "device_name", "header", "image", "install"]
    CLOUD_FIELD_NUMBER: ClassVar[int]
    CLOUD_VOXEL_FIELD_NUMBER: ClassVar[int]
    DEVICE_FIELD_NUMBER: ClassVar[int]
    DEVICE_NAME_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    IMAGE_FIELD_NUMBER: ClassVar[int]
    INSTALL_FIELD_NUMBER: ClassVar[int]
    cloud: _containers.RepeatedCompositeFieldContainer[Message_DepthCameraPoint]
    cloud_voxel: float
    device: Message_DepthCameraDeviceInfo
    device_name: str
    header: _message_header_pb2.Message_Header
    image: Message_2DImage
    install: Message_DepthCameraInstallInfo

    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 device_name: Optional[str] = ...,
                 cloud: Optional[Iterable[Union[Message_DepthCameraPoint, Mapping]]] = ...,
                 install: Optional[Union[Message_DepthCameraInstallInfo, Mapping]] = ...,
                 device: Optional[Union[Message_DepthCameraDeviceInfo, Mapping]] = ...,
                 image: Optional[Union[Message_2DImage, Mapping]] = ...,
                 cloud_voxel: Optional[float] = ...) -> None: ...


class Message_DepthCameraDeviceInfo(_message.Message):
    """
    表示深度相机设备信息的模型。

    Attributes:
        device_name (str): 设备名称，默认为空字符串。
        points (typing.List[Message_ScanRangePoint]): 点的列表，默认为空列表。
    """
    __slots__ = ["device_name", "point"]
    DEVICE_NAME_FIELD_NUMBER: ClassVar[int]
    POINT_FIELD_NUMBER: ClassVar[int]
    device_name: str
    point: _containers.RepeatedCompositeFieldContainer[Message_ScanRangePoint]

    def __init__(self, device_name: Optional[str] = ...,
                 point: Optional[Iterable[Union[Message_ScanRangePoint, Mapping]]] = ...) -> None: ...


class Message_DepthCameraInstallInfo(_message.Message):
    """
    表示深度相机安装信息的模型类。

    Attributes:
        x (float): 深度相机安装位置的x坐标，默认值为0.0。
        y (float): 深度相机安装位置的y坐标，默认值为0.0。
        z (float): 深度相机安装位置的z坐标，默认值为0.0。
        roll (float): 深度相机绕x轴的旋转角度（横滚角），默认值为0.0。
        pitch (float): 深度相机绕y轴的旋转角度（俯仰角），默认值为0.0。
        yaw (float): 深度相机绕z轴的旋转角度（偏航角），默认值为0.0。
    """
    __slots__ = ["pitch", "roll", "x", "y", "yaw", "z"]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    pitch: float
    roll: float
    x: float
    y: float
    yaw: float
    z: float

    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...,
                 roll: Optional[float] = ..., pitch: Optional[float] = ..., yaw: Optional[float] = ...) -> None: ...


class Message_DepthCameraPoint(_message.Message):
    """
    表示深度相机点的模型。

    Attributes:
        x (float): x 坐标，默认为 0.0。
        y (float): y 坐标，默认为 0.0。
        z (float): z 坐标，默认为 0.0。
        label (int): 点的标签，用于标识不同类型，如障碍洞为 1，物为 1，人为 2，默认为 0。
    """
    __slots__ = ["label", "x", "y", "z"]
    LABEL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    label: int
    x: float
    y: float
    z: float

    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...,
                 label: Optional[int] = ...) -> None: ...


class Message_ScanRangePoint(_message.Message):
    """
    表示扫描范围点信息的模型类。

    Attributes:
        x (float): 扫描范围点的x坐标，默认值为0.0。
        y (float): 扫描范围点的y坐标，默认值为0.0。
    """
    __slots__ = ["x", "y"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float

    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ...) -> None: ...


class PixelFormat(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    """
    定义图像像素格式的枚举类。

    Attributes:
        RGB8 (int): 8位RGB格式。
        RGBA8 (int): 8位RGBA格式。
        RGB16 (int): 16位RGB格式。
        RGBA16 (int): 16位RGBA格式。
        BGR8 (int): 8位BGR格式。
        BGRA8 (int): 8位BGRA格式。
        BGR16 (int): 16位BGR格式。
        BGRA16 (int): 16位BGRA格式。
        MONO8 (int): 8位单通道灰度格式。
        MONO16 (int): 16位单通道灰度格式。
        TYPE_8UC1 (int): OpenCV 8位无符号单通道矩阵类型。
        TYPE_8UC2 (int): OpenCV 8位无符号双通道矩阵类型。
        TYPE_8UC3 (int): OpenCV 8位无符号三通道矩阵类型。
        TYPE_8UC4 (int): OpenCV 8位无符号四通道矩阵类型。
        TYPE_8SC1 (int): OpenCV 8位有符号单通道矩阵类型。
        TYPE_8SC2 (int): OpenCV 8位有符号双通道矩阵类型。
        TYPE_8SC3 (int): OpenCV 8位有符号三通道矩阵类型。
        TYPE_8SC4 (int): OpenCV 8位有符号四通道矩阵类型。
        TYPE_16UC1 (int): OpenCV 16位无符号单通道矩阵类型。
        TYPE_16UC2 (int): OpenCV 16位无符号双通道矩阵类型。
        TYPE_16UC3 (int): OpenCV 16位无符号三通道矩阵类型。
        TYPE_16UC4 (int): OpenCV 16位无符号四通道矩阵类型。
        TYPE_16SC1 (int): OpenCV 16位有符号单通道矩阵类型。
        TYPE_16SC2 (int): OpenCV 16位有符号双通道矩阵类型。
        TYPE_16SC3 (int): OpenCV 16位有符号三通道矩阵类型。
        TYPE_16SC4 (int): OpenCV 16位有符号四通道矩阵类型。
        TYPE_32SC1 (int): OpenCV 32位有符号单通道矩阵类型。
        TYPE_32SC2 (int): OpenCV 32位有符号双通道矩阵类型。
        TYPE_32SC3 (int): OpenCV 32位有符号三通道矩阵类型。
        TYPE_32SC4 (int): OpenCV 32位有符号四通道矩阵类型。
        TYPE_32FC1 (int): OpenCV 32位浮点单通道矩阵类型。
        TYPE_32FC2 (int): OpenCV 32位浮点双通道矩阵类型。
        TYPE_32FC3 (int): OpenCV 32位浮点三通道矩阵类型。
        TYPE_32FC4 (int): OpenCV 32位浮点四通道矩阵类型。
        TYPE_64FC1 (int): OpenCV 64位浮点单通道矩阵类型。
        TYPE_64FC2 (int): OpenCV 64位浮点双通道矩阵类型。
        TYPE_64FC3 (int): OpenCV 64位浮点三通道矩阵类型。
        TYPE_64FC4 (int): OpenCV 64位浮点四通道矩阵类型。
        BAYER_RGGB8 (int): 8位RGGB拜耳编码格式。
        BAYER_BGGR8 (int): 8位BGGR拜耳编码格式。
        BAYER_GBRG8 (int): 8位GBRG拜耳编码格式。
        BAYER_GRBG8 (int): 8GRBG拜耳编码格式。
        BAYER_RGGB16 (int): 16位RGGB拜耳编码格式。
        BAYER_BGGR16 (int): 16位BGGR拜耳编码格式。
        BAYER_GBRG16 (int): 16位GBRG拜耳编码格式。
        BAYER_GRBG16 (int): 16位GRBG拜耳编码格式。
        YUV422 (int): 8位深度的UYVY版本的YUV422编解码格式 http://www.fourcc.org/yuv.php#UYVY
    """
    __slots__ = []
