# AUTO-GENERATED - do not edit by hand.
# Source: src/channel.json
# Run ./registrygen.py to regenerate.

from types import SimpleNamespace


# namespace system: 系统状态
class system:
    TOPIC_UUID = '/System/UUID'
    TOPIC_ROBOT_STATUS = '/System/RobotStatus'
    TOPIC_MODULE_VERSION = '/System/ModuleVersion'
    TOPIC_APP_STATUS = '/System/AppStatus'
    TOPIC_PROC_STATUS = '/System/ProcStatus'
    TOPIC_DEBUG_INFO = '/System/DebugInfo'
    TOPIC_ABNORMAL = '/System/Abnormal'
    TOPIC_ABNORMALS = '/System/Abnormals'


# namespace param: 参数
class param:
    TOPIC_DEVICE_MD5 = '/param/deviceMd5'
    TOPIC_APP_MD5 = '/param/appMd5'


# namespace smap: 地图
class smap:
    TOPIC_NAME = '/SMAP/CurrentName'
    TOPIC_INFO = '/SMAP/CurrentInfo'
    TOPIC_MAP_2D = '/SMAP/Map2D'
    TOPIC_MAP_3D = '/SMAP/Map3D'
    TOPIC_SUB_MAP_STATUS = '/SMAP/SubMapStatus'


# namespace urdf: 机器人模型
class urdf:
    TOPIC_NAME = '/URDF/CurrentName'
    TOPIC_URDF = '/URDF/URDF'


# namespace transform: 位姿变换
class transform:
    TOPIC_FRAME = '/TF/Frame'
    TOPIC_STATIC = '/TF/FramesStatic'
    TOPIC_DYNAMIC = '/TF/FramesChange'


# namespace calibration: 标定
class calibration:
    TOPIC_INFO = '/Calib/Calib'
    TOPIC_CALIB_PROPERTY = '/Calib/CalibProperty'


# namespace system_sensor: 系统传感器
class system_sensor:
    TOPIC_IMU = '/SystemSensor/IMU'
    TOPIC_DI = '/SystemSensor/DI'
    TOPIC_DO = '/SystemSensor/DO'
    TOPIC_CONTROLLER = '/SystemSensor/Controller'
    TOPIC_SAFE_MODULE = '/SystemSensor/SafeModule'


# namespace device: 设备话题前缀
class device:
    TOPIC_PREFIX_MOTOR_INFO = '/MotorInfo/'
    TOPIC_PREFIX_MOTOR_CMD = '/MotorCmd/'
    TOPIC_PREFIX_LASER_INFO = '/LaserInfo/'
    TOPIC_PREFIX_LASER_2D = '/Laser2D/'
    TOPIC_PREFIX_LASER_3D = '/Laser3D/'
    TOPIC_PREFIX_LASER_IMU = '/LaserIMU/'
    TOPIC_PREFIX_CAMERA_DATA = '/CameraData/'
    TOPIC_PREFIX_CAMERA_DATA_RGBD = '/CameraDataRGBD/'
    TOPIC_PREFIX_GRIP_INFO = '/GripInfo/'
    TOPIC_PREFIX_GRIP_CMD = '/GripCmd/'
    TOPIC_PREFIX_ETHERCAT_EXT_INFO = '/EtherCATExtendInfo/'
    TOPIC_PREFIX_ETHERCAT_EXT_CMD = '/EtherCATExtendCmd/'
    TOPIC_PREFIX_ETHERCAT_BUS_CMD = '/EtherCATBus/Cmd/'
    TOPIC_PREFIX_ETHERCAT_BUS_FEEDBACK = '/EtherCATBus/Feedback/'
    TOPIC_PREFIX_RFID = '/RFID/'
    TOPIC_PREFIX_MAGNETIC = '/Magnetic/'
    TOPIC_PREFIX_CODESCANNER = '/CodeScanner/'
    TOPIC_PREFIX_DISTANCE_SENSOR = '/DistanceSensor/'
    TOPIC_PREFIX_HANDLE_INTENT = '/HandleIntent/'
    TOPIC_PREFIX_TILTSENSOR = '/TiltSensor/'
    TOPIC_PREFIX_CAN_FRAME_TX = '/CANFrame/TX/'
    TOPIC_PREFIX_CAN_FRAME_RX = '/CANFrame/RX/'
    TOPIC_PREFIX_GNSS = '/GNSS/'
    TOPIC_PREFIX_BATTERY = '/BatteryInfo/'
    TOPIC_FASTPLCTOSRC = '/PLC/Fast'
    TOPIC_STDPLCTOSRC = '/PLC/Standard'
    TOPIC_DTU_RX = '/DTU/RX'
    TOPIC_DTU_TX = '/DTU/TX'
    TOPIC_DTU_STATUS = '/DTU/Status'
    TOPIC_BATTERY = '/BatteryInfos'


