"""Elevator protocol registration metadata.

The package exports the runtime protocol interfaces without writing files when
it is imported by ``tasks/v3/standard/elevator.py``.  Installation can execute
this module directly to generate the Roboshop registration descriptor.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from .base import ElevatorProtocol, ElevatorProtocolResult, ProtocolRejected, ProtocolUnavailable
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
