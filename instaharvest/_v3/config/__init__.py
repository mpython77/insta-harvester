"""
Composed configuration for v3.

Each subsystem owns its own dataclass under this package.
``Settings`` composes them; nothing else does. No subsystem
should reach across boundaries to read another subsystem's
config — pass the relevant config in at construction time.
"""

from instaharvest._v3.config.settings import Settings

__all__ = ["Settings"]
