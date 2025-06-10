import enum
from abc import ABC, abstractmethod

class CommType(enum.Enum):
    SERIAL = 0
    CAN = 1

class Communication(ABC):
    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def send(self, message):
        pass

    @abstractmethod
    def recv(self):
        pass
