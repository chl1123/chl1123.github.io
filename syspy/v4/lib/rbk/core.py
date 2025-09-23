from .pymodule import PyModule
import time, signal


def Init(name: str):
    PyModule.Init(name)
    signal.signal(signal.SIGINT, lambda signal, frame: exit(0))


def WaitForShutdown():
    while True:
        time.sleep(1)
