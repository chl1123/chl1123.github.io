import json
import uuid
from typing import Optional, Union, Dict, Any


class JSONRPCError(Exception):
    # 标准错误码
    PARSE = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL = -32603

    # 自定义错误码
    INVALID_RESPONSE = -32000

    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(code, message, data)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data
        }


class ParseError(JSONRPCError):
    def __init__(self, data: Optional[Any] = None):
        super().__init__(self.PARSE, "Parse error", data)


class InvalidRequest(JSONRPCError):
    def __init__(self, data: Optional[Any] = None):
        super().__init__(self.INVALID_REQUEST, "Invalid Request", data)


class MethodNotFound(JSONRPCError):
    def __init__(self, data: Optional[Any] = None):
        super().__init__(self.METHOD_NOT_FOUND, "Method not found", data)


class InvalidParams(JSONRPCError):
    def __init__(self, data: Optional[Any] = None):
        super().__init__(self.INVALID_PARAMS, "Invalid params", data)


class InternalError(JSONRPCError):
    def __init__(self, data: Optional[Any] = None):
        super().__init__(self.INTERNAL, "Internal error", data)


class InvalidResponse(JSONRPCError):
    def __init__(self, data: Optional[Any] = None):
        super().__init__(self.INVALID_RESPONSE, "Invalid response", data)


class JsonRpcMessage:
    def __init__(self, id: Optional[Union[int, str]] = None, jsonrpc: str = "2.0"):
        self._jsonrpc = jsonrpc
        self._id = id

    def set_id(self, id: Optional[Union[int, str]]):
        self._id = id

    def get_id(self):
        return self._id

    def get_version(self):
        return self._jsonrpc

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self):
        pass


class JSONRPCRequest(JsonRpcMessage):
    def __init__(self, method: str, params: Optional[Union[list, dict]] = None,
                 id: Optional[Union[int, str]] = None, jsonrpc: str = "2.0"):
        super().__init__(id or str(uuid.uuid4()), jsonrpc)
        self._method = method
        self._params = params or []

    @classmethod
    def parse(cls, data: Dict) -> 'JSONRPCRequest':
        if data.get("jsonrpc") != "2.0":
            raise InvalidRequest("Invalid JSON-RPC version")

        method = data.get("method")
        if not isinstance(method, str):
            raise InvalidRequest("Missing or invalid method")

        params = data.get("params")
        if params is not None and not isinstance(params, (list, dict)):
            raise InvalidRequest("Params must be array or object")

        request_id = data.get("id")
        if request_id is not None and not isinstance(request_id, (int, str, type(None))):
            raise InvalidRequest("Invalid ID type")

        return cls(method=method, params=params, id=request_id)

    def set_method(self, method: str):
        self._method = method

    def get_method(self):
        return self._method

    def get_params(self):
        return self._params

    def to_dict(self) -> dict:
        return {
            "jsonrpc": self._jsonrpc,
            "method": self._method,
            "params": self._params,
            "id": self._id
        }


class JSONRPCResponse(JsonRpcMessage):
    def __init__(self, id: Optional[Union[int, str]] = None):
        super().__init__(id)
        self._result = None
        self._error = None

    def set_result(self, result: Any):
        self._result = result
        self._error = None  # 设置结果时清除错误

    def set_error(self, error: JSONRPCError):
        self._error = error
        self._result = None  # 设置错误时清除结果

    def has_result(self) -> bool:
        return self._result is not None

    def has_error(self) -> bool:
        return self._error is not None

    def get_result(self):
        return self._result

    def get_error(self) -> Optional[JSONRPCError]:
        return self._error

    @classmethod
    def parse(cls, data: Dict) -> 'JSONRPCResponse':
        if data.get("jsonrpc") != "2.0":
            raise InvalidResponse("Invalid JSON-RPC version")

        request_id = data.get("id")
        if not isinstance(request_id, (int, str, type(None))):
            raise InvalidResponse("ID must be int, str or None")

        response = cls(id=request_id)
        if "result" in data:
            response.set_result(data.get("result"))
        elif data.get("error") is not None:
            error = data.get("error")
            if not isinstance(error, dict):
                raise InvalidResponse("Error must be dict")
            error_code = error.get("code")
            if not isinstance(error_code, int):
                raise InvalidResponse("Error code must be int")
            error_message = error.get("message")
            if not isinstance(error_message, str):
                raise InvalidResponse("Error message must be str")
            error_data = error.get("data")
            response.set_error(JSONRPCError(error_code, error_message, error_data))
        else:
            raise InvalidResponse(f"Missing result or error. {data=}")
        return response

    def to_dict(self) -> Dict:
        response = {"jsonrpc": self._jsonrpc, "id": self._id}
        if self.has_error():
            response["error"] = self._error.to_dict()
        else:
            response["result"] = self._result
        return response

    def get_print(self) -> str:
        response = self.to_dict()
        # 如果结果太长，则只显示长度
        length = len(str(self.get_result()))
        if length > 20:
            response["result"] = "..."
            response["result_len"] = length
        return json.dumps(response)
