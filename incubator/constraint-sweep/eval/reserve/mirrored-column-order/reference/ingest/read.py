"""Read a bank export file back into payment records.

The bank's import job uses this reader, with the field order from layout.json.
"""
import csv
import json
from pathlib import Path

LAYOUT = Path(__file__).with_name("layout.json")


def read_export(fh, layout_path=LAYOUT):
    """Return one dict per row, keyed by the layout's column names."""
    columns = json.loads(Path(layout_path).read_text(encoding="utf-8"))["columns"]
    return [dict(zip(columns, fields)) for fields in csv.reader(fh)]
