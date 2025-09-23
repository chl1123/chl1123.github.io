from .pymodule import PyModule


def LogDebug(msg: str):
    PyModule.LogDebug(msg)


def LogInfo(msg: str):
    PyModule.LogInfo(msg)


def LogWarn(msg: str):
    PyModule.LogWarn(msg)


def LogError(msg: str):
    PyModule.LogError(msg)


def LogFatal(msg: str):
    PyModule.LogFatal(msg)


def formatLogText(msg: str):
    return f"[Text][{msg}]"