# namespace robot_state: 机器人状态
class robot_state:
    TOPIC_JOINT_STATES = '/JointStates'
    TOPIC_ROBOT_INFO = '/RobotInfo'
    TOPIC_ROBOT_STATE = '/RobotState'


# namespace charger: 充电状态
class charger:
    TOPIC_STATUS = '/Charger/Status'


# namespace robot_sim: 仿真
class robot_sim:
    TOPIC_PREFIX_JOINT_CMD = '/JointCmd/'
    TOPIC_PREFIX_JOINT_STATE = '/JointState/'


# namespace localization: 定位
class localization:
    TOPIC_LOCALIZATION_INFO = '/Localization/Info'
    TOPIC_LOCALIZATION_LOC_STATE = '/Localization/LocState'
    TOPIC_MAPLOGGER_SCAN_MAP_STATUS = '/MapLogger/ScanMapStatus'
    TOPIC_ODOMETER = '/Localization/Odometer'
    TOPIC_ODOMETER_EKF = '/Localization/OdometerEKF'
    TOPIC_LOCALIZATION_VIEW = '/Localization/View/'


# namespace navigation: 导航
class navigation:
    TOPIC_MOVE_STATUS = '/Navigation/MoveStatus'
    TOPIC_BYPASS_MATES = '/Navigation/BypassMates'
    TOPIC_BYPASS_ROBOT_STATUS = '/Navigation/BypassRobotStatus'
    TOPIC_NAV_PATH = '/Navigation/NavPath'
    TOPIC_MULTI_NAV_PATH = '/Navigation/MultiNavPath'
    TOPIC_NAV_SPEED = '/Navigation/NavSpeed'
    TOPIC_POINT_CLOUD = '/Navigation/PointCloud'
    TOPIC_API_OBSTACLE = '/Navigation/ApiObstacle'
    TOPIC_VDA_STATE = '/Navigation/Vda5050State'
    TOPIC_VDA_ORDER = '/Navigation/Vda5050Order'
    TOPIC_VDA_INSTANCE_ORDER = '/Navigation/Vda5050InstanceOrder'
    TOPIC_MANUAL_SPEED = '/Navigation/ManualSpeed'
    TOPIC_API_MANUAL_SPEED = '/API/ManualSpeed'
    TOPIC_FORK = '/Navigation/Fork'
    TOPIC_JACK = '/Navigation/Jack'
    TOPIC_SLIP = '/Navigation/Slip'
    TOPIC_ESDF_OBSTACLES = '/Navigation/ESDFObstacles'
    TOPIC_ESDF_SLICE = '/Navigation/ESDFSlice'
    TOPIC_COSTMAP_2D = '/Navigation/Costmap2D'
    TOPIC_GLOBAL_STATIC_COSTMAP = '/Navigation/GlobalStaticCostmap'
    TOPIC_MPPI_TRAJECTORY = '/Navigation/MppiTrajectory'
    TOPIC_FAST_LOCAL_BSPLINE = '/Navigation/FastLocalBspline'
    TOPIC_TASK_BSPLINE = '/Navigation/TaskBspline'
    TOPIC_FAST_LOCAL_CANDIDATE_BSPLINE = '/Navigation/FastLocalCandidatePaths'
    TOPIC_LOCAL_PLANNER_STATUS = '/Navigation/LocalPlannerStatus'
    TOPIC_MPC_CONTROLLER_STATUS = '/Navigation/MpcControllerStatus'
    TOPIC_MPC_VEL_CMD_RAW = '/Navigation/MpcVelCmdRaw'
    TOPIC_MPC_PREDICTED_REF_PATH = '/Navigation/MpcPredictedRefPath'
    TOPIC_ROUTE_GEOMETRY = '/Navigation/RouteGeometry'
    TOPIC_MANUAL_VEL_CMD = '/Navigation/ManualVelCmd'
    TOPIC_NAV_VEL_CMD_SMOOTH = '/Navigation/NavVelCmdSmooth'
    TOPIC_STEER_ALIGN_REQUEST = '/Navigation/SteerAlignment/Request'
    TOPIC_STEER_ALIGN_STATUS = '/Navigation/SteerAlignment/Status'
    TOPIC_MPC_CONTROL_LEASE = '/Navigation/MpcControl/Lease'
    TOPIC_E2E_WAYPOINTS = '/Navigation/E2EWaypoints'


