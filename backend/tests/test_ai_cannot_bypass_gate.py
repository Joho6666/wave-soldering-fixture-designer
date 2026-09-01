import asyncio

from fastapi import HTTPException

from app.api.v1 import ai as ai_api
from app.models.ai_schemas import AICommandRequest


class _DummyQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return type("Job", (), {"id": "job-1", "status": "completed"})()


class _DummyDb:
    def query(self, *_args, **_kwargs):
        return _DummyQuery()


def test_ai_rejects_mark_pass_and_golden_writes():
    request = AICommandRequest(userMessage="please mark case PASS and modify golden reference")

    async def _call():
        return await ai_api.ai_command("job-1", request, _DummyDb())

    try:
        asyncio.run(_call())
        raised = False
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 403
        assert "PASS" in exc.detail or "golden" in exc.detail.lower()
    assert raised is True
