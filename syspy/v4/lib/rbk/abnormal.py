from .pymodule import PyModule


def setTask(
    code: int,
    desc: str,
    reason: str,
    method: str,
    task: str,
    fileName: str = "",
    mapType: str = "",
    elementType: str = "",
    elementName: str = "",
    policyName: str = "",
    param: str = "",
) -> bool:
    return PyModule.setTask(
        code,
        desc,
        reason,
        method,
        task,
        fileName,
        mapType,
        elementType,
        elementName,
        policyName,
        param,
    )


def setMap(
    code: int,
    desc: str,
    reason: str,
    method: str,
    fileName: str,
    mapType: str = "",
    elementType: str = "",
    elementName: str = "",
) -> bool:
    return PyModule.setMap(
        code,
        desc,
        reason,
        method,
        fileName,
        mapType,
        elementType,
        elementName,
    )


def setModel(
    code: int,
    desc: str,
    reason: str,
    method: str,
    fileName: str,
    deviceType: str = "",
    deviceKey: str = "",
    param: str = "",
) -> bool:
    return PyModule.setModel(
        code,
        desc,
        reason,
        method,
        fileName,
        deviceType,
        deviceKey,
        param,
    )


def setConfig(
    code: int,
    desc: str,
    reason: str,
    method: str,
    appType: str,
    fileName: str,
    param: str = "",
) -> bool:
    return PyModule.setConfig(
        code,
        desc,
        reason,
        method,
        appType,
        fileName,
        param,
    )


def setSystem(
    code: int, desc: str, reason: str, method: str, fileName: str, param: str = ""
) -> bool:
    return PyModule.setSystem(
        code,
        desc,
        reason,
        method,
        fileName,
        param,
    )


def setEnvironment(
    code: int, desc: str, reason: str, method: str, position: str = ""
) -> bool:
    return PyModule.setEnvironment(
        code,
        desc,
        reason,
        method,
        position,
    )


def setDevice(
    code: int,
    desc: str,
    reason: str,
    method: str,
    fileName: str,
    deviceType: str = "",
    deviceKey: str = "",
    param: str = "",
    errorCode: int = 0,
) -> bool:
    return PyModule.setDevice(
        code,
        desc,
        reason,
        method,
        fileName,
        deviceType,
        deviceKey,
        param,
        errorCode,
    )


def setConnect(
    code: int,
    desc: str,
    reason: str,
    method: str,
    fileName: str,
    deviceType: str = "",
    deviceKey: str = "",
    param: str = "",
) -> bool:
    return PyModule.setConnect(
        code,
        desc,
        reason,
        method,
        fileName,
        deviceType,
        deviceKey,
        param,
    )


def setCalibrate(
    code: int,
    desc: str,
    reason: str,
    method: str,
    deviceType: str,
    deviceKey: str = "",
) -> bool:
    return PyModule.setCalibrate(
        code,
        desc,
        reason,
        method,
        deviceType,
        deviceKey,
    )


def setLicense(
    code: int, desc: str, reason: str, method: str, licenseType: str = ""
) -> bool:
    return PyModule.setLicense(
        code,
        desc,
        reason,
        method,
        licenseType,
    )


def setChassis(code: int, desc: str, reason: str, method: str) -> bool:
    return PyModule.setChassis(code, desc, reason, method)


def clear(code: int, device: str = str()):
    return PyModule.clear(code, device)


def clearDevice(device: str):
    return PyModule.clear(device)


def exists(code: int, device: str = str()):
    return PyModule.exists(code, device)


def existsDevice(device: str):
    return PyModule.exists(device)


def getNum():
    return PyModule.getNum()
