import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict, Optional
import openpyxl
from openpyxl import Workbook

class StreamingExcelExporter:
    """
    Writes data to Excel in real-time (row by row).
    Useful for long scraping sessions to prevent data loss.
    """
    def __init__(self, filename: str, columns: List[str]):
        self.filename = filename
        self.columns = columns
        self.workbook: Optional[Workbook] = None
        self.sheet = None
        self._initialize_file()

    def _initialize_file(self):
        """Creates file and writes header if it doesn't exist"""
        if os.path.exists(self.filename):
            self.workbook = openpyxl.load_workbook(self.filename)
            self.sheet = self.workbook.active
        else:
            self.workbook = Workbook()
            self.sheet = self.workbook.active
            self.sheet.append(self.columns)
            self.workbook.save(self.filename)

    def append_row(self, row_data: List[Any]):
        """Appends a single row and saves the file"""
        self.sheet.append(row_data)
        self._save()

    def append_batch(self, rows: List[List[Any]]):
        """Appends a batch of rows and saves the file"""
        for row in rows:
            self.sheet.append(row)
        self._save()

    def _save(self):
        try:
            self.workbook.save(self.filename)
        except PermissionError:
            print(f"⚠️ Warning: Could not save {self.filename} (Permission Denied). Is it open?")

class StreamingJSONExporter:
    """
    Writes data to JSONL (JSON Lines) file in real-time.
    Safer than standard JSON for streams as it doesn't require loading the whole file.
    """
    def __init__(self, filename: str):
        self.filename = filename
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

    def append_item(self, item: Dict[str, Any]):
        """Appends a single item as a JSON line"""
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    def append_batch(self, items: List[Dict[str, Any]]):
        """Appends a batch of items"""
        with open(self.filename, 'a', encoding='utf-8') as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
