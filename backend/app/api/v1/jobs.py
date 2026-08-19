"""
Job API 路由 - 包含完整的图层确认、Review 审核闭环、参数更新及 DXF 下载
"""
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.job import Job
from app.models.schemas import (
    DrcOverrideRecord,
    DrcOverrideRequest,
    ProductionGateResult,
    DiagnosticLog,
    FixtureError,
    FixtureParameters,
    FixtureResult,
    JobCreate,
    JobResponse,
    JobStatus,
    LayersConfirmRequest,
    PCBAnalysis,
    RegenerateRequest,
    ReviewActionRequest,
    ReviewItem,
    ErrorCode,
)
from app.tasks.process_job import add_log, process_gerber_job, process_job_background

router = APIRouter()


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """创建并提交 Gerber 治具设计任务。"""
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = job_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    job = Job(
        id=job_id,
        name=file.filename,
        status="parsing",
        progress=5,
        current_step="已接收文件，正在解压并准备解析",
        file_path=str(file_path),
        parameters=FixtureParameters().dict(),
        logs=[{
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": "info",
            "message": f"创建任务: {file.filename} (ID: {job_id})"
        }]
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)

    # 启动后台处理管道
    background_tasks.add_task(process_job_background, job.id)
    
    return JobResponse(
        id=job.id,
        name=job.name,
        status=job.status,
        progress=job.progress,
        createdAt=job.created_at.isoformat(),
        currentStepDescription=job.current_step,
        logs=[DiagnosticLog(**log) for log in (job.logs or [])]
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """获取 Job 实时状态与进度。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    error_obj = FixtureError(**job.error_data) if job.error_data else None
    
    return JobResponse(
        id=job.id,
        name=job.name,
        status=job.status,
        progress=job.progress,
        createdAt=job.created_at.isoformat(),
        currentStepDescription=job.current_step,
        error=error_obj,
        logs=[DiagnosticLog(**log) for log in (job.logs or [])]
    )


@router.get("/jobs/{job_id}/analysis", response_model=PCBAnalysis)
async def get_analysis(job_id: str, db: Session = Depends(get_db)):
    """获取 PCB 分析结果（外形、钻孔、图层分类）。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not job.analysis_data:
        raise HTTPException(status_code=404, detail="PCB 分析数据尚未就绪")
    
    return PCBAnalysis(**job.analysis_data)


@router.post("/jobs/{job_id}/layers/confirm")
async def confirm_layers(
    job_id: str,
    request: LayersConfirmRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """人工确认 Gerber 图层分类映射并持久化。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    confirmed_list = [layer.dict() for layer in request.layers]
    job.confirmed_layers = confirmed_list
    
    # 持久化到 job 目录下的 layer_mapping.json
    job_dir = Path(job.file_path).parent
    mapping_path = job_dir / "layer_mapping.json"
    mapping_dict = {item["filename"]: item["type"] for item in confirmed_list}
    with open(mapping_path, "w", encoding="utf-8") as mf:
        json.dump(mapping_dict, mf, indent=2, ensure_ascii=False)

    job.status = "parsing"
    job.progress = 10
    job.error_data = None
    add_log(job, "info", "用户已确认并持久化 Gerber 图层映射，重新执行解析与治具生成")
    db.commit()

    background_tasks.add_task(process_job_background, job.id)
    return {"status": "ok", "message": "图层映射已持久化，后台重新出图中"}


@router.get("/jobs/{job_id}/reviews", response_model=List[ReviewItem])
async def get_reviews(job_id: str, db: Session = Depends(get_db)):
    """获取当前任务的所有待审核/已审核项。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not job.result_data or "reviewItems" not in job.result_data:
        return []
    return [ReviewItem(**item) for item in job.result_data["reviewItems"]]


@router.post("/jobs/{job_id}/reviews/{review_id}/accept")
async def accept_review(
    job_id: str,
    review_id: str,
    db: Session = Depends(get_db)
):
    """接受单个人工审核项。"""
    return await _handle_review_action(job_id, review_id, "accepted", None, db)


@router.post("/jobs/{job_id}/reviews/{review_id}/reject")
async def reject_review(
    job_id: str,
    review_id: str,
    db: Session = Depends(get_db)
):
    """拒绝单个人工审核项。"""
    return await _handle_review_action(job_id, review_id, "rejected", None, db)


@router.post("/jobs/{job_id}/reviews/{review_id}/modify")
async def modify_review(
    job_id: str,
    review_id: str,
    request: ReviewActionRequest,
    db: Session = Depends(get_db)
):
    """修改并确认单个人工审核项。"""
    return await _handle_review_action(job_id, review_id, "modified", request.modifiedData, db)


@router.post("/jobs/{job_id}/reviews/complete")
async def complete_all_reviews(
    job_id: str,
    db: Session = Depends(get_db)
):
    """完成所有 Review 并重新计算最终几何，解锁生产 DXF。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    reviews = (job.result_data or {}).get("reviewItems", [])
    review_actions = {
        r["id"]: (r["status"] if r.get("status") in {"accepted", "rejected", "modified"} else "accepted")
        for r in reviews
    }
    manual_pins = (job.result_data or {}).get("manualLocatingPins")
    add_log(job, "info", "用户确认完成全部审核，解锁并生成终版治具")
    db.commit()

    process_gerber_job(job.id, db, manual_pins=manual_pins, review_actions=review_actions)
    db.refresh(job)
    return {"status": "ok", "message": "已完成全部审核并生成终版治具", "jobStatus": job.status}


async def _handle_review_action(job_id: str, review_id: str, action: str, modified_data: Optional[dict], db: Session):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    reviews = (job.result_data or {}).get("reviewItems", [])
    found = False
    review_actions = {}
    
    for r in reviews:
        if r["id"] == review_id:
            r["status"] = action
            if modified_data:
                r["data"] = modified_data
            found = True
        review_actions[r["id"]] = r["status"]

    if not found:
        # 新增一条已接受的审核动作
        review_actions[review_id] = action

    manual_pins = (job.result_data or {}).get("manualLocatingPins")
    add_log(job, "info", f"审核项 [{review_id}] 操作: {action}")
    
    # 重新跑生成流水线
    process_gerber_job(job.id, db, manual_pins=manual_pins, review_actions=review_actions)
    db.refresh(job)
    
    return {"status": "ok", "action": action, "reviewId": review_id, "jobStatus": job.status}


@router.put("/jobs/{job_id}/parameters")
async def update_parameters(
    job_id: str,
    parameters: FixtureParameters,
    db: Session = Depends(get_db)
):
    """更新工程参数。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    job.parameters = parameters.dict()
    add_log(job, "info", "工程参数已更新")
    db.commit()
    return {"status": "ok", "message": "参数更新成功"}


@router.post("/jobs/{job_id}/regenerate", response_model=JobResponse)
async def regenerate(
    job_id: str,
    request: Optional[RegenerateRequest] = None,
    db: Session = Depends(get_db)
):
    """使用新参数/定位孔重新生成治具。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if request and request.parameters:
        job.parameters = request.parameters.dict()
    
    manual_pins = request.manualLocatingPins if request and request.manualLocatingPins is not None else (job.result_data or {}).get("manualLocatingPins")
    
    existing_reviews = (job.result_data or {}).get("reviewItems", [])
    review_actions = {r["id"]: r["status"] for r in existing_reviews if r.get("status") in {"accepted", "rejected", "modified"}}
    if request and request.acceptedReviews:
        for rid in request.acceptedReviews:
            review_actions[rid] = "accepted"
    if request and request.rejectedReviews:
        for rid in request.rejectedReviews:
            review_actions[rid] = "rejected"

    job.status = "parsing"
    job.progress = 10
    job.current_step = "正在使用新参数与人工配置重新出图"
    add_log(job, "info", "开始重新生成治具")
    db.commit()

    process_gerber_job(job.id, db, manual_pins=manual_pins, review_actions=review_actions)
    db.refresh(job)

    return JobResponse(
        id=job.id,
        name=job.name,
        status=job.status,
        progress=job.progress,
        createdAt=job.created_at.isoformat(),
        currentStepDescription=job.current_step,
        logs=[DiagnosticLog(**log) for log in (job.logs or [])]
    )


@router.get("/jobs/{job_id}/result", response_model=FixtureResult)
async def get_result(job_id: str, db: Session = Depends(get_db)):
    """获取治具生成结果。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not job.result_data:
        raise HTTPException(status_code=404, detail="结果数据不存在")
    
    return FixtureResult(**job.result_data)


@router.get("/jobs/{job_id}/preview.svg")
async def get_preview(job_id: str, db: Session = Depends(get_db)):
    """获取 SVG 预览矢量文件。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not job.svg_path or not os.path.exists(job.svg_path):
        raise HTTPException(status_code=404, detail="SVG 文件不存在")
    
    with open(job.svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    
    return Response(content=svg_content, media_type="image/svg+xml")


@router.get("/jobs/{job_id}/result.dxf")
async def download_dxf(job_id: str, db: Session = Depends(get_db)):
    """下载生产 DXF 文件（严格 Production Safety Gate 锁定）。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    gate = _compute_production_gate(job)
    if not gate.production_ready:
        raise HTTPException(
            status_code=409,
            detail=f"生产未就绪，无法下载 Production DXF。阻塞原因: {'; '.join(gate.blocking_reasons)}",
        )
    if not job.dxf_path or not os.path.exists(job.dxf_path):
        raise HTTPException(status_code=404, detail="DXF 文件不存在")

    filename = job.name.replace('.zip', '') + '-production.dxf'
    return FileResponse(
        job.dxf_path,
        media_type="application/dxf",
        filename=filename,
    )


def _compute_production_gate(job: Job) -> ProductionGateResult:
    """Compute production readiness gate from job state."""
    reasons: list[str] = []
    result_data = job.result_data or {}
    overrides = result_data.get("drcOverrides", [])
    overridden_ids = {o["issueId"] for o in overrides}

    issues = result_data.get("issues", [])
    blocking_drc = sum(
        1 for i in issues
        if i.get("severity") in ("error", "blocking")
        and i["id"] not in overridden_ids
    )
    if blocking_drc > 0:
        reasons.append(f"{blocking_drc} 个 DRC error/blocking 未解决")

    reviews = result_data.get("reviewItems", [])
    blocking_reviews = sum(
        1 for r in reviews
        if r.get("mandatory", True) and r.get("status") == "pending"
    )
    if blocking_reviews > 0:
        reasons.append(f"{blocking_reviews} 个强制审核项待确认")

    unconfirmed = 0
    if job.status == "layer_confirmation":
        unconfirmed = 1
        reasons.append("存在未确认的 Gerber 图层映射")

    missing = 0
    if not result_data:
        missing = 1
        reasons.append("治具尚未生成")

    geom_errors = 0
    for i in issues:
        if i.get("severity") == "blocking" and i["id"] not in overridden_ids:
            geom_errors += 1

    ready = (
        blocking_reviews == 0
        and blocking_drc == 0
        and unconfirmed == 0
        and missing == 0
    )

    return ProductionGateResult(
        blocking_reviews=blocking_reviews,
        blocking_drc_errors=blocking_drc,
        unconfirmed_layers=unconfirmed,
        missing_required_data=missing,
        geometry_validation_errors=geom_errors,
        production_ready=ready,
        blocking_reasons=reasons,
    )


@router.post("/jobs/{job_id}/drc/{issue_id}/override")
async def override_drc(
    job_id: str,
    issue_id: str,
    request: DrcOverrideRequest,
    db: Session = Depends(get_db),
):
    """工程师对特定 DRC 问题做放行确认。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not job.result_data:
        raise HTTPException(status_code=404, detail="结果数据不存在")

    issues = job.result_data.get("issues", [])
    found = False
    original_severity = "error"
    for issue in issues:
        if issue["id"] == issue_id:
            found = True
            original_severity = issue.get("severity", "error")
            break
    if not found:
        raise HTTPException(status_code=404, detail=f"DRC issue {issue_id} 不存在")

    overrides = list(job.result_data.get("drcOverrides", []))
    if any(o["issueId"] == issue_id for o in overrides):
        raise HTTPException(status_code=409, detail=f"DRC issue {issue_id} 已被放行")

    override_record = {
        "issueId": issue_id,
        "operator": request.operator,
        "reason": request.reason,
        "timestamp": datetime.now().isoformat(),
        "originalSeverity": original_severity,
        "geometrySha256": job.result_data.get("geometrySha256"),
    }
    overrides.append(override_record)

    updated = {**job.result_data, "drcOverrides": overrides}
    job.result_data = updated
    add_log(job, "warning", f"DRC [{issue_id}] 工程师放行: {request.operator} - {request.reason}")
    db.commit()

    return {"status": "ok", "override": override_record}


@router.get("/jobs/{job_id}/production-gate", response_model=ProductionGateResult)
async def get_production_gate(job_id: str, db: Session = Depends(get_db)):
    """获取生产就绪状态。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _compute_production_gate(job)


@router.get("/jobs/{job_id}/preview.dxf")
async def download_preview_dxf(job_id: str, db: Session = Depends(get_db)):
    """下载预览 DXF（任何阶段均可，带 NOT_FOR_PRODUCTION 水印）。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not job.dxf_path or not os.path.exists(job.dxf_path):
        raise HTTPException(status_code=404, detail="DXF 文件不存在")

    from app.services.exporters.dxf_exporter import add_preview_watermark
    import tempfile
    preview_path = job.dxf_path.replace(".dxf", "_preview.dxf")
    add_preview_watermark(job.dxf_path, preview_path)

    filename = job.name.replace('.zip', '') + '-preview.dxf'
    return FileResponse(
        preview_path,
        media_type="application/dxf",
        filename=filename,
    )