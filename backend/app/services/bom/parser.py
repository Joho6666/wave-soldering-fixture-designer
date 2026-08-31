"""BOM CSV parser. Missing height stays None — never invented."""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


BOM_NAME_HINTS = ("bom", "bill", "物料", "清单", "bomlist")
BOM_EXTENSIONS = {".csv", ".txt"}

REF_KEYS = ("ref", "designator", "reference", "refdes", "qty refs", "位号", "元件位号")
VAL_KEYS = ("value", "val", "comment", "型号", "值", "规格")
PKG_KEYS = ("footprint", "package", "pattern", "封装")
DESC_KEYS = ("description", "desc", "comment", "描述", "说明")
HEIGHT_KEYS = ("height", "body height", "comp height", "z", "高度", "元件高度", "厚度")


@dataclass(frozen=True)
class BomRow:
    refdes_list: tuple[str, ...]
    value: str | None
    footprint: str | None
    description: str | None
    height_mm: float | None
    source_filename: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "refdesList": list(self.refdes_list),
            "value": self.value,
            "footprint": self.footprint,
            "description": self.description,
            "heightMm": self.height_mm,
            "sourceFilename": self.source_filename,
        }


def looks_like_bom_filename(filename: str) -> bool:
    name = PurePosixPath(filename.replace("\\", "/")).name.lower()
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in BOM_EXTENSIONS:
        return False
    if any(h in name for h in ("pnp", "cpl", "centroid", "pick", "place", "pos")):
        return False
    return any(hint in name for hint in BOM_NAME_HINTS)


def parse_bom_bytes(data: bytes, filename: str = "bom.csv") -> list[BomRow]:
    text = _decode(data)
    if not text.strip():
        return []
    sample = text.lstrip("\ufeff")
    delimiter = _detect_delimiter(sample)
    reader = csv.reader(io.StringIO(sample), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if len(rows) < 2:
        return []

    header_idx, mapping = _find_header(rows)
    if mapping is None or "ref" not in mapping:
        return []

    results: list[BomRow] = []
    for row in rows[header_idx + 1 :]:
        if len(row) <= mapping["ref"]:
            continue
        refs = _split_refdes(row[mapping["ref"]])
        if not refs:
            continue
        value = _cell(row, mapping.get("val"))
        footprint = _cell(row, mapping.get("pkg"))
        description = _cell(row, mapping.get("desc"))
        height = None
        if "height" in mapping and mapping["height"] < len(row):
            height = _parse_height(row[mapping["height"]])
        results.append(
            BomRow(
                refdes_list=tuple(refs),
                value=value,
                footprint=footprint,
                description=description,
                height_mm=height,
                source_filename=filename,
            )
        )
    return results


def parse_bom_members(members: list[tuple[str, bytes]]) -> list[BomRow]:
    results: list[BomRow] = []
    for filename, data in members:
        if looks_like_bom_filename(filename):
            results.extend(parse_bom_bytes(data, filename))
    return results


def explode_by_refdes(rows: list[BomRow]) -> dict[str, BomRow]:
    by_ref: dict[str, BomRow] = {}
    for row in rows:
        for ref in row.refdes_list:
            by_ref[ref.upper()] = row
    return by_ref


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk", "cp936", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _detect_delimiter(sample: str) -> str:
    first = next((line for line in sample.splitlines() if line.strip()), "")
    if first.count(";") >= 2 and first.count(";") >= first.count(","):
        return ";"
    if first.count("\t") >= 2:
        return "\t"
    return ","


def _norm(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.strip().lower())


def _find_header(rows: list[list[str]]) -> tuple[int, dict[str, int] | None]:
    for idx, row in enumerate(rows[:12]):
        mapping = _map_columns(row)
        if mapping and "ref" in mapping:
            return idx, mapping
    return 0, None


def _map_columns(header: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    used: set[int] = set()
    norms = [_norm(c) for c in header]
    groups = [
        ("ref", REF_KEYS),
        ("height", HEIGHT_KEYS),
        ("pkg", PKG_KEYS),
        ("val", VAL_KEYS),
        ("desc", DESC_KEYS),
    ]
    for dest, keys in groups:
        for i, name in enumerate(norms):
            if i in used or not name:
                continue
            if any(name == k or k in name for k in keys):
                mapping[dest] = i
                used.add(i)
                break
    return mapping


def _cell(row: list[str], idx: int | None) -> str | None:
    if idx is None or idx >= len(row):
        return None
    text = row[idx].strip()
    return text or None


def _split_refdes(raw: str) -> list[str]:
    parts = re.split(r"[\s,;]+", raw.strip())
    return [p for p in parts if p and not p.lower() in {"ref", "designator"}]


def _parse_height(raw: str) -> float | None:
    text = raw.strip().lower().replace(",", ".")
    if not text or text in {"n/a", "na", "-", "none", "null"}:
        return None
    unit = "mm"
    if "mil" in text:
        unit = "mil"
    number = re.sub(r"[^0-9.+-]", "", text)
    if not number:
        return None
    try:
        value = float(number)
    except ValueError:
        return None
    if unit == "mil":
        value *= 0.0254
    if value <= 0:
        return None
    return round(value, 4)
