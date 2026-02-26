"""
Instagram Scraper - Universal Data Export

Export any scraper result to CSV, JSON, or JSONL format.
Handles nested data structures, auto-flattening, and UTF-8 BOM for Excel.

Usage:
    from instaharvest import DataExporter

    exporter = DataExporter()
    exporter.export_csv(result.posts, 'hashtag_fashion.csv')
    exporter.export_json(result.to_dict(), 'hashtag_fashion.json')

    # Auto-export with timestamp
    exporter.auto_export(result, prefix='fashion', formats=['csv', 'json'])
"""

import csv
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DataExporter:
    """
    Universal data exporter for Instagram scraper results.

    Supports CSV, JSON, and JSONL (JSON Lines) formats.
    Handles nested dataclass results, auto-flattening for CSV,
    and UTF-8 BOM headers for Excel compatibility.

    Features:
    - Export to CSV with auto-column detection
    - Export to JSON (pretty-printed)
    - Export to JSONL (streaming, one record per line)
    - Auto-export with timestamped filenames
    - Dataclass → dict conversion
    - Nested dict flattening for CSV
    - UTF-8 BOM for Excel CSV compatibility
    """

    def __init__(
        self,
        output_dir: str = '.',
        add_bom: bool = True,
        pretty_json: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize DataExporter.

        Args:
            output_dir: Directory for output files (created if needed)
            add_bom: Add UTF-8 BOM to CSV for Excel compatibility
            pretty_json: Pretty-print JSON output
            logger: Optional logger instance
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.add_bom = add_bom
        self.pretty_json = pretty_json
        self.logger = logger or logging.getLogger(__name__)

    # ==================== CSV Export ====================

    def export_csv(
        self,
        data: Union[List[Dict], List[Any]],
        filename: str,
        fieldnames: Optional[List[str]] = None,
    ) -> str:
        """
        Export data to CSV file.

        Args:
            data: List of dicts or dataclass instances
            filename: Output filename (relative to output_dir)
            fieldnames: Optional column names (auto-detected if None)

        Returns:
            Absolute path to created file
        """
        if not data:
            self.logger.warning("No data to export to CSV")
            return ''

        rows = self._normalize_rows(data)
        if not rows:
            return ''

        # Auto-detect fieldnames from first row
        if fieldnames is None:
            fieldnames = list(rows[0].keys())

        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8-sig' if self.add_bom else 'utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

        self.logger.info(f"CSV exported: {filepath} ({len(rows)} rows)")
        return str(filepath.resolve())

    # ==================== JSON Export ====================

    def export_json(
        self,
        data: Any,
        filename: str,
    ) -> str:
        """
        Export data to JSON file.

        Args:
            data: Any serializable data (dict, list, dataclass)
            filename: Output filename

        Returns:
            Absolute path to created file
        """
        serializable = self._to_serializable(data)
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(
                serializable, f,
                ensure_ascii=False,
                indent=2 if self.pretty_json else None,
                default=str,
            )

        size_kb = filepath.stat().st_size / 1024
        self.logger.info(f"JSON exported: {filepath} ({size_kb:.1f} KB)")
        return str(filepath.resolve())

    # ==================== JSONL Export ====================

    def export_jsonl(
        self,
        data: Union[List[Dict], List[Any]],
        filename: str,
    ) -> str:
        """
        Export data to JSON Lines file (one JSON object per line).
        Ideal for streaming and large datasets.

        Args:
            data: List of records
            filename: Output filename

        Returns:
            Absolute path to created file
        """
        if not data:
            self.logger.warning("No data to export to JSONL")
            return ''

        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                serializable = self._to_serializable(item)
                f.write(json.dumps(serializable, ensure_ascii=False, default=str))
                f.write('\n')

        self.logger.info(f"JSONL exported: {filepath} ({len(data)} records)")
        return str(filepath.resolve())

    # ==================== Auto Export ====================

    def auto_export(
        self,
        result: Any,
        prefix: str = 'export',
        formats: List[str] = None,
    ) -> Dict[str, str]:
        """
        Automatically export result to multiple formats with timestamped filenames.

        Args:
            result: Scraper result (dataclass or dict)
            prefix: Filename prefix (e.g. 'fashion_hashtag')
            formats: List of formats: 'csv', 'json', 'jsonl' (default: ['csv', 'json'])

        Returns:
            Dict mapping format to file path
        """
        if formats is None:
            formats = ['csv', 'json']

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        paths = {}

        # Convert to dict
        data_dict = self._to_serializable(result)

        for fmt in formats:
            filename = f"{prefix}_{timestamp}.{fmt}"

            if fmt == 'json':
                paths['json'] = self.export_json(data_dict, filename)

            elif fmt == 'csv':
                # For CSV, find the list of items to export
                rows = self._extract_rows(data_dict)
                if rows:
                    paths['csv'] = self.export_csv(rows, filename)

            elif fmt == 'jsonl':
                rows = self._extract_rows(data_dict)
                if rows:
                    paths['jsonl'] = self.export_jsonl(rows, filename)

        return paths

    # ==================== Utilities ====================

    def _normalize_rows(self, data: Union[List[Dict], List[Any]]) -> List[Dict]:
        """Convert list of items to list of flat dicts"""
        rows = []
        for item in data:
            if is_dataclass(item):
                d = asdict(item)
            elif isinstance(item, dict):
                d = item
            else:
                d = {'value': str(item)}

            # Flatten nested dicts
            flat = self._flatten_dict(d)
            rows.append(flat)

        return rows

    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dict: {'a': {'b': 1}} → {'a_b': 1}"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            elif isinstance(v, list):
                # Convert lists to string for CSV
                if v and isinstance(v[0], dict):
                    items.append((new_key, json.dumps(v, ensure_ascii=False, default=str)))
                else:
                    items.append((new_key, ', '.join(str(x) for x in v)))
            else:
                items.append((new_key, v))
        return dict(items)

    def _extract_rows(self, data: Any) -> List[Dict]:
        """Extract exportable rows from a result dict"""
        if isinstance(data, list):
            return self._normalize_rows(data)

        if isinstance(data, dict):
            # Find the first list field (posts, users, items, etc.)
            for key in ['posts', 'users', 'hashtags', 'places', 'items', 'stories', 'results']:
                if key in data and isinstance(data[key], list) and data[key]:
                    return self._normalize_rows(data[key])

            # If no list found, try all list values
            for key, val in data.items():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    return self._normalize_rows(val)

            # Single record — wrap in list
            return [self._flatten_dict(data)]

        return []

    def _to_serializable(self, obj: Any) -> Any:
        """Convert any object to JSON-serializable format"""
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, dict):
            return {k: self._to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._to_serializable(item) for item in obj]
        if isinstance(obj, (datetime, Path)):
            return str(obj)
        return obj
