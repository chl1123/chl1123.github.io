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


class Message_LaserInstallInfo(BaseModel):
    """表示激光安装信息的模型。

    Attributes:
        x (float): 激光安装位置的X坐标，默认值为0.0。
        y (float): 激光安装位置的Y坐标，默认值为0.0。
        z (float): 激光安装位置的Z坐标，默认值为0.0。
        yaw (float): 激光安装的偏航角，默认值为0.0。
        upside (bool): 激光是否倒置安装，默认值为False。
    """
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    upside: bool = Field(default=False)


class Message_LaserDeviceInfo(BaseModel):
    """表示激光设备信息的模型。

    Attributes:
        device_name (str): 激光设备的名称，默认值为空字符串。
        min_range (float): 激光设备的最小探测范围，默认值为0.0。
        max_range (float): 激光设备的最大探测范围，默认值为0.0。
        min_angle (float): 激光设备的最小探测角度，默认值为0.0。
        max_angle (float): 激光设备的最大探测角度，默认值为0.0。
        real_step (float): 激光设备的实际扫描步长，默认值为0.0。
        pub_step (float): 激光设备的发布扫描步长，默认值为0.0。
        time_increment (float): 激光设备的时间增量，默认值为0.0。
        scan_freq (float): 激光设备的扫描频率，默认值为0.0。
        id (int): 激光设备的ID，默认值为0。
        isClockWise (bool): 激光设备是否为顺时针扫描，默认值为False。
    """
    device_name: str = Field(default="")
    min_range: float = Field(default=0.0)
    max_range: float = Field(default=0.0)
    min_angle: float = Field(default=0.0)
    max_angle: float = Field(default=0.0)
    real_step: float = Field(default=0.0)
    pub_step: float = Field(default=0.0)
    time_increment: float = Field(default=0.0)
    scan_freq: float = Field(default=0.0)
    id: int = Field(default=0)
    isClockWise: bool = Field(default=False)


class Message_LaserBeam(BaseModel):
    """激光束信息模型类

    Attributes:
        header (typing.Optional[Message_Header]): 激光束的消息头，可选字段，默认值为None。
        angle (float): 激光束的角度，默认值为0.0。
        dist (float): 激光束的距离，默认值为0.0。
        x (float): 激光束在X轴的坐标，默认值为0.0。
        y (float): 激光束在Y轴的坐标，默认值为0.0。
        rssi (float): 激光束的接收信号强度指示，默认值为0.0。
        valid (bool): 激光束是否有效，默认值为False。
        is_virtual (bool): 激光束是否为虚拟的，默认值为False。
        is_obstacle (bool): 激光束是否表示障碍物，默认值为False。
    """
    header: typing.Optional[Message_Header] = None
    angle: float = Field(default=0.0)
    dist: float = Field(default=0.0)
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    rssi: float = Field(default=0.0)
    valid: bool = Field(default=False)
    is_virtual: bool = Field(default=False)
    is_obstacle: bool = Field(default=False)


class Message_LaserBeam3D(BaseModel):
    """3D激光束信息模型类

    Attributes:
        id (int): 3D激光束的ID，默认值为0。
        x (float): 3D激光束在X轴的坐标，默认值为0.0。
        y (float): 3D激光束在Y轴的坐标，默认值为0.0。
        z (float): 3D激光束在Z轴的坐标，默认值为0.0。
        intensity (int): 3D激光束的强度，默认值为0。
        ring (int): 3D激光束所在的环编号，默认值为0。
        timestamp (int): 3D激光束的时间戳，默认值为0。
        data (bytes): 3D激光束的数据，默认值为空字节串。
        firstAzimuth (float): 3D激光束的第一个方位角，默认值为0.0。
        secondAzimuth (float): 3D激光束的第二个方位角，默认值为0.0。
    """
    id: int = Field(default=0)
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    intensity: int = Field(default=0)
    ring: int = Field(default=0)
    timestamp: int = Field(default=0)
    data: bytes = Field(default=b"")
    firstAzimuth: float = Field(default=0.0)
    secondAzimuth: float = Field(default=0.0)


