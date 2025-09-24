from .pymodule import PyModule
from typing import Union, Optional
import json


def addService(
    server_name: str,
    service_name: str,
    function: callable,
    no_return: bool = False,
    dispatcher: bool = False,
):
    if no_return:
        PyModule.addServiceNoReturn(server_name, service_name, function)
    elif dispatcher:
        PyModule.addServiceDispatcher(server_name, service_name, function)
    else:
        PyModule.addService(server_name, service_name, function)


def callService(
    server_name: str,
    service_name: str,
    timeout_ms: Optional[int] = 5000,
    request: Optional[Union[str, dict]] = None,
    no_return: bool = False,
    dispatcher: bool = False,
):
    if request is None:
        request = ""
    elif isinstance(request, dict):
        request = json.dumps(request)

    if no_return:
        PyModule.callServiceNoReturn(server_name, service_name, timeout_ms, request)
    elif dispatcher:
        return PyModule.callServiceDispatcher(
            server_name, service_name, timeout_ms, request
        )
    else:
        return PyModule.callService(server_name, service_name, timeout_ms, request)
