"""File ingestion adapter (REAL source) — desk exports / user-held RFQ history.

Accepts JSONL (one payload per line), a JSON array file, or CSV (header row
→ dict rows). Every payload is passed through the declarative FieldMap and
normalized; the verbatim row is preserved in ``raw``.

This is the adapter a desk export or a personally-held RFQ log flows through
today — the first real-data path into the journal.
"""

from __future__ import annotations

import csv
import json
from typing import Any, Dict, Iterator, List

from .base import FieldMap, RFQProvider


class FileRFQProvider(RFQProvider):
    """REAL source: payloads from a file on disk."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.name = f"file:{path}"

    def iter_raw(self) -> Iterator[Dict[str, Any]]:
        if self.path.endswith(".csv"):
            with open(self.path, "r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    yield dict(row)
        elif self.path.endswith(".json"):
            with open(self.path, "r", encoding="utf-8") as f:
                arr = json.load(f)
            if not isinstance(arr, list):
                raise ValueError(f"{self.path}: expected a JSON array of payloads")
            for item in arr:
                yield item
        else:  # default: JSONL
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    yield json.loads(s)
