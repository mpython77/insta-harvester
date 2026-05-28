"""
Infrastructure adapters.

These are the only modules in v3 that import Playwright or curl_cffi.
Everything above (``core``, ``scrapers``, ``facade``) interacts with
this layer through the protocols declared in ``core.protocols``.
"""

from instaharvest._v3.infrastructure.http import CurlHttpClient
from instaharvest._v3.infrastructure.browser import PlaywrightBrowserSession
from instaharvest._v3.infrastructure.session import FileSessionStore
from instaharvest._v3.infrastructure.logger import StructuredLogger, get_logger

__all__ = [
    "CurlHttpClient",
    "PlaywrightBrowserSession",
    "FileSessionStore",
    "StructuredLogger",
    "get_logger",
]
