import json

import pytest

from syspy.dio import Do


class FakeRpcClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_message(self, topic, plugin):
        self.calls.append((topic, plugin))
        return json.dumps(self.payload)


@pytest.fixture
def reset_do_state():
    Do._MODEL_CLASS = None
    Do.data = None
    Do._last_update_time = 0.0
    yield
    Do._MODEL_CLASS = None
    Do.data = None
    Do._last_update_time = 0.0


def test_init_model_class_binds_message_class(reset_do_state):
    # 缺少 @classmethod 时该调用会抛 TypeError（Do 的模型类无法初始化）
    Do.init_model_class()

    from syspy.protobuf import Message_DO

    assert Do._MODEL_CLASS is Message_DO


def test_get_do_reads_node_status(reset_do_state, monkeypatch):
    fake_client = FakeRpcClient(
        {
            "node": [
                {"id": 1, "status": True},
                {"id": 2, "status": False},
            ],
            "maxNode": 2,
        }
    )
    monkeypatch.setattr(Do, "_rpc_client", fake_client)

    assert Do.get_do(1) is True
    assert Do.get_do(2) is False
    assert Do.get_do(3) is False
    assert Do.get_max_node() == 2
    assert fake_client.calls[0] == ("rbk.protocol.Message_DO", "DSPChassis")
