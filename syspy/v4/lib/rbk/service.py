from .pymodule import PyModule
from typing import Union, Optional
import json


def addService(server_name: str, service_name: str, function: callable):
    return PyModule.addService(server_name, service_name, function)


def addServiceDispatcher(server_name: str, service_name: str, function: callable):
    return PyModule.addServiceDispatcher(server_name, service_name, function)


def callService(
    server_name: str,
    service_name: str,
    timeout_ms: Optional[int] = None,
    request: Optional[Union[str, dict]] = None,
):
    if timeout_ms is None:
        timeout_ms = 5000
    if type(request) is dict:
        request = json.dumps(request)
    if request is None:
        request = ""
    return PyModule.callService(server_name, service_name, timeout_ms, request)


def callServiceDispatcher(
    server_name: str,
    service_name: str,
    timeout_ms: Optional[int] = None,
    request: Optional[Union[str, dict]] = None,
):
    if timeout_ms is None:
        timeout_ms = 5000
    if type(request) is dict:
        request = json.dumps(request)
    if request is None:
        request = ""
    return PyModule.callServiceDispatcher(
        server_name, service_name, timeout_ms, request
    )
