import os

# 仓库自带的生成代码由 protoc < 3.19 生成，新版 protobuf 需要纯 Python 实现才能加载。
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import inspect
import unittest

from syspy.dio import Do
from syspy.protobuf import Message_DO


class _FakeRpcClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_message(self, topic, plugin):
        self.calls.append((topic, plugin))
        return self.payload


class DoReadTest(unittest.TestCase):
    def setUp(self):
        Do._MODEL_CLASS = None
        Do.data = None
        Do._last_update_time = 0.0
        self.addCleanup(setattr, Do, "_rpc_client", Do._rpc_client)
        Do._rpc_client = _FakeRpcClient('{"node": [{"id": 3, "status": true}], "max_node": 8}')

    def test_init_model_class_is_classmethod(self):
        self.assertIsInstance(inspect.getattr_static(Do, "init_model_class"), classmethod)

    def test_get_do_uses_message_model(self):
        self.assertTrue(Do.get_do(3))
        self.assertFalse(Do.get_do(4))
        self.assertEqual(Do.get_max_node(), 8)
        self.assertIs(Do._MODEL_CLASS, Message_DO)


if __name__ == "__main__":
    unittest.main()
