"""
任务处理器 - 整合 Gerber 解析、治具生成、DRC 及 DXF/SVG 导出
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from typing import Any
from app.core.database import SessionLocal
from app.models.job import Job
from app.models.schemas import ErrorCode
from app.services.exporters.dxf_exporter import export_fixture_dxf, export_fixture_svg
from app.services.fixture.generator import FixtureGenerator, FixtureGenerationError
from app.core.config import SOFTWARE_VERSION, ALGORITHM_VERSION, RULE_PROFILE_VERSION
from app.services.gerber.parser import GerberParser, GerberParseError
from app.services.gerber.component_detector import detect_bot_components, detect_through_hole_clusters
from app.core.config import ENABLE_OCR


def add_log(job: Job, level: str, message: str):
    """添加可持久化的任务日志。"""
    job.logs = [*(job.logs or []), {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
    }]


def process_job_background(job_id: str):
    """FastAPI BackgroundTasks entry point with its own DB session."""
    db = SessionLocal()
    try:
        process_gerber_job(job_id, db)
    finally:
        db.close()


def process_gerber_job(
    job_id: str,
    db: Session,
    manual_pins: list[str] | None = None,
    review_actions: dict[str, str] | None = None,
    custom_regions: list[dict[str, Any]] | None = None,
):
    """
    处理 Gerber 任务的主流水线
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return

    try:
        # Step 1: 解析 Gerber
        job.status = "parsing"
        job.progress = 15
        job.current_step = "正在扫描并验证 Gerber/Excellon 制造文件"
        add_log(job, "info", f"开始解析任务 ZIP: {Path(job.file_path).name}")
        db.commit()

        parser = GerberParser()
        analysis_result = parser.parse_zip(job.file_path, confirmed_layers=job.confirmed_layers)

        # 检查是否需要图层确认 (Confidence < 0.8 或缺少关键外形/钻孔)
        if analysis_result.get("requires_layer_confirmation"):
            job.status = "layer_confirmation"
            job.progress = 20
            job.current_step = analysis_result.get("message", "检测到无法可靠识别的关键图层，请人工确认")
            job.analysis_data = {
                "width": 0.0,
                "height": 0.0,
                "fileCount": len(analysis_result.get("layers", [])),
                "holeCount": 0,
                "outlineClosed": False,
                "outlineAreaMm2": 0.0,
                "layers": analysis_result.get("layers", []),
                "diagnostics": analysis_result.get("diagnostics", []),
            }
            job.error_data = {
                "code": analysis_result.get("error_code", ErrorCode.UNKNOWN_CRITICAL_LAYER),
                "title": "需要确认 Gerber 图层",
                "message": analysis_result.get("message", "请在图层弹窗中指定正确的 PCB 外形层或钻孔层。"),
                "recoverable": True,
            }
            add_log(job, "warning", "置信度不足或关键图层不明确，挂起等待用户确认图层映射")
            db.commit()
            return

        pcb_geom = analysis_result.pop("pcb_geometry")
        job.analysis_data = analysis_result
        job.progress = 40
        job.current_step = f"PCB 外形闭合成功 ({pcb_geom.width:.1f}×{pcb_geom.height:.1f}mm), 提取真实钻孔 {len(pcb_geom.holes)} 个"
        add_log(job, "info", f"PCB 外形尺寸: {pcb_geom.width:.2f} × {pcb_geom.height:.2f} mm, 钻孔数: {len(pcb_geom.holes)}")
        db.commit()

        # Step 2: 治具几何生成
        job.status = "generating"
        job.progress = 60
        job.current_step = "正在计算沉板区、R1.85清角、BOT避位、TOP上锡与治具外框"
        db.commit()

        # 继承此前的人工选孔和审核决策（如果本次未显式覆盖）
        if manual_pins is None and job.result_data:
            manual_pins = job.result_data.get("manualLocatingPins")
        if review_actions is None and job.result_data:
            existing_items = job.result_data.get("reviewItems", [])
            review_actions = {r["id"]: r["status"] for r in existing_items if r.get("status") in {"accepted", "rejected", "modified"}}
        if custom_regions is None and job.result_data:
            custom_regions = job.result_data.get("customRegions", [])

        generator = FixtureGenerator({"pcb_geometry": pcb_geom})
        fixture_data = generator.generate(
            job.parameters or {},
            review_actions=review_actions,
            manual_pins=manual_pins,
            custom_regions=custom_regions,
        )

        job.progress = 80
        job.current_step = "正在生成分层 SVG 预览与 AutoCAD R2018 DXF 图纸"
        db.commit()

        # Step 3: 导出 DXF 与 SVG
        output_dir = Path(job.file_path).parent
        dxf_filename = f"{job.id}_fixture.dxf"
        svg_filename = f"{job.id}_preview.svg"
        dxf_path = str(output_dir / dxf_filename)
        svg_path = str(output_dir / svg_filename)

        export_fixture_dxf(fixture_data, dxf_path)
        export_fixture_svg(fixture_data, svg_path)

        job.dxf_path = dxf_path
        job.svg_path = svg_path

        # Step 4: 整合结果与状态流转
        fixture_status = fixture_data.get("status", "completed")
        review_items = fixture_data.get("reviewItems", [])
        pending_reviews = [r for r in review_items if r.get("status") == "pending" and r.get("mandatory", True)]

        job.status = "review_required" if len(pending_reviews) > 0 else "completed"
        job.progress = 100
        job.current_step = f"治具出图完成 ({job.status}) - DRC 问题: {len(fixture_data.get('issues', []))}, 待审核项: {len(pending_reviews)}"
        
        existing_overrides = (job.result_data or {}).get("drcOverrides", [])
        job.result_data = {
            "fixtureWidth": fixture_data["fixtureWidth"],
            "fixtureHeight": fixture_data["fixtureHeight"],
            "featureSummary": fixture_data["featureSummary"],
            "issues": fixture_data["issues"],
            "reviewItems": fixture_data.get("reviewItems", []),
            "locatingCandidates": fixture_data.get("locating_candidates", []),
            "manualLocatingPins": manual_pins,
            "customRegions": custom_regions or [],
            "status": job.status,
            "geometrySha256": fixture_data.get("geometrySha256"),
            "drcOverrides": existing_overrides,
            "algorithmVersion": ALGORITHM_VERSION,
            "softwareVersion": SOFTWARE_VERSION,
            "ruleProfileVersion": RULE_PROFILE_VERSION,
            "generatedAt": datetime.now().isoformat(),
        }
        
        add_log(job, "info", f"治具工程出图完成，最终状态: {job.status}")
        db.commit()

    except GerberParseError as e:
        job.status = "failed"
        job.progress = 100
        job.current_step = f"Gerber 解析失败: {e.message}"
        job.error_data = {
            "code": e.code,
            "title": "Gerber 解析失败",
            "message": e.message,
            "details": e.details,
            "recoverable": True,
        }
        add_log(job, "error", f"GerberParseError [{e.code}]: {e.message}")
        db.commit()

    except FixtureGenerationError as e:
        job.status = "failed"
        job.progress = 100
        job.current_step = f"治具几何生成失败: {str(e)}"
        job.error_data = {
            "code": ErrorCode.GEOMETRY_ERROR,
            "title": "治具生成失败",
            "message": str(e),
            "recoverable": True,
        }
        add_log(job, "error", f"FixtureGenerationError: {str(e)}")
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.progress = 100
        job.current_step = f"处理异常: {str(e)}"
        job.error_data = {
            "code": ErrorCode.GEOMETRY_ERROR,
            "title": "系统内部错误",
            "message": str(e),
            "details": [traceback.format_exc()],
            "recoverable": False,
        }
        add_log(job, "error", f"Unhandled Exception: {traceback.format_exc()}")
        db.commit()

