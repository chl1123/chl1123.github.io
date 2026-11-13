import os
import unittest

# 当前环境可能安装了较新的 protobuf，纯 Python 实现可兼容旧版生成代码
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from syspy import Do


class _FakeRpcClient:
    """返回固定 DO 消息的 RPC 桩。"""

    def __init__(self, payload: str):
        self.payload = payload

    def get_message(self, topic: str, plugin: str) -> str:
        return self.payload


class DoReadTest(unittest.TestCase):
    """验证 DO 读取接口在首次调用时能正确初始化模型类。"""

    def setUp(self):
        self._saved_client = Do._rpc_client
        self._saved_model_class = Do._MODEL_CLASS
        self._saved_data = Do.data
        self._saved_update_time = Do._last_update_time
        Do._rpc_client = _FakeRpcClient(
            '{"node": [{"id": 1, "status": true}], "max_node": 4}'
        )
        Do._MODEL_CLASS = None
        Do.data = None
        Do._last_update_time = 0.0

    def tearDown(self):
        Do._rpc_client = self._saved_client
        Do._MODEL_CLASS = self._saved_model_class
        Do.data = self._saved_data
        Do._last_update_time = self._saved_update_time

    def test_get_do_initializes_model_class(self):
        self.assertIs(Do.get_do(1), True)
        self.assertIs(Do.get_do(2), False)

    def test_get_dos_and_max_node(self):
        self.assertEqual(
            [(node.id, node.status) for node in Do.get_dos()], [(1, True)]
        )
        self.assertEqual(Do.get_max_node(), 4)


if __name__ == "__main__":
    unittest.main()
