"""ProcessProfile — single source of manufacturing numeric defaults.

Values match the v0.4 FixtureParameters / FixtureGenerator defaults so existing
jobs keep the same 2D geometry unless an engineer overrides them. New fields
are software defaults, not claimed industry standards.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Literal


WaveDirection = Literal["+X", "-X", "+Y", "-Y"]


@dataclass(frozen=True)
class ProcessProfile:
    # Fixture body
    palletThicknessMm: float = 10.0
    fixtureMarginXmm: float = 20.0
    fixtureMarginYmm: float = 30.0
    fixtureCornerRadiusMm: float = 5.0
    minimumMaterialWebMm: float = 2.0
    fixtureSizeRoundStepMm: float = 5.0
    sinkClearanceMm: float = 0.2
    filletRadiusMm: float = 1.85
    railWidthMm: float = 5.0
    solderBarrierWidthMm: float = 10.0
    barrierMountHoleDiameterMm: float = 3.2
    clampHoleDiameterMm: float = 3.4
    clampOffsetMm: float = 10.0
    clampPinClearanceMm: float = 10.0
    handholdWidthMm: float = 20.0
    handholdHeightMm: float = 40.0
    handholdOverlapMm: float = 1.0
    handholdCornerRadiusMm: float = 2.0
    springClipRadiusMm: float = 2.45

    # Pocket / keepout
    keepoutClearanceMm: float = 0.7
    keepoutInnerFilletMm: float = 1.5
    componentVerticalClearanceMm: float = 0.5
    pocketFloorThicknessMm: float = 2.0
    defaultPocketDepthMm: float = 2.0

    # Solder openings
    solderClearanceMm: float = 3.0
    solderMinOuterDiameterMm: float = 3.0
    solderMinOpeningWidthMm: float = 1.5
    solderOpeningMergeDistanceMm: float = 2.0

    # Locating pins
    minPinHoleDiameterMm: float = 2.0
    maxPinHoleDiameterMm: float = 4.5
    preferredPinDiameterMinMm: float = 2.5
    preferredPinDiameterMaxMm: float = 4.5
    preferredNPTH: bool = True
    minPinSeparationMm: float = 15.0
    pinEdgeBonusMm: float = 15.0
    pinDiameterOffsetMm: float = 0.1
    pinDiameterMinMm: float = 1.5
    pinDiameterMaxMm: float = 4.0

    # Machine (stored, not consumed by opening algorithm this round)
    waveDirection: WaveDirection = "+X"
    conveyorDirection: WaveDirection = "+X"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, supplied: dict[str, Any] | None) -> ProcessProfile:
        if not supplied:
            return cls()
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            if f.name not in supplied:
                continue
            raw = supplied[f.name]
            if f.type is bool or f.type == "bool":
                kwargs[f.name] = bool(raw)
            elif f.name in {"waveDirection", "conveyorDirection"}:
                value = str(raw)
                if value in {"+X", "-X", "+Y", "-Y"}:
                    kwargs[f.name] = value
            else:
                try:
                    kwargs[f.name] = float(raw)
                except (TypeError, ValueError):
                    continue
        return cls(**kwargs)
