#!/usr/bin/env python3
"""
Export each sheet of an Excel workbook to CSV and maintain a manifest JSON.

Manifest format
---------------
{
  "version": 1,
  "generated_dir": "generated/csv",
  "source": {
    "path": "path/to/workbook.xlsx",
    "sha256": "<sha256-of-excel-file-bytes>"
  },
  "output": [
    {
      "sheet_name": "Sheet1",
      "csv_path": "generated/csv/workbook/Sheet1.csv",
      "sha256": "<sha256-of-csv-file-bytes>"
    }
  ]
}

Versioning rule (no signature)
------------------------------
- The manifest "version" increments only when the Excel file's sha256 changes
  compared to the previous manifest.

Notes
-----
- This reads the workbook via pandas/openpyxl. If your workbook relies on formulas,
  ensure the file is saved with calculated values before committing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# ----------------------------
# Utilities
# ----------------------------
def sha256_file(path: Path) -> str:
    """Compute sha256 of a file's bytes."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str) -> str:
    """
    Make a filesystem-friendly filename stem from a sheet name.
    Keeps alnum, '-' and '_' and replaces other chars with '_'.
    """
    cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name).strip("_")
    return cleaned or "sheet"


def read_json(path: Path) -> Dict[str, Any]:
    """Read JSON file if it exists, else return empty dict."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON with stable formatting and trailing newline."""
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ----------------------------
# Data model
# ----------------------------
@dataclass(frozen=True)
class OutputEntry:
    sheet_name: str
    csv_path: str
    sha256: str

    def to_dict(self) -> Dict[str, str]:
        return {"sheet_name": self.sheet_name, "csv_path": self.csv_path, "sha256": self.sha256}


# ----------------------------
# Core logic
# ----------------------------
def export_sheets_to_csv(excel_path: Path, outdir: Path) -> List[OutputEntry]:
    """
    Export each sheet in excel_path to a CSV under:
      outdir/<workbook-stem>/<safe-sheet-name>.csv

    Returns list of OutputEntry objects (sheet_name, csv_path, csv sha256).
    """
    xls = pd.ExcelFile(excel_path)

    workbook_dir = outdir / excel_path.stem
    workbook_dir.mkdir(parents=True, exist_ok=True)

    outputs: List[OutputEntry] = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name=sheet_name)

        csv_file = workbook_dir / f"{safe_filename(sheet_name)}.csv"
        df.to_csv(csv_file, index=False)

        outputs.append(
            OutputEntry(
                sheet_name=sheet_name,
                csv_path=str(csv_file.as_posix()),
                sha256=sha256_file(csv_file),
            )
        )

    # stable ordering in output
    return sorted(outputs, key=lambda o: o.csv_path)


def next_version(old_manifest: Dict[str, Any], new_excel_sha: str) -> int:
    """
    Increment version only when the Excel sha changes.
    """
    old_version = int(old_manifest.get("version", 0))
    old_sha = (old_manifest.get("source") or {}).get("sha256", "")
    return old_version + 1 if new_excel_sha != old_sha else old_version


def build_manifest(
    excel_path: Path,
    outdir: Path,
    manifest_path: Path,
    outputs: List[OutputEntry],
    excel_sha: str,
    version: int,
) -> Dict[str, Any]:
    return {
        "version": version,
        "generated_dir": str(outdir.as_posix()),
        "source": {
            "path": str(excel_path.as_posix()),
            "sha256": excel_sha,
        },
        "output": [o.to_dict() for o in outputs],
    }


# ----------------------------
# CLI
# ----------------------------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Export Excel sheets to CSV and update manifest JSON.")
    ap.add_argument("--excel", required=True, help="Path to .xlsx/.xlsm")
    ap.add_argument("--outdir", required=True, help="Directory for CSV outputs")
    ap.add_argument("--manifest", required=True, help="Path to manifest.json")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    excel_path = Path(args.excel)
    outdir = Path(args.outdir)
    manifest_path = Path(args.manifest)

    if not excel_path.exists():
        raise SystemExit(f"Excel file not found: {excel_path}")

    outdir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    old_manifest = read_json(manifest_path)

    excel_sha = sha256_file(excel_path)
    outputs = export_sheets_to_csv(excel_path, outdir)

    version = next_version(old_manifest, excel_sha)
    new_manifest = build_manifest(excel_path, outdir, manifest_path, outputs, excel_sha, version)

    write_json(manifest_path, new_manifest)


if __name__ == "__main__":
    main()