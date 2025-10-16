from .message.CanFrame_pb2 import CanFrame
from .message.message_battery_pb2 import msgBattery
from .message.message_bin_pb2 import msgBins, msgBin
from .message.message_controller_pb2 import msgController
from .message.message_depthcamera_pb2 import *
from .message.message_distancesensor_pb2 import *
from .message.message_dmx512_pb2 import msgDmx512
from .message.message_io_pb2 import *
from .message.message_laser_pb2 import *
from .message.message_localization_pb2 import msgLocalization
from .message.message_magnetic_pb2 import msgMagnetic, msgMagneticNode
from .message.message_motorinfos_pb2 import *
from .message.message_movetask_pb2 import msgMoveStatus
from .message.message_navigation_pb2 import *
from .message.message_odometer_pb2 import msgOdometer
from .message.message_codescanner_pb2 import *
from .message.message_rfid_pb2 import msgRFID, msgRFIDNode
from .message.message_script_pb2 import msgScript
from .message.message_sound_pb2 import msgSound

__all__ = [
    "CanFrame",
    "msgBattery",
    "msgBins",
    "msgBin",

    "msgController",

    "msgDistanceSensor",
    "msgDistanceNode",

    "msgDmx512",
    "msgDI",
    "msgDINode",
    "msgDO",
    "msgDONode",

    "msgMotorInfo",

    "msgAllLasers",
    "msgAllLasers3D",
    "msgLaser3D",
    "msgLaser",
    "msgLaserDeviceInfo",
    "msgLaserBeam3D",
    "msgLaserBeam",

    "msgLocalization",
    "msgMoveStatus",

    "msgMagnetic",
    "msgMagneticNode",

    "msgNavSpeed",
    "msgMotorCmd",

    "msgOdometer",
    "msgCodeScanner",
    "msgCodeScannerDMT",
    "msgCodeScannerInfo",

    "msgRFID",
    "msgRFIDNode",

    "msgSound",
    "msgScript"
]  # 列出所有公共模块
