"""Unified 2D rigid transform: mirror → rotate → translate.

All PCB instance / panel / fixture coordinate conversions must go through
this type. Do not sprinkle ad-hoc ``x + offset`` in feature generators.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from shapely.affinity import rotate, scale, translate
from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class Transform2D:
    """Local → global: optional mirror across Y, CCW rotation about origin, then translation."""

    tx: float = 0.0
    ty: float = 0.0
    rotation_deg: float = 0.0
    mirror_x: bool = False

    @classmethod
    def identity(cls) -> Transform2D:
        return cls()

    @classmethod
    def translation(cls, tx: float, ty: float) -> Transform2D:
        return cls(tx=float(tx), ty=float(ty))

    def apply_xy(self, x: float, y: float) -> tuple[float, float]:
        if self.mirror_x:
            x = -x
        rad = math.radians(self.rotation_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        xr = cos_a * x - sin_a * y
        yr = sin_a * x + cos_a * y
        return xr + self.tx, yr + self.ty

    def inverse_xy(self, x: float, y: float) -> tuple[float, float]:
        x = x - self.tx
        y = y - self.ty
        rad = math.radians(-self.rotation_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        xr = cos_a * x - sin_a * y
        yr = sin_a * x + cos_a * y
        if self.mirror_x:
            xr = -xr
        return xr, yr

    def local_to_global(self, x: float, y: float) -> tuple[float, float]:
        return self.apply_xy(x, y)

    def global_to_local(self, x: float, y: float) -> tuple[float, float]:
        return self.inverse_xy(x, y)

    def apply(self, geom: BaseGeometry) -> BaseGeometry:
        if geom is None or geom.is_empty:
            return geom
        g = geom
        if self.mirror_x:
            g = scale(g, xfact=-1.0, yfact=1.0, origin=(0.0, 0.0))
        if abs(self.rotation_deg) > 1e-12:
            g = rotate(g, self.rotation_deg, origin=(0.0, 0.0), use_radians=False)
        if abs(self.tx) > 1e-15 or abs(self.ty) > 1e-15:
            g = translate(g, xoff=self.tx, yoff=self.ty)
        return g

    def inverse(self) -> Transform2D:
        ix, iy = self.inverse_xy(0.0, 0.0)
        return Transform2D(tx=ix, ty=iy, rotation_deg=-self.rotation_deg, mirror_x=self.mirror_x)

    def apply_hole(self, hole: dict[str, Any]) -> dict[str, Any]:
        x, y = self.apply_xy(float(hole["x"]), float(hole["y"]))
        out = dict(hole)
        out["x"] = x
        out["y"] = y
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "tx": self.tx,
            "ty": self.ty,
            "rotationDeg": self.rotation_deg,
            "mirrorX": self.mirror_x,
        }
