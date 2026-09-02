from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProtocolUnavailable(RuntimeError):
    pass


class ProtocolRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class DoorProtocolResult:
    accepted: bool
    control_state: str
    passage_state: str
    error_code: int = 0


class DoorProtocol(ABC):
    supports_source_side = True

    @abstractmethod
    def query_status(self) -> DoorProtocolResult:
        pass

    @abstractmethod
    def request_open(self, source_side, instance_args, active_time: int) -> DoorProtocolResult:
        pass

    @abstractmethod
    def keep_alive(self, source_side, instance_args, active_time: int) -> DoorProtocolResult:
        pass

    @abstractmethod
    def release(self, instance_args=None) -> DoorProtocolResult:
        pass
