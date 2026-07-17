#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Compatibility exports for BehavFactory LED scripts."""

from syspy.led import Led as led
from syspy.led import LedOutput

__all__ = ["led", "LedOutput"]
