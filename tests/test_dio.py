import inspect

import pytest

from syspy.dio import Do


@pytest.fixture(autouse=True)
def reset_do_state():
    saved = (Do._MODEL_CLASS, Do.data, Do._last_update_time)
    Do._MODEL_CLASS = None
    Do.data = None
    yield
    Do._MODEL_CLASS, Do.data, Do._last_update_time = saved


def test_init_model_class_is_classmethod():
    """Do.update() 通过 cls.init_model_class() 调用，必须是 classmethod"""
    assert isinstance(inspect.getattr_static(Do, "init_model_class"), classmethod)


def test_init_model_class_callable_via_class():
    """缺少 @classmethod 时，通过类调用会抛 TypeError: missing 'cls'"""
    Do._MODEL_CLASS = object()
    assert Do.init_model_class() is None