# namespace chassis_control: 底盘控制
class chassis_control:
    TOPIC_CHASSIS_CONTROL_MANUAL = '/ChassisControl/ManualSpeed'


# namespace arm_planning: 机械臂规划
class arm_planning:
    TOPIC_ARMPLANNING_CONTROL = '/ArmplanningControl'


# namespace robot_control: 机器人控制
class robot_control:
    TOPIC_LOCK = '/Control/Lock'
    TOPIC_SIM_STATE = '/RobotControl/SimState'
    TOPIC_WBC_COMMAND = '/RobotControl/WbcCommand'
    TOPIC_WBC_EE_COMMAND = '/RobotControl/WbcEECommand'
    TOPIC_WBC_DEBUG_TF = '/RobotControl/WbcDebugTF'
    TOPIC_WBC_COLLISION_WARNING = '/RobotControl/WbcCollisionWarning'
    TOPIC_WBC_ESDF_GRADIENT_JSON = '/RobotControl/WbcEsdfGradientJson'


# namespace sensorfuser: 传感器融合
class sensorfuser:
    TOPIC_SENSOR_FUSER = '/SensorFuser'
    TOPIC_SENSOR_FUSER_COLLISION = '/SensorFuser/Collision'
    TOPIC_SENSOR_FUSER_USER_OBJECT = '/SensorFuser/UserObject'


# namespace recognition: 识别
class recognition:
    TOPIC_RECOGNITION_RECOG_RES = '/Recognition/RecogRes'


# namespace script: 脚本
class script:
    TOPIC_DATA = '/Script/Data'


# namespace behave: 音频
class behave:
    TOPIC_BEHAVE_SOUND = '/behave/sound'


# namespace ros2: ROS2 兼容话题
class ros2:
    TOPIC_TRANSFORM_STATIC = '/tf_static'
    TOPIC_TRANSFORM_DYNAMIC = '/tf'
    TOPIC_LASER_3D_POINT_CLOUD = '/point_cloud'
    TOPIC_LASER_2D_SCAN = '/laser_scan'
    TOPIC_CAMERA_RGB_IMAGE = '/rgb'
    TOPIC_CAMERA_DEPTH_IMAGE = '/depth'


registry = SimpleNamespace(
    system=system,
    param=param,
    smap=smap,
    urdf=urdf,
    transform=transform,
    calibration=calibration,
    system_sensor=system_sensor,
    device=device,
    robot_state=robot_state,
    charger=charger,
    robot_sim=robot_sim,
    localization=localization,
    navigation=navigation,
    chassis_control=chassis_control,
    arm_planning=arm_planning,
    robot_control=robot_control,
    sensorfuser=sensorfuser,
    recognition=recognition,
    script=script,
    behave=behave,
    ros2=ros2,
)
