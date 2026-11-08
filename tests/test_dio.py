import os

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import pytest

from syspy.dio import Do
from syspy.protobuf import Message_DO


@pytest.fixture
def uninitialized_do():
    original = Do._MODEL_CLASS
    Do._MODEL_CLASS = None
    yield
    Do._MODEL_CLASS = original


def test_init_model_class_resolves_message_class(uninitialized_do):
    # Do.init_model_class 必须是类方法，且能从 syspy.protobuf 正确导入 Message_DO。
    Do.init_model_class()
    assert Do._MODEL_CLASS is Message_DO
