from syspy.config import RBK_VERSION, RBK_FULL_VERSION, RBK_SIMULATION
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "../generic"))
sys.path.insert(0, os.path.join(current_dir, "../tasks"))
sys.path.insert(0, os.path.join(current_dir, "../generic/common"))
sys.path.insert(0, os.path.join(current_dir, "../tasks/common"))
if RBK_VERSION == 3:
    sys.path.insert(0, os.path.join(current_dir, "../generic/v3"))
    sys.path.insert(0, os.path.join(current_dir, "../tasks/v3"))
elif RBK_VERSION == 4:
    sys.path.insert(0, os.path.join(current_dir, "../generic/v4"))
    sys.path.insert(0, os.path.join(current_dir, "../tasks/v4"))

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
from .utils import _TR
from .utils.param_server import ParamServer, ScriptParam
from .lib.robot import RobotParam, RobotError
from .lib.module import ScriptStatus, Module, ModuleBase
from .lib.net_protocol import NetProtocol
from .lib.trace import Trace

from .battery import Battery
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
from .rfid import Rfid
from .sound import Sound
from .sim import is_simulation, sim_only


__all__ = [
    "RBK_VERSION",
    "RBK_FULL_VERSION",
    "RBK_SIMULATION",
    "LevelDB",
    "Abnormal",
    "Bin",
    "Container",
    "Trace",
    "Logger",
    "NetProtocol",
    "Can",
    "RobotParam",
    "RobotError",
    "ScriptStatus",
    "Module",
    "ModuleBase",
    "_TR",
    "ParamServer",
    "ScriptParam",
    "Battery",
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
    "Rfid",
    "Recognize",
    "Sound",
    "is_simulation",
    "sim_only",
]  # 列出所有公共模块
