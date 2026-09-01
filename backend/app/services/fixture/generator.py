"""Deterministic fixture geometry generator — orchestration only."""
from __future__ import annotations

from typing import Any

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from app.geometry.digest import geometry_digest
from app.models.geometry import FixtureGeometry, FixtureRegion, PCBGeometry
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
from app.services.fixture.pressure_relief import generate_pressure_relief
from app.services.fixture.semantic_adapter import ensure_semantic
from app.services.fixture.solder_optimizer import generate_solder_openings
from app.services.panel.grid import build_grid_panel
from app.services.rules.process_profile import ProcessProfile


class FixtureGenerationError(ValueError):
    pass


def _copy_hole(hole: dict[str, Any], transform) -> dict[str, Any]:
    return transform.apply_hole(hole)


def _copy_region_meta(meta: FixtureRegion, geom, suffix: str) -> FixtureRegion:
    return FixtureRegion(
        id=f"{meta.id}-{suffix}",
        region_type=meta.region_type,
        geometry=geom,
        source_type=meta.source_type,
        source_ids=tuple(f"{s}:{suffix}" for s in meta.source_ids) if meta.source_ids else (suffix,),
        confidence=meta.confidence,
        manual_override=meta.manual_override,
        parameters=dict(meta.parameters or {}),
    )


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

        panel = build_grid_panel(self.pcb, params)
        if panel is not None:
            return self._generate_panel(params, panel, review_actions, manual_pins, custom_regions)
        return self._generate_single(params, review_actions, manual_pins, custom_regions, working_pcb=self.pcb)

    def _generate_single(
        self,
        params: dict[str, Any],
        review_actions: dict[str, str] | None,
        manual_pins: list[str] | None,
        custom_regions: list[dict[str, Any]] | None,
        working_pcb: PCBGeometry,
        panel=None,
        tooling_holes: list[dict[str, Any]] | None = None,
        fiducials: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        sink_region = generate_sink_region_with_relief(working_pcb.outline, params)
        if sink_region.is_empty or not sink_region.is_valid:
            raise FixtureGenerationError("PCB 外形偏移后无法形成有效沉板区。")

        body = fixture_body(sink_region, params)
        handhold_regions = handholds(sink_region, params)
        clamp = clamp_holes(sink_region, params)
        rails, barriers, barrier_mount_holes = rails_and_barriers(body, params)

        locating_candidates, locating_pins, locating_review = generate_locating_pins(
            working_pcb, params, manual_pins, review_actions
        )
        keepouts, keepout_review, keepout_meta = generate_keepouts(working_pcb, params, review_actions)
        solder_regions, solder_review, solder_meta = generate_solder_openings(working_pcb, params, review_actions)
        spring_clips, spring_clip_review = front_panel_spring_clips(working_pcb, params, review_actions)

        if not manual_pins:
            locating_candidates, locating_pins, locating_review = generate_locating_pins(
                working_pcb,
                params,
                manual_pins,
                review_actions,
                keepouts=keepouts,
                solder_regions=solder_regions,
                clamp_holes=clamp,
            )

        if custom_regions:
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

        relief_channels, relief_meta = generate_pressure_relief(
            body=body,
            pcb_outline=working_pcb.outline,
            keepouts=keepouts,
            keepout_meta=keepout_meta,
            solder_regions=solder_regions,
            locating_pins=locating_pins,
            clamp_holes=clamp,
            params=params,
        )

        review_items = [*locating_review, *keepout_review, *solder_review, *spring_clip_review]
        pending_mandatory_reviews = [
            r for r in review_items if r.get("mandatory", True) and r.get("status") == "pending"
        ]

        provisional = FixtureGeometry(
            pcb=working_pcb,
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
            drc_issues=[],
            review_items=review_items,
            parameters=params,
            geometry_sha256="",
            spring_clip_holes=spring_clips,
            keepout_region_meta=keepout_meta,
            solder_region_meta=solder_meta,
            pressure_relief_channels=relief_channels,
            pressure_relief_meta=relief_meta,
            tooling_holes=tooling_holes or [],
            fiducials=fiducials or [],
            panel=panel,
        )
        provisional.drc_issues = run_drc(provisional)
        provisional.geometry_sha256 = self._geometry_digest(provisional)

        status = "review_required" if len(pending_mandatory_reviews) > 0 else "completed"
        region_audit = (
            [m.to_dict() for m in keepout_meta]
            + [m.to_dict() for m in solder_meta]
            + [m.to_dict() for m in relief_meta]
        )

        return {
            "fixture_geometry": provisional,
            "pcb_outline": working_pcb.outline,
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
            "pressure_relief_channels": relief_channels,
            "tooling_holes": tooling_holes or [],
            "fiducials": fiducials or [],
            "panel": panel.to_dict() if panel is not None else None,
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
                "pressureReliefCount": len(relief_channels),
                "panelInstanceCount": len(panel.pcb_instances) if panel is not None else 1,
                "semanticComponentCount": len(working_pcb.components or []),
                "throughHoleComponentCount": len(working_pcb.through_hole_components or []),
            },
        }

    def _generate_panel(
        self,
        params: dict[str, Any],
        panel,
        review_actions: dict[str, str] | None,
        manual_pins: list[str] | None,
        custom_regions: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Generate per-instance features, then one shared fixture body around the panel."""
        local = self._generate_single(
            params,
            review_actions,
            manual_pins,
            custom_regions,
            working_pcb=self.pcb,
            panel=None,
        )
        local_fix: FixtureGeometry = local["fixture_geometry"]

        keepouts: list = []
        keepout_meta: list[FixtureRegion] = []
        solders: list = []
        solder_meta: list[FixtureRegion] = []
        pins: list[dict[str, Any]] = []
        pin_candidates: list[dict[str, Any]] = []
        clamps: list[dict[str, Any]] = []
        springs: list[dict[str, Any]] = []
        outlines = []
        sink_parts = []

        for inst in panel.pcb_instances:
            tf = inst.transform
            outlines.append(tf.apply(self.pcb.outline))
            sink_parts.append(tf.apply(local_fix.sink_region))
            for g, meta in zip(local_fix.keepout_regions, local_fix.keepout_region_meta or [None] * len(local_fix.keepout_regions)):
                gg = tf.apply(g)
                keepouts.append(gg)
                if meta is not None:
                    keepout_meta.append(_copy_region_meta(meta, gg, inst.id))
            for g, meta in zip(local_fix.solder_regions, local_fix.solder_region_meta or [None] * len(local_fix.solder_regions)):
                gg = tf.apply(g)
                solders.append(gg)
                if meta is not None:
                    solder_meta.append(_copy_region_meta(meta, gg, inst.id))
            for pin in local_fix.locating_pins:
                copied = _copy_hole(pin, tf)
                copied["id"] = f"{pin.get('id', 'pin')}-{inst.id}"
                pins.append(copied)
            for cand in local_fix.locating_pin_candidates:
                copied = dict(cand)
                x, y = tf.apply_xy(float(cand["x"]), float(cand["y"]))
                copied["x"] = x
                copied["y"] = y
                copied["id"] = f"{cand.get('id', 'cand')}-{inst.id}"
                pin_candidates.append(copied)
            for clamp in local_fix.clamp_holes:
                copied = _copy_hole(clamp, tf)
                copied["id"] = f"{clamp.get('id', 'clamp')}-{inst.id}"
                clamps.append(copied)
            for sp in local_fix.spring_clip_holes:
                copied = _copy_hole(sp, tf)
                copied["id"] = f"{sp.get('id', 'spring')}-{inst.id}"
                springs.append(copied)

        combined_outline = unary_union(outlines)
        combined_sink = unary_union(sink_parts)
        envelope = unary_union([combined_sink, panel.outline])
        body = fixture_body(envelope, params)
        handhold_regions = handholds(combined_sink, params)
        rails, barriers, barrier_mount_holes = rails_and_barriers(body, params)

        working = PCBGeometry(
            outline=combined_outline,
            holes=list(self.pcb.holes),
            layers=list(self.pcb.layers),
            source_sha256=self.pcb.source_sha256,
            geometry_sha256=self.pcb.geometry_sha256,
            components=list(self.pcb.components or []),
            pads=list(self.pcb.pads or []),
            through_hole_components=list(self.pcb.through_hole_components or []),
            semantic_conflicts=list(self.pcb.semantic_conflicts or []),
        )

        relief_channels, relief_meta = generate_pressure_relief(
            body=body,
            pcb_outline=combined_outline,
            keepouts=keepouts,
            keepout_meta=keepout_meta,
            solder_regions=solders,
            locating_pins=pins,
            clamp_holes=clamps,
            params=params,
        )

        review_items = list(local_fix.review_items)
        pending_mandatory_reviews = [
            r for r in review_items if r.get("mandatory", True) and r.get("status") == "pending"
        ]
        provisional = FixtureGeometry(
            pcb=working,
            body=body,
            sink_region=combined_sink,
            keepout_regions=keepouts,
            solder_regions=solders,
            locating_pins=pins,
            locating_pin_candidates=pin_candidates,
            clamp_holes=clamps,
            handholds=handhold_regions,
            rails=rails,
            solder_barriers=barriers,
            solder_barrier_mount_holes=barrier_mount_holes,
            drc_issues=[],
            review_items=review_items,
            parameters=params,
            geometry_sha256="",
            spring_clip_holes=springs,
            keepout_region_meta=keepout_meta,
            solder_region_meta=solder_meta,
            pressure_relief_channels=relief_channels,
            pressure_relief_meta=relief_meta,
            tooling_holes=list(panel.tooling_holes),
            fiducials=list(panel.fiducials),
            panel=panel,
        )
        provisional.drc_issues = run_drc(provisional)
        provisional.geometry_sha256 = self._geometry_digest(provisional)
        status = "review_required" if len(pending_mandatory_reviews) > 0 else "completed"
        region_audit = (
            [m.to_dict() for m in keepout_meta]
            + [m.to_dict() for m in solder_meta]
            + [m.to_dict() for m in relief_meta]
        )
        return {
            "fixture_geometry": provisional,
            "pcb_outline": combined_outline,
            "fixture_outline": body,
            "sink_area": combined_sink,
            "keepout_zones": keepouts,
            "solder_windows": solders,
            "pins": pins,
            "locating_candidates": pin_candidates,
            "clips": clamps,
            "handholds": handhold_regions,
            "rails": rails,
            "solder_barriers": barriers,
            "solder_barrier_mount_holes": barrier_mount_holes,
            "spring_clips": springs,
            "pressure_relief_channels": relief_channels,
            "tooling_holes": list(panel.tooling_holes),
            "fiducials": list(panel.fiducials),
            "panel": panel.to_dict(),
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
                "solderWindowCount": len(solders),
                "locatingPinCount": len(pins),
                "locatingCandidateCount": len(pin_candidates),
                "clampCount": len(clamps),
                "barrierMountHoleCount": len(barrier_mount_holes),
                "springClipCount": len(springs),
                "pressureReliefCount": len(relief_channels),
                "panelInstanceCount": len(panel.pcb_instances),
                "semanticComponentCount": len(self.pcb.components or []),
                "throughHoleComponentCount": len(self.pcb.through_hole_components or []),
            },
        }

    def _parameters(self, supplied: dict[str, Any]) -> dict[str, Any]:
        return ProcessProfile.from_dict(supplied).to_dict()

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
        return geometry_digest(fixture)
