# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_header_p2p import Message_Header
from enum import IntEnum
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class PixelFormat(IntEnum):
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
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)


class Message_DepthCameraInstallInfo(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    roll: float = Field(default=0.0)
    pitch: float = Field(default=0.0)
    yaw: float = Field(default=0.0)


class Message_DepthCameraDeviceInfo(BaseModel):
    device_name: str = Field(default="")
    point: typing.List[Message_ScanRangePoint] = Field(default_factory=list)


class Message_DepthCameraPoint(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    label: int = Field(default=0)  # hole 1,obstacle 1 , person 2


class Message_DepthCameraCloud(BaseModel):
    header: typing.Optional[Message_Header] = None
    device_name: str = Field(default="")
    cloud: typing.List[Message_DepthCameraPoint] = Field(default_factory=list)
    install: typing.Optional[Message_DepthCameraInstallInfo] = None
    device: typing.Optional[Message_DepthCameraDeviceInfo] = None
    image: typing.Optional[Message_2DImage] = None
    cloud_voxel: float = Field(default=0.0)


class Message_AllCameraCloud(BaseModel):
    allcloud: typing.List[Message_DepthCameraCloud] = Field(default_factory=list)
