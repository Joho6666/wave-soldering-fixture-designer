"""Pick-and-place / centroid parser (CSV / TXT). Height is never invented."""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


PNP_NAME_HINTS = (
    "pnp",
    "cpl",
    "pick",
    "place",
    "centroid",
    "pickandplace",
    "pick-and-place",
    "placement",
    "坐标",
    "贴片",
    "位号",
)

PNP_EXTENSIONS = {".csv", ".txt", ".pos"}

REF_KEYS = ("ref", "designator", "reference", "refdes", "part", "位号", "元件位号", "编号")
X_KEYS = ("mid x", "posx", "pos x", "centerx", "center x", "x (mm)", "x(mm)", "x (mil)", "x(mil)", "x")
Y_KEYS = ("mid y", "posy", "pos y", "centery", "center y", "y (mm)", "y(mm)", "y (mil)", "y(mil)", "y")
ROT_KEYS = ("rotation", "rot", "angle", "theta", "方向", "角度")
SIDE_KEYS = ("layer", "side", "top/bottom", "tb", "面", "层")
PKG_KEYS = ("package", "footprint", "pattern", "封装", "封装名")
VAL_KEYS = ("value", "val", "comment", "val.", "型号", "值")
UNIT_KEYS = ("unit", "units", "单位")


@dataclass(frozen=True)
class PnPPlacement:
    refdes: str
    x_mm: float
    y_mm: float
    rotation: float | None
    side: str
    footprint: str | None
    value: str | None
    source_filename: str
    unit_in_file: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "refdes": self.refdes,
            "xMm": self.x_mm,
            "yMm": self.y_mm,
            "rotation": self.rotation,
            "side": self.side,
            "footprint": self.footprint,
            "value": self.value,
            "sourceFilename": self.source_filename,
            "unitInFile": self.unit_in_file,
        }


def looks_like_pnp_filename(filename: str) -> bool:
    name = PurePosixPath(filename.replace("\\", "/")).name.lower()
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in PNP_EXTENSIONS and suffix not in {".csv", ".txt"}:
        return False
    stem = PurePosixPath(name).stem.lower()
    if stem in {"pos", "xy"} or stem.endswith("-pos") or stem.endswith("_pos"):
        return True
    return any(hint in name for hint in PNP_NAME_HINTS)


def parse_pnp_bytes(data: bytes, filename: str = "pnp.csv") -> list[PnPPlacement]:
    text = _decode(data)
    if not text.strip():
        return []
    sample = text.lstrip("\ufeff")
    delimiter = _detect_delimiter(sample)
    reader = csv.reader(io.StringIO(sample), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if len(rows) < 2:
        return []

    header_idx, mapping, file_unit = _find_header(rows)
    if mapping is None or "ref" not in mapping or "x" not in mapping or "y" not in mapping:
        return []

    placements: list[PnPPlacement] = []
    seen: set[str] = set()
    for row in rows[header_idx + 1 :]:
        if len(row) <= max(mapping.values()):
            continue
        ref = row[mapping["ref"]].strip()
        if not ref or ref.startswith("#") or ref.lower() in {"ref", "designator", "reference"}:
            continue
        try:
            x_raw = _parse_number(row[mapping["x"]])
            y_raw = _parse_number(row[mapping["y"]])
        except ValueError:
            continue

        unit = file_unit
        if "unit" in mapping and mapping["unit"] < len(row) and row[mapping["unit"]].strip():
            unit = _normalize_unit(row[mapping["unit"]]) or unit
        x_mm, y_mm = _to_mm(x_raw, unit), _to_mm(y_raw, unit)

        rotation = None
        if "rot" in mapping and mapping["rot"] < len(row):
            try:
                rotation = _parse_number(row[mapping["rot"]])
            except ValueError:
                rotation = None

        side = "unknown"
        if "side" in mapping and mapping["side"] < len(row):
            side = _normalize_side(row[mapping["side"]])

        footprint = None
        if "pkg" in mapping and mapping["pkg"] < len(row):
            footprint = row[mapping["pkg"]].strip() or None
        value = None
        if "val" in mapping and mapping["val"] < len(row):
            value = row[mapping["val"]].strip() or None

        key = ref.upper()
        if key in seen:
            continue
        seen.add(key)
        placements.append(
            PnPPlacement(
                refdes=ref,
                x_mm=round(x_mm, 4),
                y_mm=round(y_mm, 4),
                rotation=rotation,
                side=side,
                footprint=footprint,
                value=value,
                source_filename=filename,
                unit_in_file=unit,
            )
        )
    return placements


def parse_pnp_members(members: list[tuple[str, bytes]]) -> list[PnPPlacement]:
    results: list[PnPPlacement] = []
    for filename, data in members:
        if looks_like_pnp_filename(filename):
            results.extend(parse_pnp_bytes(data, filename))
    return results


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
    if first.count(",") >= 2:
        return ","
    return ","


def _norm(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.strip().lower())


def _find_header(rows: list[list[str]]) -> tuple[int, dict[str, int] | None, str]:
    for idx, row in enumerate(rows[:12]):
        mapping = _map_columns(row)
        if mapping and "ref" in mapping and "x" in mapping and "y" in mapping:
            joined = " ".join(_norm(c) for c in row)
            unit = "mil" if "mil" in joined and "mm" not in joined else "mm"
            return idx, mapping, unit
    return 0, None, "mm"


def _map_columns(header: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    used: set[int] = set()
    norms = [_norm(c) for c in header]
    groups = [
        ("ref", REF_KEYS),
        ("x", X_KEYS),
        ("y", Y_KEYS),
        ("rot", ROT_KEYS),
        ("side", SIDE_KEYS),
        ("pkg", PKG_KEYS),
        ("val", VAL_KEYS),
        ("unit", UNIT_KEYS),
    ]
    for dest, keys in groups:
        for i, name in enumerate(norms):
            if i in used or not name:
                continue
            if any(name == k or name.startswith(k + " ") or k in name.split() or name == k for k in keys):
                mapping[dest] = i
                used.add(i)
                break
            if dest in {"x", "y"} and name in keys:
                mapping[dest] = i
                used.add(i)
                break
    # exact short names last-resort
    for i, name in enumerate(norms):
        if i in used:
            continue
        if name == "x" and "x" not in mapping:
            mapping["x"] = i
            used.add(i)
        elif name == "y" and "y" not in mapping:
            mapping["y"] = i
            used.add(i)
    return mapping


def _parse_number(raw: str) -> float:
    text = raw.strip().replace(",", ".")
    text = re.sub(r"[^0-9.+-]", "", text)
    if text in {"", "+", "-", ".", "+.", "-."}:
        raise ValueError(raw)
    return float(text)


def _normalize_unit(raw: str) -> str | None:
    text = raw.strip().lower()
    if "mil" in text:
        return "mil"
    if "mm" in text or "milli" in text:
        return "mm"
    return None


def _to_mm(value: float, unit: str) -> float:
    if unit == "mil":
        return value * 0.0254
    return value


def _normalize_side(raw: str) -> str:
    text = raw.strip().lower()
    if text in {"t", "top", "front", "f", "1", "顶", "正面", "顶层"}:
        return "top"
    if text in {"b", "bot", "bottom", "back", "2", "底", "背面", "底层"}:
        return "bottom"
    if "top" in text or "front" in text:
        return "top"
    if "bot" in text or "back" in text:
        return "bottom"
    return "unknown"
