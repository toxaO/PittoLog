from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanResult:
    ok: bool
    message: str
    item_barcode: str | None = None
    department_barcode: str | None = None
    item_name: str | None = None
    department_name: str | None = None
    operation: str | None = None
