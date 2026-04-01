#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Safe placeholder for missing State fields."""


class _MissingValue(object):
    raw = {}

    def __getattr__(self, _key):
        return self

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __eq__(self, other):
        return other is None

    def __repr__(self):
        return "None"

    __str__ = __repr__

    def get(self, _key, default=None):
        return default


MISSING = _MissingValue()


class StateNode(object):
    """Dictionary wrapper with nested attribute access for State data."""

    def __init__(self, data):
        self._data = data if isinstance(data, dict) else {}

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)
        value = self._data.get(key, MISSING)
        if value is None:
            return MISSING
        if isinstance(value, dict):
            return StateNode(value)
        return value

    def get(self, key, default=None):
        value = self._data.get(key, default)
        if value is None:
            return default
        if isinstance(value, dict):
            return StateNode(value)
        return value

    @property
    def raw(self):
        return self._data
