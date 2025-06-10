# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing
from enum import IntEnum

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field

from .message_header_p2p import Message_Header


class PixelFormat(IntEnum):
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
    RGB8 = 0
    RGBA8 = 1
    RGB16 = 2
    RGBA16 = 3
    BGR8 = 4
    BGRA8 = 5
    BGR16 = 6
    BGRA16 = 7
    MONO8 = 8
    MONO16 = 9
    TYPE_8UC1 = 10
    TYPE_8UC2 = 11
    TYPE_8UC3 = 12
    TYPE_8UC4 = 13
    TYPE_8SC1 = 14
    TYPE_8SC2 = 15
    TYPE_8SC3 = 16
    TYPE_8SC4 = 17
    TYPE_16UC1 = 18
    TYPE_16UC2 = 19
    TYPE_16UC3 = 20
    TYPE_16UC4 = 21
    TYPE_16SC1 = 22
    TYPE_16SC2 = 23
    TYPE_16SC3 = 24
    TYPE_16SC4 = 25
    TYPE_32SC1 = 26
    TYPE_32SC2 = 27
    TYPE_32SC3 = 28
    TYPE_32SC4 = 29
    TYPE_32FC1 = 30
    TYPE_32FC2 = 31
    TYPE_32FC3 = 32
    TYPE_32FC4 = 33
    TYPE_64FC1 = 34
    TYPE_64FC2 = 35
    TYPE_64FC3 = 36
    TYPE_64FC4 = 37
    BAYER_RGGB8 = 38
    BAYER_BGGR8 = 39
    BAYER_GBRG8 = 40
    BAYER_GRBG8 = 41
    BAYER_RGGB16 = 42
    BAYER_BGGR16 = 43
    BAYER_GBRG16 = 44
    BAYER_GRBG16 = 45
    YUV422 = 46


class Message_2DImage(BaseModel):
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
    width: int = Field(default=0)
    height: int = Field(default=0)
    data: bytes = Field(default=b"")
    encoding: str = Field(default="")  # enum PixelFormat
    base64Data: str = Field(default="")
    fx: float = Field(default=0.0)
    fy: float = Field(default=0.0)
    cx: float = Field(default=0.0)
    cy: float = Field(default=0.0)


class Message_ScanRangePoint(BaseModel):
    """
    表示扫描范围点信息的模型类。

    Attributes:
        x (float): 扫描范围点的x坐标，默认值为0.0。
        y (float): 扫描范围点的y坐标，默认值为0.0。
    """
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)


class Message_DepthCameraInstallInfo(BaseModel):
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
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    roll: float = Field(default=0.0)
    pitch: float = Field(default=0.0)
    yaw: float = Field(default=0.0)


class Message_DepthCameraDeviceInfo(BaseModel):
    """
    表示深度相机设备信息的模型。

    Attributes:
        device_name (str): 设备名称，默认为空字符串。
        points (typing.List[Message_ScanRangePoint]): 点的列表，默认为空列表。
    """
    device_name: str = Field(default="")
    points: typing.List[Message_ScanRangePoint] = Field(default_factory=list)


class Message_DepthCameraPoint(BaseModel):
    """
    表示深度相机点的模型。

    Attributes:
        x (float): x 坐标，默认为 0.0。
        y (float): y 坐标，默认为 0.0。
        z (float): z 坐标，默认为 0.0。
        label (int): 点的标签，用于标识不同类型，如障碍洞为 1，物为 1，人为 2，默认为 0。
    """
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    label: int = Field(default=0)  # 障碍洞 1，物 1，人 2


class Message_DepthCameraCloud(BaseModel):
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
    header: typing.Optional[Message_Header] = None
    device_name: str = Field(default="")
    cloud: typing.List[Message_DepthCameraPoint] = Field(default_factory=list)
    install: typing.Optional[Message_DepthCameraInstallInfo] = None
    device: typing.Optional[Message_DepthCameraDeviceInfo] = None
    image: typing.Optional[Message_2DImage] = None
    cloud_voxel: float = Field(default=0.0)


class Message_AllCameraCloud(BaseModel):
    """
    表示所有相机点云的模型。

    Attributes:
        allcloud (typing.List[Message_DepthCameraCloud]): 所有深度相机点云的列表，默认为空列表。
    """
    allcloud: typing.List[Message_DepthCameraCloud] = Field(default_factory=list)
