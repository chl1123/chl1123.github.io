from .state import state
from .tricolor import tricolor
from .audio import audio
from .trigger import trigger

__all__ = ["state", "led", "tricolor", "audio", "trigger"]


def __getattr__(name):
    if name == "led":
        from .led import led
        globals()[name] = led
        return led
    raise AttributeError(name)