class Message_Laser(BaseModel):
    """表示激光信息的模型。

    Attributes:
        device_info (typing.Optional[Message_LaserDeviceInfo]): 激光设备的信息，可选字段，默认值为None。
        install_info (typing.Optional[Message_LaserInstallInfo]): 激光安装信息，可选字段，默认值为None。
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认值为None。
        beams (typing.List[Message_LaserBeam]): 激光束列表，默认值为空列表。
        use_forLoc (bool): 是否用于定位，默认值为False。
        beams_not_use (typing.List[Message_LaserBeam]): 未使用的激光束列表，默认值为空列表。
        is3DLocalization (bool): 是否进行3D定位，默认值为False。
        use_forBinDetection (bool): 是否用于箱子检测，默认值为False。
    """
    device_info: typing.Optional[Message_LaserDeviceInfo] = None
    install_info: typing.Optional[Message_LaserInstallInfo] = None
    header: typing.Optional[Message_Header] = None
    beams: typing.List[Message_LaserBeam] = Field(default_factory=list)
    use_forLoc: bool = Field(default=False)
    beams_not_use: typing.List[Message_LaserBeam] = Field(default_factory=list)
    is3DLocalization: bool = Field(default=False)
    use_forBinDetection: bool = Field(default=False)


class Message_Laser3D(BaseModel):
    """3D激光信息模型类

    Attributes:
        device_info (typing.Optional[Message_LaserDeviceInfo]): 激光设备的信息，可选字段，默认值为None。
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认值为None。
        beams3D (typing.List[Message_LaserBeam3D]): 3D激光束列表，默认值为空列表。
        use_forLoc (bool): 是否用于定位，默认值为False。
        beams_not_use (typing.List[Message_LaserBeam]): 未使用的激光束列表，默认值为空列表。
        is3DLocalization (bool): 是否进行3D定位，默认值为False。
        lasertype (int): 激光类型，默认值为0。1表示robosense 16，2表示robosense helios，3表示velodyne 16。
        factor (float): 因子，默认值为0.0。
        azimuthcorrection (typing.List[float]): 方位角校正值列表，默认值为空列表。
        verticalcorrection (typing.List[float]): 垂直校正值列表，默认值为空列表。
        is3DobstacleDetection (bool): 是否进行3D障碍物检测，默认值为False。
    """
    device_info: typing.Optional[Message_LaserDeviceInfo] = None
    header: typing.Optional[Message_Header] = None
    beams3D: typing.List[Message_LaserBeam3D] = Field(default_factory=list)
    use_forLoc: bool = Field(default=False)
    beams_not_use: typing.List[Message_LaserBeam] = Field(default_factory=list)
    is3DLocalization: bool = Field(default=False)
    lasertype: int = Field(default=0)
    factor: float = Field(default=0.0)
    azimuthcorrection: typing.List[float] = Field(default_factory=list)
    verticalcorrection: typing.List[float] = Field(default_factory=list)
    is3DobstacleDetection: bool = Field(default=False)


class Message_AllLasers(BaseModel):
    """包含多个激光信息的模型类

    Attributes:
        laser (typing.List[Message_Laser]): 激光信息列表，包含多个Message_Laser对象，默认值为空列表。
    """
    laser: typing.List[Message_Laser] = Field(default_factory=list)


class Message_AllLasers3D(BaseModel):
    """包含多个3D激光信息的模型类

    Attributes:
        lasers3d (typing.List[Message_Laser3D]): 3D激光信息列表，包含多个Message_Laser3D对象，默认值为空列表。
    """
    lasers3d: typing.List[Message_Laser3D] = Field(default_factory=list)


