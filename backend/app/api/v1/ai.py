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
    ExplainIssueCommand,
    LocateIssueCommand,
)
from app.models.job import Job
from app.models.schemas import FixtureParameters
from app.services.ai.openai_compatible import AIProviderError, parse_command

router = APIRouter()


def _job_context(job: Job) -> dict:
    return {
        "jobId": job.id,
        "status": job.status,
        "parameters": job.parameters or {},
        "analysis": job.analysis_data or {},
        "result": job.result_data or {},
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

    if isinstance(command, UpdateParametersCommand):
        current = job.parameters or FixtureParameters().model_dump()
        merged = {**current, **command.parameters.values()}
        validated = FixtureParameters.model_validate(merged)
        job.parameters = validated.model_dump()
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
    job.current_step = "AI 命令已批准，正在重新生成"
    job.logs = [*(job.logs or []), {"time": "AI", "level": "info", "message": "AI 命令已批准并提交确定性几何引擎"}]
    db.commit()

    from app.tasks.process_job import process_gerber_job
    process_gerber_job(job.id, db)
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
