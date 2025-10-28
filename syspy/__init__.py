from syspy.config import RBK_VERSION, RBK_FULL_VERSION
from .navigation import NavSpeedInterface, NavigationInterface, NavStatusInterface
from .odometer import OdometerInterface

if RBK_VERSION == 3:
    from syspy.v3.odometer import OdometerV3
    Odometer: OdometerInterface = OdometerV3()

    from syspy.v3.navigation import NavigationV3, NavStatusV3, NavSpeedV3
    Navigation: NavigationInterface = NavigationV3()
    NavStatus: NavStatusInterface = NavStatusV3()
    NavSpeed: NavSpeedInterface = NavSpeedV3()

elif RBK_VERSION == 4:
    from syspy.v4.odometer import OdometerV4
    Odometer: OdometerInterface = OdometerV4()

    from syspy.v4.navigation import NavigationV4, NavStatusV4, NavSpeedV4
    Navigation: NavigationInterface = NavigationV4()
    NavStatus: NavStatusInterface = NavStatusV4()
    NavSpeed: NavSpeedInterface = NavSpeedV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

# from typeguard import install_import_hook
# install_import_hook('syspy')
from .lib.plyvel_db import LevelDB
from .bin import Bin, Container
from .lib.abnormal import Abnormal
from .lib.can_frame import Can
from .lib.logger import Logger
from .lib.robot_param import RobotParam
from .lib.module import ScriptStatus, Module, ModuleBase
from .lib.net_protocol import NetProtocol
from .lib.trace import Trace
from .utils.param_server import ParamServer, ScriptParam

from .battery import Battery

from .camera import Camera
from .charger import Charger
from .controller import Controller
from .dio import Di, Do
from .distance import Distance
from .laser import Laser, Laser3D
from .led import Led
from .loc import Loc
from .magnetic import Magnetic
from .map import Map
from .motor import Motor
from .code_scanner import CodeScanner
from .recognize import Recognize
from .rfid import RFID
from .sound import Sound


__all__ = [
    "RBK_VERSION",
    "RBK_FULL_VERSION",
    "Abnormal",
    "Bin",
    "Container",
    "Trace",
    "Logger",
    "NetProtocol",
    "Can",
    "RobotParam",
    "ScriptStatus",
    "Module",
    "ModuleBase",
    "ParamServer",
    "ScriptParam",
    "Battery",
    "Camera",
    "Charger",
    "Controller",
    "Di",
    "Do",
    "Distance",
    "Laser",
    "Laser3D",
    "Led",
    "Loc",
    "Magnetic",
    "Map",
    "Motor",
    "Navigation",
    "NavStatus",
    "NavSpeed",
    "Odometer",
    "CodeScanner",
    "RFID",
    "Recognize",
    "Sound",
]  # 列出所有公共模块
