"""Deterministic fixture geometry generator — orchestration only."""
from __future__ import annotations

import hashlib
from typing import Any

from shapely import make_valid, normalize, to_wkb
from shapely.geometry import Polygon, box

from app.models.geometry import FixtureGeometry, PCBGeometry
from app.services.fixture.drc import run_drc
from app.services.fixture.fixture_body_generator import (
    fixture_body,
    generate_sink_region_with_relief,
    handholds,
    rails_and_barriers,
)
from app.services.fixture.keepout_generator import generate_keepouts
from app.services.fixture.locating_pin_optimizer import generate_locating_pins
from app.services.fixture.mounting_generator import clamp_holes, front_panel_spring_clips
from app.services.fixture.semantic_adapter import ensure_semantic
from app.services.fixture.solder_optimizer import generate_solder_openings
from app.services.rules.process_profile import ProcessProfile


class FixtureGenerationError(ValueError):
    pass


class FixtureGenerator:
    def __init__(self, pcb_analysis: dict[str, Any]):
        self.pcb: PCBGeometry | None = pcb_analysis.get("pcb_geometry")
        if self.pcb is None or self.pcb.outline is None or self.pcb.outline.is_empty:
            raise FixtureGenerationError("缺少真实 PCBGeometry，禁止使用估算外形生成治具。")

    def generate(
        self,
        parameters: dict[str, Any],
        review_actions: dict[str, str] | None = None,
        manual_pins: list[str] | None = None,
        custom_regions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        params = self._parameters(parameters)
        ensure_semantic(self.pcb)

        sink_region = generate_sink_region_with_relief(self.pcb.outline, params)
        if sink_region.is_empty or not sink_region.is_valid:
            raise FixtureGenerationError("PCB 外形偏移后无法形成有效沉板区。")

        body = fixture_body(sink_region, params)
        handhold_regions = handholds(sink_region, params)
        clamp = clamp_holes(sink_region, params)
        rails, barriers, barrier_mount_holes = rails_and_barriers(body, params)

        locating_candidates, locating_pins, locating_review = generate_locating_pins(
            self.pcb, params, manual_pins, review_actions
        )
        keepouts, keepout_review, keepout_meta = generate_keepouts(self.pcb, params, review_actions)
        solder_regions, solder_review, solder_meta = generate_solder_openings(self.pcb, params, review_actions)
        spring_clips, spring_clip_review = front_panel_spring_clips(self.pcb, params, review_actions)

        # Re-score pins against generated keepout/solder/clamp only when auto-selecting.
        # Manual pin choices are never silently replaced.
        if not manual_pins:
            locating_candidates, locating_pins, locating_review = generate_locating_pins(
                self.pcb,
                params,
                manual_pins,
                review_actions,
                keepouts=keepouts,
                solder_regions=solder_regions,
                clamp_holes=clamp,
            )

        if custom_regions:
            from app.models.geometry import FixtureRegion
            for idx, cr in enumerate(custom_regions):
                cx = float(cr.get("x", 0.0))
                cy = float(cr.get("y", 0.0))
                w = float(cr.get("width", 10.0))
                h = float(cr.get("height", 10.0))
                rtype = cr.get("regionType", "keepout")
                poly = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                if poly.is_empty:
                    continue
                label = str(cr.get("label") or f"custom-{idx + 1}")
                meta = FixtureRegion(
                    id=f"custom-{idx + 1}",
                    region_type="custom",
                    geometry=poly,
                    source_type="manual",
                    source_ids=(label,),
                    confidence=1.0,
                    manual_override=True,
                    parameters={"sourceType": "manual", "regionType": rtype},
                )
                if rtype == "keepout":
                    keepouts.append(poly)
                    keepout_meta.append(meta)
                elif rtype == "solder":
                    solder_regions.append(poly)
                    solder_meta.append(meta)

        review_items = [*locating_review, *keepout_review, *solder_review, *spring_clip_review]
        pending_mandatory_reviews = [
            r for r in review_items if r.get("mandatory", True) and r.get("status") == "pending"
        ]

        provisional = FixtureGeometry(
            pcb=self.pcb,
            body=body,
            sink_region=sink_region,
            keepout_regions=keepouts,
            solder_regions=solder_regions,
            locating_pins=locating_pins,
            locating_pin_candidates=locating_candidates,
            clamp_holes=clamp,
            handholds=handhold_regions,
            rails=rails,
            solder_barriers=barriers,
            solder_barrier_mount_holes=barrier_mount_holes,
            spring_clip_holes=spring_clips,
            drc_issues=[],
            review_items=review_items,
            parameters=params,
            geometry_sha256="",
            keepout_region_meta=keepout_meta,
            solder_region_meta=solder_meta,
        )
        provisional.drc_issues = run_drc(provisional)
        provisional.geometry_sha256 = self._geometry_digest(provisional)

        status = "review_required" if len(pending_mandatory_reviews) > 0 else "completed"
        region_audit = [m.to_dict() for m in keepout_meta] + [m.to_dict() for m in solder_meta]

        return {
            "fixture_geometry": provisional,
            "pcb_outline": self.pcb.outline,
            "fixture_outline": body,
            "sink_area": sink_region,
            "keepout_zones": keepouts,
            "solder_windows": solder_regions,
            "pins": locating_pins,
            "locating_candidates": locating_candidates,
            "clips": clamp,
            "handholds": handhold_regions,
            "rails": rails,
            "solder_barriers": barriers,
            "solder_barrier_mount_holes": barrier_mount_holes,
            "spring_clips": spring_clips,
            "issues": provisional.drc_issues,
            "reviewItems": review_items,
            "status": status,
            "fixtureWidth": provisional.width,
            "fixtureHeight": provisional.height,
            "geometrySha256": provisional.geometry_sha256,
            "regionAudit": region_audit,
            "featureSummary": {
                "sinkRegionCount": 1,
                "keepoutRegionCount": len(keepouts),
                "solderWindowCount": len(solder_regions),
                "locatingPinCount": len(locating_pins),
                "locatingCandidateCount": len(locating_candidates),
                "clampCount": len(clamp),
                "barrierMountHoleCount": len(barrier_mount_holes),
                "springClipCount": len(spring_clips),
                "semanticComponentCount": len(self.pcb.components or []),
                "throughHoleComponentCount": len(self.pcb.through_hole_components or []),
            },
        }

    def _parameters(self, supplied: dict[str, Any]) -> dict[str, Any]:
        return ProcessProfile.from_dict(supplied).to_dict()

    # Thin wrappers kept for existing unit tests that call private methods.
    def _generate_sink_region_with_relief(self, outline: Polygon, params: dict[str, Any]) -> Polygon:
        return generate_sink_region_with_relief(outline, params)

    def _fixture_body(self, sink_region: Polygon, params: dict[str, Any]) -> Polygon:
        return fixture_body(sink_region, params)

    def _handholds(self, sink_region: Polygon, params: dict[str, Any]) -> list[Polygon]:
        return handholds(sink_region, params)

    def _clamp_holes(self, sink_region: Polygon, params: dict[str, Any]) -> list[dict[str, Any]]:
        return clamp_holes(sink_region, params)

    def _rails_and_barriers(self, body: Polygon, params: dict[str, Any]):
        return rails_and_barriers(body, params)

    def _locating_pin_candidates(
        self,
        params: dict[str, Any],
        manual_pins: list[str] | None = None,
        review_actions: dict[str, str] | None = None,
    ):
        merged = self._parameters(params)
        return generate_locating_pins(self.pcb, merged, manual_pins, review_actions)

    def _bottom_keepouts(self, params: dict[str, Any], review_actions: dict[str, str] | None = None):
        merged = self._parameters(params)
        keepouts, reviews, _meta = generate_keepouts(self.pcb, merged, review_actions)
        return keepouts, reviews

    def _solder_regions(self, params: dict[str, Any], review_actions: dict[str, str] | None = None):
        merged = self._parameters(params)
        regions, reviews, _meta = generate_solder_openings(self.pcb, merged, review_actions)
        return regions, reviews

    def _front_panel_spring_clips(self, params: dict[str, Any], review_actions: dict[str, str] | None = None):
        merged = self._parameters(params)
        return front_panel_spring_clips(self.pcb, merged, review_actions)

    def _geometry_digest(self, fixture: FixtureGeometry) -> str:
        h = hashlib.sha256()
        h.update(to_wkb(normalize(make_valid(fixture.body)), hex=False))
        h.update(to_wkb(normalize(make_valid(fixture.sink_region)), hex=False))
        sorted_pins = sorted(fixture.locating_pins, key=lambda p: (p["x"], p["y"]))
        for pin in sorted_pins:
            h.update(f"{pin['x']}:{pin['y']}:{pin['diameter']}".encode("utf-8"))
        sorted_clamps = sorted(fixture.clamp_holes, key=lambda c: (c["x"], c["y"]))
        for clip in sorted_clamps:
            h.update(f"{clip['x']}:{clip['y']}:{clip['diameter']}".encode("utf-8"))
        sorted_springs = sorted(getattr(fixture, "spring_clip_holes", []), key=lambda s: (s["x"], s["y"]))
        for sp in sorted_springs:
            h.update(f"{sp['x']}:{sp['y']}:{sp['diameter']}".encode("utf-8"))
        sorted_keepouts = sorted(
            [kz for kz in fixture.keepout_regions if not kz.is_empty],
            key=lambda k: (k.centroid.x, k.centroid.y),
        )
        for kz in sorted_keepouts:
            h.update(to_wkb(normalize(make_valid(kz)), hex=False))
        sorted_solders = sorted(
            [sw for sw in fixture.solder_regions if not sw.is_empty],
            key=lambda s: (s.centroid.x, s.centroid.y),
        )
        for sw in sorted_solders:
            h.update(to_wkb(normalize(make_valid(sw)), hex=False))
        return h.hexdigest()
