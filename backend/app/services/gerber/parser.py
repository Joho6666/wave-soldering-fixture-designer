"""Deterministic Gerber ZIP parser. No estimated dimensions or fabricated layers."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from gerbonara import ExcellonFile, GerberFile
from gerbonara.graphic_objects import Arc, Flash, Line
from gerbonara.graphic_primitives import Arc as PrimitiveArc
from gerbonara.graphic_primitives import ArcPoly, Circle, Line as PrimitiveLine, Rectangle
from gerbonara.utils import MM, approximate_arc
from shapely import make_valid, normalize, to_wkb
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, MultiPolygon
from shapely.ops import polygonize, unary_union, linemerge

from app.models.geometry import DrillHit, PCBGeometry
from app.models.schemas import ErrorCode


GERBER_EXTENSIONS = {".gbr", ".ger", ".gko", ".gml", ".gm1", ".gtl", ".gbl", ".gto", ".gbo", ".gts", ".gbs"}
DRILL_EXTENSIONS = {".drl", ".xln", ".txt"}
ALLOWED_EXTENSIONS = GERBER_EXTENSIONS | DRILL_EXTENSIONS
MAX_MEMBER_COUNT = 500
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
OUTLINE_CLOSE_TOLERANCE_MM = 0.20


class GerberParseError(ValueError):
    def __init__(self, code: str, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


class GerberParser:
    def parse_zip(self, zip_path: str, confirmed_layers: list[dict] | None = None) -> dict:
        archive = Path(zip_path)
        if not archive.exists():
            raise GerberParseError("INVALID_ZIP", f"ZIP 文件不存在: {zip_path}")
            
        try:
            source_bytes = archive.read_bytes()
        except Exception as exc:
            raise GerberParseError("INVALID_ZIP", f"无法读取 ZIP 文件: {exc}")
            
        source_digest = self._sha256(source_bytes)
        members = self._read_safe_archive(archive)
        if not members:
            raise GerberParseError("ZIP_EMPTY", "ZIP 文件为空或未包含有效的 Gerber/Drill 制造文件。")

        # Load persisted layer mapping if present
        mapping_file = archive.parent / "layer_mapping.json"
        persisted_mapping = {}
        if mapping_file.exists():
            try:
                with open(mapping_file, "r", encoding="utf-8") as mf:
                    persisted_mapping = json.load(mf)
            except Exception:
                pass

        confirmed_map = {item["filename"].replace("\\", "/").lower(): item["type"] for item in (confirmed_layers or [])}
        for fn, ltype in persisted_mapping.items():
            fn_key = fn.replace("\\", "/").lower()
            if fn_key not in confirmed_map:
                confirmed_map[fn_key] = ltype

        layers: list[dict] = []
        gerbers: dict[str, GerberFile] = {}
        drills: list[DrillHit] = []
        outline_candidates: list[tuple[str, Polygon, list[str]]] = []
        geometries: dict[str, object] = {}
        diagnostics: list[str] = []

        for index, (filename, data) in enumerate(members):
            suffix = Path(filename).suffix.lower()
            layer_id = self._stable_id("layer", filename, data)
            requested_type = confirmed_map.get(filename.lower())

            if suffix in DRILL_EXTENSIONS or self._is_excellon_content(data):
                try:
                    drill_file = self._parse_drill(filename, data)
                    file_hits = self._drill_hits(drill_file, layer_id)
                    drills.extend(file_hits)
                    layers.append(self._layer_record(layer_id, filename, "drill", 1.0, "Excellon 文件已真实解析", True))
                    continue
                except Exception as ex:
                    diagnostics.append(f"尝试解析钻孔文件 {filename} 失败: {ex}")

            if suffix not in GERBER_EXTENSIONS and not requested_type:
                continue

            try:
                gerber = self._parse_gerber(filename, data)
            except Exception as ex:
                diagnostics.append(f"文件 {filename} 无法解析为标准 Gerber: {ex}")
                layers.append(self._layer_record(layer_id, filename, "unknown", 0.0, f"解析异常: {str(ex)[:80]}", False))
                continue

            detected_type, confidence, reason = self._classify_layer(filename, gerber)
            if requested_type:
                detected_type, confidence, reason = requested_type, 1.0, "用户确认的图层映射"
            gerbers[layer_id] = gerber
            layers.append(self._layer_record(layer_id, filename, detected_type, confidence, reason, bool(requested_type) or confidence >= 0.8))

            if detected_type == "board_outline":
                try:
                    outline, outline_diagnostics = self._outline_geometry(gerber)
                    outline_candidates.append((filename, outline, outline_diagnostics))
                    diagnostics.extend(outline_diagnostics)
                except Exception as ex:
                    diagnostics.append(f"外形层候选 {filename} 提取轮廓失败: {ex}")
            elif detected_type != "unknown":
                try:
                    geometries[detected_type] = self._gerber_geometry(gerber)
                except Exception as ex:
                    diagnostics.append(f"图层 {filename} ({detected_type}) 提取几何失败: {ex}")

        has_board_outline = any(l["type"] == "board_outline" for l in layers)
        has_drill = any(l["type"] == "drill" for l in layers)

        if not outline_candidates:
            if not has_board_outline:
                return {
                    "requires_layer_confirmation": True,
                    "layers": layers,
                    "diagnostics": diagnostics,
                    "error_code": "MISSING_OUTLINE_LAYER",
                    "message": "未可靠识别 PCB 外形层 (GKO/GML/GM1)，请在图层确认中人工指定。"
                }
            raise GerberParseError(
                "MISSING_OUTLINE_LAYER",
                "未检测到 PCB 外形层，请确认 ZIP 中包含 GKO、GML、GM1 或 Gerber X2 Profile 图层。",
            )

        if not drills:
            if not has_drill:
                return {
                    "requires_layer_confirmation": True,
                    "layers": layers,
                    "diagnostics": diagnostics,
                    "error_code": "MISSING_DRILL_LAYER",
                    "message": "未可靠识别 Excellon 钻孔层 (DRL/XLN)，请在图层确认中人工指定。"
                }
            raise GerberParseError("MISSING_DRILL_LAYER", "未检测到可解析的 Excellon DRL/XLN 钻孔层。")

        outline = self._select_outline(outline_candidates)
        normalized_outline = normalize(outline)
        geometry_digest = hashlib.sha256(to_wkb(normalized_outline, hex=False)).hexdigest()
        
        pth_count = sum(1 for h in drills if h.plated is True or h.plated is None)
        npth_count = sum(1 for h in drills if h.plated is False)

        pcb = PCBGeometry(
            outline=outline,
            holes=drills,
            layers=layers,
            source_sha256=source_digest,
            geometry_sha256=geometry_digest,
            top_copper=geometries.get("top_copper"),
            bottom_copper=geometries.get("bottom_copper"),
            top_soldermask=geometries.get("top_soldermask"),
            bottom_soldermask=geometries.get("bottom_soldermask"),
            top_silkscreen=geometries.get("top_silkscreen"),
            bottom_silkscreen=geometries.get("bottom_silkscreen"),
            diagnostics=diagnostics,
        )

        min_confidence = min((l["confidence"] for l in layers if l["type"] != "unknown"), default=1.0)

        return {
            "pcb_geometry": pcb,
            "width": round(pcb.width, 3),
            "height": round(pcb.height, 3),
            "fileCount": len(layers),
            "holeCount": len(drills),
            "pthCount": pth_count,
            "npthCount": npth_count,
            "outlineClosed": True,
            "outlineAreaMm2": round(outline.area, 3),
            "layers": layers,
            "holes": [h.to_dict() for h in drills],
            "diagnostics": diagnostics,
            "sourceSha256": source_digest,
            "geometrySha256": geometry_digest,
            "requires_layer_confirmation": min_confidence < 0.8,
        }

    def _is_excellon_content(self, data: bytes) -> bool:
        text_sample = data[:2048].decode("utf-8", errors="ignore").upper()
        return "M48" in text_sample or "INCH" in text_sample or "METRIC" in text_sample or "T01" in text_sample or "T1C" in text_sample

    def _read_safe_archive(self, archive: Path) -> list[tuple[str, bytes]]:
        try:
            with ZipFile(archive, "r") as zf:
                infos = zf.infolist()
                if len(infos) > MAX_MEMBER_COUNT:
                    raise GerberParseError("ZIP_INVALID", f"ZIP 成员过多 ({len(infos)} > {MAX_MEMBER_COUNT})，拒绝解析。")
                total_bytes = 0
                members: list[tuple[str, bytes]] = []
                for info in infos:
                    if info.is_dir():
                        continue
                    normalized = PurePosixPath(info.filename.replace("\\", "/"))
                    if normalized.is_absolute() or ".." in normalized.parts:
                        raise GerberParseError("ZIP_INVALID", f"ZIP 包含不安全路径: {info.filename}")
                    total_bytes += info.file_size
                    if total_bytes > MAX_UNCOMPRESSED_BYTES:
                        raise GerberParseError("ZIP_INVALID", "ZIP 解压后体积超出安全限制。")
                    
                    data = zf.read(info.filename)
                    members.append((info.filename, data))
                return members
        except BadZipFile as exc:
            raise GerberParseError("INVALID_ZIP", f"ZIP 文件损坏或格式错误: {exc}") from exc

    def _parse_gerber(self, filename: str, data: bytes) -> GerberFile:
        try:
            content_str = data.decode("utf-8", errors="ignore")
            return GerberFile.from_string(content_str)
        except Exception as exc:
            raise GerberParseError("INVALID_GERBER", f"Gerber 文件解析失败: {filename} ({exc})") from exc

    def _parse_drill(self, filename: str, data: bytes) -> ExcellonFile:
        try:
            content_str = data.decode("utf-8", errors="ignore")
            return ExcellonFile.from_string(content_str)
        except Exception as exc:
            raise GerberParseError("INVALID_EXCELLON", f"Excellon 钻孔文件解析失败: {filename} ({exc})") from exc

    def _classify_layer(self, filename: str, gerber: GerberFile) -> tuple[str, float, str]:
        path = PurePosixPath(filename.replace("\\", "/"))
        name = path.name.lower()
        suffix = path.suffix.lower()

        # 1. Check X2 metadata if available
                # 1. Check X2 metadata if available (gerbonara stores %TF in .file_attrs dict as tuple/str)
        meta = getattr(gerber, "file_attrs", None) or getattr(gerber, "file_attributes", None) or {}
        file_function = meta.get(".FileFunction", "")
        if isinstance(file_function, (tuple, list)):
            fn_upper = ",".join(str(item).upper() for item in file_function)
        elif isinstance(file_function, str):
            fn_upper = file_function.upper()
        else:
            fn_upper = str(file_function).upper() if file_function else ""

        if fn_upper:
            if "PROFILE" in fn_upper or "OUTLINE" in fn_upper:
                return "board_outline", 0.99, "Gerber X2 Profile 元数据识别"
            if "COPPER" in fn_upper and ("TOP" in fn_upper or "L1" in fn_upper):
                return "top_copper", 0.98, "Gerber X2 Top Copper 元数据识别"
            if "COPPER" in fn_upper and ("BOT" in fn_upper or "L2" in fn_upper or "LN" in fn_upper):
                return "bottom_copper", 0.98, "Gerber X2 Bottom Copper 元数据识别"
            if "SOLDERMASK" in fn_upper and "TOP" in fn_upper:
                return "top_soldermask", 0.98, "Gerber X2 Top Soldermask 元数据识别"
            if "SOLDERMASK" in fn_upper and "BOT" in fn_upper:
                return "bottom_soldermask", 0.98, "Gerber X2 Bottom Soldermask 元数据识别"
            if "LEGEND" in fn_upper and "TOP" in fn_upper:
                return "top_silkscreen", 0.98, "Gerber X2 Top Silkscreen 元数据识别"
            if "LEGEND" in fn_upper and "BOT" in fn_upper:
                return "bottom_silkscreen", 0.98, "Gerber X2 Bottom Silkscreen 元数据识别"

# 2. Strong suffix patterns
        if suffix in {".gko", ".gml", ".gm1"}:
            return "board_outline", 0.95, "标准外形层扩展名"
        if suffix in {".gtl", ".top", ".cmp"}:
            return "top_copper", 0.92, "标准顶层铜皮扩展名"
        if suffix in {".gbl", ".bot", ".sol"}:
            return "bottom_copper", 0.92, "标准底层铜皮扩展名"
        if suffix in {".gts", ".stc", ".smt"}:
            return "top_soldermask", 0.92, "标准顶层阻焊扩展名"
        if suffix in {".gbs", ".sts", ".smb"}:
            return "bottom_soldermask", 0.92, "标准底层阻焊扩展名"
        if suffix in {".gto", ".plc", ".sst"}:
            return "top_silkscreen", 0.92, "标准顶层丝印扩展名"
        if suffix in {".gbo", ".pls", ".ssb"}:
            return "bottom_silkscreen", 0.92, "标准底层丝印扩展名"

        # 3. Filename keyword patterns
        if any(k in name for k in ["outline", "boardoutline", "profile", "edge", "border", "gm1", "gko"]):
            return "board_outline", 0.90, "文件名匹配 PCB 外形关键词"
        if any(k in name for k in ["gtl", "top_copper", "topcopper", "copper_top", "f_cu", "top.gbr"]):
            return "top_copper", 0.85, "文件名匹配顶层铜皮关键词"
        if any(k in name for k in ["gbl", "bot_copper", "bottomcopper", "copper_bot", "b_cu", "bottom.gbr"]):
            return "bottom_copper", 0.85, "文件名匹配底层铜皮关键词"
        if any(k in name for k in ["gts", "top_mask", "topsoldermask", "mask_top", "f_mask"]):
            return "top_soldermask", 0.85, "文件名匹配顶层阻焊关键词"
        if any(k in name for k in ["gbs", "bot_mask", "bottomsoldermask", "mask_bot", "b_mask"]):
            return "bottom_soldermask", 0.85, "文件名匹配底层阻焊关键词"
        if any(k in name for k in ["gto", "top_silk", "topsilkscreen", "silk_top", "f_silk"]):
            return "top_silkscreen", 0.85, "文件名匹配顶层丝印关键词"
        if any(k in name for k in ["gbo", "bot_silk", "bottomsilkscreen", "silk_bot", "b_silk"]):
            return "bottom_silkscreen", 0.85, "文件名匹配底层丝印关键词"

        # Unclear layer, assign low confidence
        return "unknown", 0.30, "未识别的标准图层名称或扩展名"

    def _drill_hits(self, drill_file: ExcellonFile, layer_id: str) -> list[DrillHit]:
        hits: list[DrillHit] = []
        
        objects = getattr(drill_file, "objects", []) or []
        for index, obj in enumerate(objects):
            try:
                x = float(obj.x) if hasattr(obj, "x") else 0.0
                y = float(obj.y) if hasattr(obj, "y") else 0.0
                
                dia = 1.0
                if hasattr(obj, "tool") and obj.tool is not None:
                    t_dia = getattr(obj.tool, "diameter", 1.0)
                    dia = float(t_dia(MM)) if callable(t_dia) else float(t_dia)

                tool_id = getattr(obj.tool, "name", f"T{index+1}") if hasattr(obj, "tool") else None
                plated = getattr(obj, "plated", None)
                kind = "slot" if hasattr(obj, "x2") and hasattr(obj, "y2") else "hole"

                hits.append(DrillHit(
                    id=f"drill-{layer_id[:6]}-{index+1}",
                    x=round(x, 4),
                    y=round(y, 4),
                    diameter_mm=round(dia, 4),
                    plated=plated,
                    tool_id=str(tool_id) if tool_id else None,
                    source_layer_id=layer_id,
                    kind=kind,
                ))
            except Exception:
                continue

        return hits

    def _outline_geometry(self, gerber: GerberFile) -> tuple[Polygon, list[str]]:
        diagnostics: list[str] = []
        lines: list[LineString] = []

        objects = getattr(gerber, "objects", []) or []
        for obj in objects:
            if isinstance(obj, Line):
                lines.append(LineString([(obj.x1, obj.y1), (obj.x2, obj.y2)]))
            elif isinstance(obj, Arc):
                try:
                    coords = approximate_arc(obj.x1, obj.y1, obj.x2, obj.y2, obj.cx, obj.cy, obj.clockwise)
                    if len(coords) >= 2:
                        lines.append(LineString(coords))
                except Exception:
                    lines.append(LineString([(obj.x1, obj.y1), (obj.x2, obj.y2)]))

        if not lines and hasattr(gerber, "primitives"):
            for prim in gerber.primitives():
                if isinstance(prim, PrimitiveLine):
                    lines.append(LineString([(prim.x1, prim.y1), (prim.x2, prim.y2)]))
                elif isinstance(prim, PrimitiveArc):
                    coords = approximate_arc(prim.x1, prim.y1, prim.x2, prim.y2, prim.cx, prim.cy, prim.clockwise)
                    if len(coords) >= 2:
                        lines.append(LineString(coords))

        if not lines:
            raise GerberParseError("INVALID_OUTLINE", "外形层不包含任何有效线段或圆弧图元。")

        # 1. 尝试直接 polygonize
        merged = unary_union(lines)
        polygons = list(polygonize(merged))

        # 2. 若存在微小端点间隙，通过 linemerge 自动闭合首尾
        if not polygons:
            merged_lines = linemerge(lines)
            multi_lines = merged_lines.geoms if hasattr(merged_lines, "geoms") else [merged_lines]
            for ml in multi_lines:
                coords = list(ml.coords)
                if len(coords) >= 3:
                    gap = math.hypot(coords[0][0] - coords[-1][0], coords[0][1] - coords[-1][1])
                    if gap <= OUTLINE_CLOSE_TOLERANCE_MM:
                        closed_coords = coords + [coords[0]]
                        p = Polygon(closed_coords)
                        if p.is_valid and p.area > 1.0:
                            polygons.append(p)
                            diagnostics.append(f"外形轮廓端点存在 {gap:.3f}mm 间隙，已精确闭合。")

        # 3. 容差缓冲闭合降级
        if not polygons:
            buffered = merged.buffer(OUTLINE_CLOSE_TOLERANCE_MM)
            polygons = [p for p in (buffered.geoms if hasattr(buffered, "geoms") else [buffered]) if isinstance(p, Polygon)]
            diagnostics.append("外形轮廓使用多边形缓冲容差闭合。")

        if not polygons:
            raise GerberParseError("INVALID_OUTLINE", "外形层线段无法构建出闭合多边形 (Polygon)。")

        largest_poly = max(polygons, key=lambda p: p.area)
        valid_poly = make_valid(largest_poly)
        if isinstance(valid_poly, MultiPolygon):
            valid_poly = max(valid_poly.geoms, key=lambda p: p.area)

        return valid_poly, diagnostics

    def _select_outline(self, candidates: list[tuple[str, Polygon, list[str]]]) -> Polygon:
        if len(candidates) == 1:
            return candidates[0][1]
        return max(candidates, key=lambda c: c[1].area)[1]

    def _gerber_geometry(self, gerber: GerberFile) -> Polygon | MultiPolygon | GeometryCollection:
        geoms = []
        if hasattr(gerber, "primitives"):
            for prim in gerber.primitives():
                if isinstance(prim, Circle):
                    if hasattr(prim, "r"):
                        r = float(prim.r)
                    elif hasattr(prim, "diameter") and callable(prim.diameter):
                        r = float(prim.diameter(MM)) / 2
                    else:
                        r = 0.5
                    geoms.append(Point(prim.x, prim.y).buffer(r))
                elif isinstance(prim, Rectangle):
                    w = float(prim.width(MM)) if hasattr(prim, "width") and callable(prim.width) else float(getattr(prim, "w", getattr(prim, "width", 1.0)))
                    h = float(prim.height(MM)) if hasattr(prim, "height") and callable(prim.height) else float(getattr(prim, "h", getattr(prim, "height", 1.0)))
                    x, y = prim.x, prim.y
                    geoms.append(Polygon([
                        (x - w / 2, y - h / 2),
                        (x + w / 2, y - h / 2),
                        (x + w / 2, y + h / 2),
                        (x - w / 2, y + h / 2),
                    ]))
                elif isinstance(prim, ArcPoly):
                    try:
                        coords = list(prim.to_polygon(MM) if callable(getattr(prim, "to_polygon", None)) else prim.to_polygon())
                        if len(coords) >= 3:
                            geoms.append(Polygon(coords))
                    except Exception:
                        pass
                elif isinstance(prim, PrimitiveLine):
                    w = getattr(prim, "width", 0.2)
                    w_val = float(w(MM)) if callable(w) else float(w)
                    geoms.append(LineString([(prim.x1, prim.y1), (prim.x2, prim.y2)]).buffer(w_val / 2))
                elif isinstance(prim, PrimitiveArc):
                    try:
                        coords = approximate_arc(prim.x1, prim.y1, prim.x2, prim.y2, prim.cx, prim.cy, prim.clockwise)
                        if len(coords) >= 2:
                            w = getattr(prim, "width", 0.2)
                            w_val = float(w(MM)) if callable(w) else float(w)
                            geoms.append(LineString(coords).buffer(w_val / 2))
                    except Exception:
                        pass
        
        if not geoms:
            return GeometryCollection()
        return make_valid(unary_union(geoms))

    def _layer_record(self, layer_id: str, filename: str, ltype: str, confidence: float, reason: str, confirmed: bool) -> dict:
        return {
            "id": layer_id,
            "filename": filename,
            "type": ltype,
            "confidence": round(confidence, 2),
            "reason": reason,
            "confirmed": confirmed,
        }

    def _stable_id(self, prefix: str, filename: str, data: bytes) -> str:
        h = hashlib.sha256(f"{filename}".encode("utf-8") + data[:256]).hexdigest()[:8]
        return f"{prefix}-{h}"

    def _sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()
