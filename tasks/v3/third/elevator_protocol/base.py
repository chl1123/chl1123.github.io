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
