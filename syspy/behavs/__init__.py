__all__ = ["led"]


def __getattr__(name):
    if name == "led":
        from .led import led
        globals()[name] = led
        return led
    raise AttributeError(name)
