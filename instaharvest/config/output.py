"""Output / export configuration.

Owned by: exporters and downloaders.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputConfig:
    """Configuration for files written by scrapers."""

    base_dir: Path = Path(".")
    json_indent: int = 2
    csv_bom: bool = True  # BOM for Excel compatibility
    overwrite_existing: bool = False

    # Session storage
    session_filename: str = "instagram_session.json"
    session_dir: Path = Path(".")

    def __post_init__(self) -> None:
        if self.json_indent < 0:
            raise ValueError("json_indent must be >= 0")
        if not self.session_filename:
            raise ValueError("session_filename must be non-empty")
