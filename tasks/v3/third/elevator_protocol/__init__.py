"""Elevator protocol registration metadata.

The package exports the runtime protocol interfaces without writing files when
it is imported by ``tasks/v3/standard/elevator.py``.  Installation can execute
this module directly to generate the Roboshop registration descriptor.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


class ProtocolUnavailable(RuntimeError):
    pass


class ProtocolRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class ElevatorProtocolResult:
    accepted: bool
    control_state: str
    floor: int
    move_state: int
    door_state: int
    task_step: Optional[int] = None
    error_code: int = 0


class ElevatorProtocol(ABC):
    @abstractmethod
    def query_status(self) -> ElevatorProtocolResult:
        pass

    @abstractmethod
    def call(self, floor: int, active_time: int) -> ElevatorProtocolResult:
        pass

    @abstractmethod
    def keep_alive(self, floor: int, active_time: int) -> ElevatorProtocolResult:
        pass

    @abstractmethod
    def release(self, active_time: int) -> ElevatorProtocolResult:
        pass

    @abstractmethod
    def is_target_ready(self, result: ElevatorProtocolResult, target_floor: int) -> bool:
        pass
#from syspy.utils import RESOURCES_DIR
from syspy.utils.param_server import BindType, ParamBuilder, ParamType

RESOURCES_DIR = "/opt/.data/rbk/resources/"
SCRIPTS_DIR = RESOURCES_DIR + "scripts/"

def build_registration() -> ParamBuilder:
    """Build the Roboshop registration descriptor with the shared parameter API."""
    builder = ParamBuilder(__file__, desc="Elevator protocol registration", p_type="registration")
    with builder.GROUPS():
        with builder.GROUP(
                key="communicationProtocol",
                name="Protocol Brand",
                desc="Select protocol brand",
        ):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            builder.DEFAULTVALUE("yuefan")

            with builder.CHILDREN():
                with builder.CHILD(
                        key="yuefan",
                        name="Yue Fan",
                        desc="Yue fan",
                ):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        with builder.CHILD(
                                key="name",
                                name="Name",
                                desc=(
                                        "Script path (relative to "
                                        "/opt/.data/rbk/resources/scripts/)"
                                ),
                        ):
                            builder.TYPE(ParamType.BIND_TYPE)
                            builder.BINDTYPE(
                                BindType.script("tasks:third:elevator_protocol"),
                                no_empty=True,
                            )
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE(
                                "tasks/third/elevator_protocol/yuefan.py"
                            )

                        with builder.CHILD(
                                key="args",
                                name="Args",
                                desc="Elevator protocol parameters",
                        ):
                            builder.TYPE(ParamType.ARRAY)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE({})

    return builder


def registration_definition() -> List[Dict[str, Any]]:
    """Return the parameter builder's top-level registration definitions."""
    return build_registration().toDict()["groups"]


def generate_registration(output_path: Union[str, Path] = RESOURCES_DIR + "policyTemplate/elevator.json"):
    """Write the elevator protocol registration descriptor to ``output_path``."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(registration_definition(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        )


generate_registration()


__all__ = [
    "ElevatorProtocol",
    "ElevatorProtocolResult",
    "ProtocolRejected",
    "ProtocolUnavailable",
]
