from . import message_header_pb2 as _message_header_pb2
from google.protobuf import wrappers_pb2 as _wrappers_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgCSPCmd(_message.Message):
    __slots__ = ["dec", "maxVelocity", "position", "torqueOffset"]
    DEC_FIELD_NUMBER: _ClassVar[int]
    MAXVELOCITY_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    TORQUEOFFSET_FIELD_NUMBER: _ClassVar[int]
    dec: _wrappers_pb2.FloatValue
    maxVelocity: _wrappers_pb2.FloatValue
    position: float
    torqueOffset: _wrappers_pb2.FloatValue
    def __init__(self, position: _Optional[float] = ..., torqueOffset: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., maxVelocity: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., dec: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...

class msgCSTCmd(_message.Message):
    __slots__ = ["maxTorque", "torque", "torqueOffset"]
    MAXTORQUE_FIELD_NUMBER: _ClassVar[int]
    TORQUEOFFSET_FIELD_NUMBER: _ClassVar[int]
    TORQUE_FIELD_NUMBER: _ClassVar[int]
    maxTorque: _wrappers_pb2.FloatValue
    torque: float
    torqueOffset: _wrappers_pb2.FloatValue
    def __init__(self, torque: _Optional[float] = ..., torqueOffset: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., maxTorque: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...

class msgCSVCmd(_message.Message):
    __slots__ = ["dec", "maxVelocity", "velocity"]
    DEC_FIELD_NUMBER: _ClassVar[int]
    MAXVELOCITY_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    dec: _wrappers_pb2.FloatValue
    maxVelocity: _wrappers_pb2.FloatValue
    velocity: float
    def __init__(self, velocity: _Optional[float] = ..., maxVelocity: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., dec: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...

class msgDOCmd(_message.Message):
    __slots__ = ["ioCmd"]
    class cmd(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    IOCMD_FIELD_NUMBER: _ClassVar[int]
    cmdNone: msgDOCmd.cmd
    ioCmd: msgDOCmd.cmd
    stop: msgDOCmd.cmd
    toNegative: msgDOCmd.cmd
    toPositive: msgDOCmd.cmd
    def __init__(self, ioCmd: _Optional[_Union[msgDOCmd.cmd, str]] = ...) -> None: ...

class msgHomingCmd(_message.Message):
    __slots__ = ["homeOffset", "homingAcceleration", "homingVelocities", "method"]
    HOMEOFFSET_FIELD_NUMBER: _ClassVar[int]
    HOMINGACCELERATION_FIELD_NUMBER: _ClassVar[int]
    HOMINGVELOCITIES_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    homeOffset: _wrappers_pb2.FloatValue
    homingAcceleration: _wrappers_pb2.FloatValue
    homingVelocities: _containers.RepeatedScalarFieldContainer[float]
    method: int
    def __init__(self, method: _Optional[int] = ..., homeOffset: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., homingVelocities: _Optional[_Iterable[float]] = ..., homingAcceleration: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...

class msgMITCmd(_message.Message):
    __slots__ = ["kd", "kp", "position", "torque", "velocity"]
    KD_FIELD_NUMBER: _ClassVar[int]
    KP_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    TORQUE_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    kd: _wrappers_pb2.FloatValue
    kp: _wrappers_pb2.FloatValue
    position: float
    torque: float
    velocity: float
    def __init__(self, kp: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., kd: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., position: _Optional[float] = ..., velocity: _Optional[float] = ..., torque: _Optional[float] = ...) -> None: ...

class msgMotorCmd(_message.Message):
    __slots__ = ["controlMode", "cspCmd", "cstCmd", "csvCmd", "doCmd", "header", "homingCmd", "mitCmd", "motorKey", "motorName", "profilePositionCmd", "profileTorqueCmd", "profileVelocityCmd"]
    class mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CONTROLMODE_FIELD_NUMBER: _ClassVar[int]
    CSP: msgMotorCmd.mode
    CSPCMD_FIELD_NUMBER: _ClassVar[int]
    CST: msgMotorCmd.mode
    CSTCMD_FIELD_NUMBER: _ClassVar[int]
    CSV: msgMotorCmd.mode
    CSVCMD_FIELD_NUMBER: _ClassVar[int]
    DISABLE: msgMotorCmd.mode
    DO: msgMotorCmd.mode
    DOCMD_FIELD_NUMBER: _ClassVar[int]
    ENABLE: msgMotorCmd.mode
    HEADER_FIELD_NUMBER: _ClassVar[int]
    HOMING: msgMotorCmd.mode
    HOMINGCMD_FIELD_NUMBER: _ClassVar[int]
    MIT: msgMotorCmd.mode
    MITCMD_FIELD_NUMBER: _ClassVar[int]
    MOTORKEY_FIELD_NUMBER: _ClassVar[int]
    MOTORNAME_FIELD_NUMBER: _ClassVar[int]
    PROFILEPOSITIONCMD_FIELD_NUMBER: _ClassVar[int]
    PROFILETORQUECMD_FIELD_NUMBER: _ClassVar[int]
    PROFILEVELOCITYCMD_FIELD_NUMBER: _ClassVar[int]
    PROFILE_POSITION: msgMotorCmd.mode
    PROFILE_TORQUE: msgMotorCmd.mode
    PROFILE_VELOCITY: msgMotorCmd.mode
    controlMode: msgMotorCmd.mode
    cspCmd: msgCSPCmd
    cstCmd: msgCSTCmd
    csvCmd: msgCSVCmd
    doCmd: msgDOCmd
    header: _message_header_pb2.msgHeader
    homingCmd: msgHomingCmd
    mitCmd: msgMITCmd
    motorKey: str
    motorName: str
    profilePositionCmd: msgProfilePositionCmd
    profileTorqueCmd: msgProfileTorqueCmd
    profileVelocityCmd: msgProfileVelocityCmd
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., controlMode: _Optional[_Union[msgMotorCmd.mode, str]] = ..., homingCmd: _Optional[_Union[msgHomingCmd, _Mapping]] = ..., profileVelocityCmd: _Optional[_Union[msgProfileVelocityCmd, _Mapping]] = ..., profilePositionCmd: _Optional[_Union[msgProfilePositionCmd, _Mapping]] = ..., cspCmd: _Optional[_Union[msgCSPCmd, _Mapping]] = ..., profileTorqueCmd: _Optional[_Union[msgProfileTorqueCmd, _Mapping]] = ..., cstCmd: _Optional[_Union[msgCSTCmd, _Mapping]] = ..., csvCmd: _Optional[_Union[msgCSVCmd, _Mapping]] = ..., mitCmd: _Optional[_Union[msgMITCmd, _Mapping]] = ..., doCmd: _Optional[_Union[msgDOCmd, _Mapping]] = ..., motorName: _Optional[str] = ..., motorKey: _Optional[str] = ...) -> None: ...

class msgProfilePositionCmd(_message.Message):
    __slots__ = ["acc", "dec", "maxVelocity", "position"]
    ACC_FIELD_NUMBER: _ClassVar[int]
    DEC_FIELD_NUMBER: _ClassVar[int]
    MAXVELOCITY_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    acc: _wrappers_pb2.FloatValue
    dec: _wrappers_pb2.FloatValue
    maxVelocity: _wrappers_pb2.FloatValue
    position: float
    def __init__(self, position: _Optional[float] = ..., maxVelocity: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., acc: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., dec: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...

class msgProfileTorqueCmd(_message.Message):
    __slots__ = ["current", "maxCurrent", "torquePercent"]
    CURRENT_FIELD_NUMBER: _ClassVar[int]
    MAXCURRENT_FIELD_NUMBER: _ClassVar[int]
    TORQUEPERCENT_FIELD_NUMBER: _ClassVar[int]
    current: _wrappers_pb2.FloatValue
    maxCurrent: _wrappers_pb2.FloatValue
    torquePercent: float
    def __init__(self, torquePercent: _Optional[float] = ..., current: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., maxCurrent: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...

class msgProfileVelocityCmd(_message.Message):
    __slots__ = ["acc", "dec", "maxVelocity", "velocity"]
    ACC_FIELD_NUMBER: _ClassVar[int]
    DEC_FIELD_NUMBER: _ClassVar[int]
    MAXVELOCITY_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    acc: _wrappers_pb2.FloatValue
    dec: _wrappers_pb2.FloatValue
    maxVelocity: _wrappers_pb2.FloatValue
    velocity: float
    def __init__(self, velocity: _Optional[float] = ..., maxVelocity: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., acc: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ..., dec: _Optional[_Union[_wrappers_pb2.FloatValue, _Mapping]] = ...) -> None: ...
