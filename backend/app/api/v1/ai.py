"""AI command endpoint. The model proposes commands; deterministic backend applies them."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_schemas import (
    AICommandRequest,
    AICommandResponse,
    RegenerateCommand,
    UpdateParametersCommand,
    ApplyRecipePresetCommand,
    SetLocatingPinsCommand,
    AddCustomRegionCommand,
    AutoFixDrcCommand,
    ExplainIssueCommand,
    LocateIssueCommand,
)
from app.models.job import Job
from app.models.schemas import FixtureParameters
from app.services.ai.openai_compatible import AIProviderError, parse_command, RECIPE_PRESETS

router = APIRouter()


def _job_context(job: Job) -> dict:
    analysis = job.analysis_data or {}
    result = job.result_data or {}
    candidates = result.get("locatingCandidates", [])
    issues = result.get("issues", [])
    
    return {
        "jobId": job.id,
        "status": job.status,
        "pcb": {
            "width": analysis.get("width", 0.0),
            "height": analysis.get("height", 0.0),
            "holeCount": analysis.get("holeCount", 0),
            "outlineClosed": analysis.get("outlineClosed", False),
        },
        "parameters": job.parameters or {},
        "selectedLocatingPins": (job.result_data or {}).get("manualLocatingPins") or [p["id"] for p in result.get("pins", [])],
        "locatingCandidates": [
            {
                "id": c.get("id"),
                "drillId": c.get("drillId"),
                "x": round(c.get("x", 0), 2),
                "y": round(c.get("y", 0), 2),
                "diameterMm": c.get("diameterMm", 0),
                "plated": c.get("plated"),
                "score": c.get("score"),
                "eligible": c.get("eligible", True),
            }
            for c in candidates[:25]
        ],
        "issues": [
            {
                "id": i.get("id"),
                "code": i.get("code"),
                "title": i.get("title"),
                "severity": i.get("severity"),
                "currentValue": i.get("currentValue"),
                "requiredValue": i.get("requiredValue"),
                "unit": i.get("unit"),
            }
            for i in issues
        ],
        "featureSummary": result.get("featureSummary", {}),
        "availablePresets": list(RECIPE_PRESETS.keys()),
    }


def _job_response(job: Job) -> dict:
    return {
        "id": job.id,
        "name": job.name,
        "status": job.status,
        "progress": job.progress,
        "createdAt": job.created_at.isoformat(),
        "currentStepDescription": job.current_step,
        "error": job.error_data,
        "logs": job.logs or [],
    }


@router.post("/jobs/{job_id}/ai/command", response_model=AICommandResponse)
async def ai_command(job_id: str, request: AICommandRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status in {"parsing", "generating", "uploading"}:
        raise HTTPException(status_code=409, detail="任务正在处理中，请等待当前生成完成。")

    if request.apply and request.command is not None:
        command = request.command
        explanation = command.reason
    else:
        try:
            command, explanation = await parse_command(request.userMessage, _job_context(job))
        except AIProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    if isinstance(command, (ExplainIssueCommand, LocateIssueCommand)):
        issue_id = command.issueId
        issues = {issue.get("id"): issue for issue in (job.result_data or {}).get("issues", [])}
        if issue_id not in issues:
            raise HTTPException(status_code=422, detail="AI 引用的 DRC 问题不属于当前任务。")

    if not request.apply:
        return AICommandResponse(
            conversationId=request.conversationId,
            message=explanation,
            status="needs_confirmation" if command.requiresConfirmation else "complete",
            command=command,
            applied=False,
        )

    if not command.requiresConfirmation:
        return AICommandResponse(
            conversationId=request.conversationId,
            message=explanation,
            status="complete",
            command=command,
            applied=False,
            errors=["该命令为只读命令，不需要 apply。"],
        )

    manual_pins = (job.result_data or {}).get("manualLocatingPins")
    custom_regions = list((job.result_data or {}).get("customRegions", []))

    if isinstance(command, UpdateParametersCommand):
        current = job.parameters or FixtureParameters().model_dump()
        merged = {**current, **command.parameters.values()}
        job.parameters = FixtureParameters.model_validate(merged).model_dump()

    elif isinstance(command, ApplyRecipePresetCommand):
        preset_data = RECIPE_PRESETS.get(command.presetId, {})
        preset_params = {**preset_data.get("parameters", {}), **command.parameters.values()}
        current = job.parameters or FixtureParameters().model_dump()
        merged = {**current, **preset_params}
        job.parameters = FixtureParameters.model_validate(merged).model_dump()

    elif isinstance(command, AutoFixDrcCommand):
        suggested = command.suggestedParameters.values()
        current = job.parameters or FixtureParameters().model_dump()
        merged = {**current, **suggested}
        job.parameters = FixtureParameters.model_validate(merged).model_dump()

    elif isinstance(command, SetLocatingPinsCommand):
        manual_pins = command.pinDrillIds

    elif isinstance(command, AddCustomRegionCommand):
        custom_regions.append({
            "regionType": command.regionType,
            "x": command.x,
            "y": command.y,
            "width": command.width,
            "height": command.height,
            "label": command.label,
        })
        job.result_data = {**(job.result_data or {}), "customRegions": custom_regions}

    elif not isinstance(command, RegenerateCommand):
        return AICommandResponse(
            conversationId=request.conversationId,
            message=explanation,
            status="complete",
            command=command,
            applied=False,
            errors=["只读命令需要由前端引用当前结果执行，服务端未修改几何。"],
        )

    job.status = "parsing"
    job.progress = 10
    job.current_step = "AI 建设指令已批准，正在重新生成治具"
    job.logs = [*(job.logs or []), {"time": "AI", "level": "info", "message": f"AI [{command.kind}] 建设指令已提交确定性几何引擎"}]
    db.commit()

    from app.tasks.process_job import process_gerber_job
    process_gerber_job(job.id, db, manual_pins=manual_pins, custom_regions=custom_regions)
    db.refresh(job)

    return AICommandResponse(
        conversationId=request.conversationId,
        message=explanation,
        status="complete" if job.status == "completed" else "needs_confirmation" if job.status == "review_required" else "error",
        command=command,
        applied=True,
        job=_job_response(job),
        errors=[],
    )
