# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class DoubleValue(BaseModel):
    """
        Wrapper message for `double`.

    The JSON representation for `DoubleValue` is JSON number.
    """

    # The double value.

    value: float = Field(default=0.0)


class FloatValue(BaseModel):
    """
        Wrapper message for `float`.

    The JSON representation for `FloatValue` is JSON number.
    """

    # The float value.

    value: float = Field(default=0.0)


class Int64Value(BaseModel):
    """
        Wrapper message for `int64`.

    The JSON representation for `Int64Value` is JSON string.
    """

    # The int64 value.

    value: int = Field(default=0)


class UInt64Value(BaseModel):
    """
        Wrapper message for `uint64`.

    The JSON representation for `UInt64Value` is JSON string.
    """

    # The uint64 value.

    value: int = Field(default=0)


class Int32Value(BaseModel):
    """
        Wrapper message for `int32`.

    The JSON representation for `Int32Value` is JSON number.
    """

    # The int32 value.

    value: int = Field(default=0)


class UInt32Value(BaseModel):
    """
        Wrapper message for `uint32`.

    The JSON representation for `UInt32Value` is JSON number.
    """

    # The uint32 value.

    value: int = Field(default=0)


class BoolValue(BaseModel):
    """
        Wrapper message for `bool`.

    The JSON representation for `BoolValue` is JSON `true` and `false`.
    """

    # The bool value.

    value: bool = Field(default=False)


class StringValue(BaseModel):
    """
        Wrapper message for `string`.

    The JSON representation for `StringValue` is JSON string.
    """

    # The string value.

    value: str = Field(default="")


class BytesValue(BaseModel):
    """
        Wrapper message for `bytes`.

    The JSON representation for `BytesValue` is JSON string.
    """

    # The bytes value.

    value: bytes = Field(default=b"")
