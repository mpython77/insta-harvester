"""
instaharvest.v3 -- canonical public import path for the v3 API.

Usage::

    from instaharvest.v3 import InstaHarvest, Settings, WebAPI

This module re-exports everything from the internal ``_v3`` package.
"""

from instaharvest._v3 import *  # noqa: F401,F403
from instaharvest._v3 import __all__  # noqa: F401
