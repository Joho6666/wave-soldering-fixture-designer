import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.v1.jobs import override_drc, revoke_drc_override
from app.models.job import Job
from app.models.schemas import DrcOverrideRequest


def _make_mock_db(job):
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value.first.return_value = job
    db.query.return_value = query
    return db


@pytest.mark.asyncio
async def test_override_drc_success():
    job = MagicMock(spec=Job)
    job.id = "job-1"
    job.logs = []
    job.result_data = {
        "geometrySha256": "sha_100",
        "issues": [{"id": "drc-issue-1", "severity": "error"}],
        "drcOverrides": [],
    }
    db = _make_mock_db(job)
    req = DrcOverrideRequest(operator="张工", reason="已复核无干涉")

    res = await override_drc("job-1", "drc-issue-1", req, db)
    assert res["status"] == "ok"
    assert res["override"]["issueId"] == "drc-issue-1"
    assert res["override"]["status"] == "active"
    assert res["override"]["geometrySha256"] == "sha_100"


@pytest.mark.asyncio
async def test_override_drc_duplicate_active_raises_409():
    job = MagicMock(spec=Job)
    job.id = "job-1"
    job.logs = []
    job.result_data = {
        "geometrySha256": "sha_100",
        "issues": [{"id": "drc-issue-1", "severity": "error"}],
        "drcOverrides": [
            {
                "issueId": "drc-issue-1",
                "operator": "张工",
                "reason": "已复核",
                "geometrySha256": "sha_100",
                "status": "active",
            }
        ],
    }
    db = _make_mock_db(job)
    req = DrcOverrideRequest(operator="李工", reason="重新放行")

    with pytest.raises(HTTPException) as exc_info:
        await override_drc("job-1", "drc-issue-1", req, db)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_override_drc_re_enables_expired_override():
    # 几何变更后 SHA 变成 sha_200，旧的 sha_100 记录已过期，重新放行应成功更新为 sha_200
    job = MagicMock(spec=Job)
    job.id = "job-1"
    job.logs = []
    job.result_data = {
        "geometrySha256": "sha_200",
        "issues": [{"id": "drc-issue-1", "severity": "error"}],
        "drcOverrides": [
            {
                "issueId": "drc-issue-1",
                "operator": "张工",
                "reason": "旧放行",
                "geometrySha256": "sha_100",
                "status": "active",
            }
        ],
    }
    db = _make_mock_db(job)
    req = DrcOverrideRequest(operator="王工", reason="在新几何下确认放行")

    res = await override_drc("job-1", "drc-issue-1", req, db)
    assert res["status"] == "ok"
    assert res["override"]["geometrySha256"] == "sha_200"
    assert res["override"]["operator"] == "王工"
    assert len(job.result_data["drcOverrides"]) == 1


@pytest.mark.asyncio
async def test_revoke_drc_override_success():
    job = MagicMock(spec=Job)
    job.id = "job-1"
    job.logs = []
    job.result_data = {
        "geometrySha256": "sha_100",
        "issues": [{"id": "drc-issue-1", "severity": "error"}],
        "drcOverrides": [
            {
                "issueId": "drc-issue-1",
                "operator": "张工",
                "reason": "已复核",
                "geometrySha256": "sha_100",
                "status": "active",
            }
        ],
    }
    db = _make_mock_db(job)

    res = await revoke_drc_override("job-1", "drc-issue-1", db)
    assert res["status"] == "ok"
    assert len(job.result_data["drcOverrides"]) == 0


@pytest.mark.asyncio
async def test_revoke_drc_override_nonexistent_raises_404():
    job = MagicMock(spec=Job)
    job.id = "job-1"
    job.logs = []
    job.result_data = {
        "geometrySha256": "sha_100",
        "issues": [{"id": "drc-issue-1", "severity": "error"}],
        "drcOverrides": [],
    }
    db = _make_mock_db(job)

    with pytest.raises(HTTPException) as exc_info:
        await revoke_drc_override("job-1", "drc-issue-1", db)
    assert exc_info.value.status_code == 404
