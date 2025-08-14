from syspy.config import rbk_version
from .navigation import NavSpeedInterface, NavigationInterface, NavStatusInterface
from .odometer import OdometerInterface

from syspy.config import rbk_version
if rbk_version == 3:
    from syspy.v3.odometer import OdometerV3
    Odometer: OdometerInterface = OdometerV3()

    from syspy.v3.navigation import NavigationV3, NavStatusV3, NavSpeedV3
    Navigation: NavigationInterface = NavigationV3()
    NavStatus: NavStatusInterface = NavStatusV3()
    NavSpeed: NavSpeedInterface = NavSpeedV3()

elif rbk_version == 4:
    from syspy.v4.odometer import OdometerV4
    Odometer: OdometerInterface = OdometerV4()

    from syspy.v4.navigation import NavigationV4, NavStatusV4, NavSpeedV4
    Navigation: NavigationInterface = NavigationV4()
    NavStatus: NavStatusInterface = NavStatusV4()
    NavSpeed: NavSpeedInterface = NavSpeedV4()
else:
    raise ValueError(f"Unsupported RBK version: {rbk_version}")

# from typeguard import install_import_hook
# install_import_hook('syspy')

from .battery import Battery
from .camera import Camera
from .charger import Charger
from .controller import Controller
from .dio import Di, Do
from .distance import Distance
from .laser import Laser
from .led import Led
from .lib.abnormal import Abnormal
from .lib.can_frame import Can
from .lib.logger import Logger
from .lib.module import ScriptStatus, Module
from .lib.net_protocol import NetProtocol
from .lib.robot_param import RobotParam
from .lib.trace import Trace
from .loc import Loc
from .magnetic import Magnetic
from .map import Map
from .motor import Motor

from .pgv import Pgv
from .recognize import Recognize
from .rfid import RFID
from .sound import Sound
from .utils.param_server import ParamServer

__all__ = [
    "rbk_version",
    "Abnormal",
    "Trace",
    "Logger",
    "NetProtocol",
    "Can",
    "RobotParam",
    "ScriptStatus",
    "Module",
    "ParamServer",
    "Battery",
    "Camera",
    "Charger",
    "Controller",
    "Di",
    "Do",
    "Distance",
    "Laser",
    "Led",
    "Loc",
    "Magnetic",
    "Map",
    "Motor",
    "Navigation",
    "NavStatus",
    "NavSpeed",
    "Odometer",
    "Pgv",
    "RFID",
    "Recognize",
    "Sound",
]  # 列出所有公共模块