class Message_LaserClusterFeature(BaseModel):
    avg_rssi: float = Field(default=0.0)
    num_points: float = Field(default=0.0)
    std: float = Field(default=0.0)
    avg_median_dev: float = Field(default=0.0)
    prev_jump: float = Field(default=0.0)
    next_jump: float = Field(default=0.0)
    width: float = Field(default=0.0)
    linearity: float = Field(default=0.0)
    circularity: float = Field(default=0.0)
    radius: float = Field(default=0.0)
    boundary_length: float = Field(default=0.0)
    ang_diff: float = Field(default=0.0)
    mean_curvature: float = Field(default=0.0)
    boundary_regularity: float = Field(default=0.0)
    iav: float = Field(default=0.0)
    std_iav: float = Field(default=0.0)


class Message_LaserCluster(BaseModel):
    device_info: typing.Optional[Message_LaserDeviceInfo] = None
    install_info: typing.Optional[Message_LaserInstallInfo] = None
    header: typing.Optional[Message_Header] = None
    beams: typing.List[Message_LaserBeam] = Field(default_factory=list)
    features: typing.Optional[Message_LaserClusterFeature] = None


class Message_LaserSegResult(BaseModel):
    header: typing.Optional[Message_Header] = None
    clusters: typing.List[Message_LaserCluster] = Field(default_factory=list)


class Message_Grid(BaseModel):
    value: int = Field(default=0)
    x: int = Field(default=0)
    y: int = Field(default=0)


class Message_CostMap(BaseModel):
    resolution: int = Field(default=0)
    grids: typing.List[Message_Grid] = Field(default_factory=list)


class Message_SensorPoint(BaseModel):
    x: float = Field(default=0.0)  # 世界坐标x
    y: float = Field(default=0.0)  # 世界坐标y
    z: float = Field(default=0.0)  # 世界坐标z
    is_obstacle: bool = Field(default=False)  # 是否是障碍物
    rssi: float = Field(default=0.0)  # 如果是激光则为rssi，其他为-1
    tag: str = Field(default="")  # 是否是行人 "person"


class Message_SensorPointCluster(BaseModel):
    class Type(IntEnum):
        Ultrasonic = 0
        Laser = 1
        Fallingdown = 2
        Collision = 3
        Infrared = 4
        VirtualPoint = 5
        APIObstacle = 6
        ReservedPoint = 7
        DiUltrasonic = 8
        DepthCamera = 9
        ReservedDepthCamera = 10
        DistanceNode = 11
        ADCollision = 12

    header: typing.Optional[Message_Header] = None  # 各种类型的数据的时间戳
    type: "Message_SensorPointCluster.Type" = Field(default=0)  # 点云数据的类型
    id: str = Field(
        default=""
    )  # 点云类型的id号，如果是激光的话，为index，APIObstacle则为障碍物名称
    point: typing.List[Message_SensorPoint] = Field(default_factory=list)


class Message_SensorPointCloud(BaseModel):
    global_cluster: typing.List[Message_SensorPointCluster] = Field(
        default_factory=list
    )
    local_cluster: typing.List[Message_SensorPointCluster] = Field(default_factory=list)


class Message_LaserPoint(BaseModel):
    class Type(IntEnum):
        Ultrasonic = 0
        Laser = 1
        Fallingdown = 2
        Collision = 3
        Infrared = 4
        VirtualPoint = 5
        APIObstacle = 6

    x: float = Field(default=0.0)  # 世界坐标x
    y: float = Field(default=0.0)  # 世界坐标y
    z: float = Field(default=0.0)  # 世界坐标z
    type: "Message_LaserPoint.Type" = Field(default=0)  # 点云数据的类型
    id: str = Field(
        default=""
    )  # 点云类型的id号，如果是激光的话，为index，APIObstacle则为障碍物名称
    is_obstacle: bool = Field(default=False)  # 是否是障碍物
    rssi: float = Field(default=0.0)  # 如果是激光则为rssi，其他为-1
    data_nsec: int = Field(default=0)  # 这个点的时间


class Message_LaserPointCloud(BaseModel):
    header: typing.Optional[Message_Header] = None
    point: typing.List[Message_LaserPoint] = Field(default_factory=list)
