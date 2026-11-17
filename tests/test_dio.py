import inspect
import time

import pytest

from syspy.dio import Do


@pytest.fixture(autouse=True)
def reset_do_state():
    Do._MODEL_CLASS = None
    Do.data = None
    yield
    Do._MODEL_CLASS = None
    Do.data = None


def test_init_model_class_is_classmethod():
    """Do.init_model_class 必须是 classmethod，否则 update() 会因缺少 cls 参数崩溃"""
    assert isinstance(inspect.getattr_static(Do, "init_model_class"), classmethod)


def test_init_model_class_callable_without_instance():
    """Do.update() 以 cls.init_model_class() 形式调用，必须无需额外参数"""
    Do._MODEL_CLASS = object()
    assert Do.init_model_class() is None


def test_update_with_cached_data_does_not_raise():
    """使用缓存数据刷新 DO 状态时不应抛 TypeError"""
    Do._MODEL_CLASS = object()
    Do.data = object()
    Do._last_update_time = time.time()
    assert Do.update() is True
