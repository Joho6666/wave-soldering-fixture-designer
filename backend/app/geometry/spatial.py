"""Spatial index helpers — avoid unbounded O(n²) polygon scans."""
from __future__ import annotations

from typing import Iterable, Sequence

from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.strtree import STRtree


def query_intersects(geoms: Sequence[BaseGeometry], target: BaseGeometry) -> list[tuple[int, BaseGeometry]]:
    if target is None or target.is_empty or not geoms:
        return []
    tree = STRtree(list(geoms))
    indexes = tree.query(target)
    if hasattr(indexes, "tolist"):
        indexes = indexes.tolist()
    hits: list[tuple[int, BaseGeometry]] = []
    for raw in indexes:
        idx = int(raw)
        if idx < 0 or idx >= len(geoms):
            continue
        candidate = geoms[idx]
        if candidate is None or candidate.is_empty:
            continue
        if candidate.intersects(target):
            hits.append((idx, candidate))
    return hits


def prepared_union(geoms: Iterable[BaseGeometry]) -> tuple[BaseGeometry | None, object | None]:
    items = [g for g in geoms if g is not None and not g.is_empty]
    if not items:
        return None, None
    merged = unary_union(items)
    return merged, prep(merged)
