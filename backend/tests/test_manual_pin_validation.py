"""Tests for manual locating pin backend validation."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import asyncio

from app.api.v1.jobs import regenerate
from app.models.job import Job
from app.models.schemas import RegenerateRequest, FixtureParameters


def _mock_job(candidates=None):
    job = MagicMock(spec=Job)
    job.id = "test-job-pin"
    job.status = "completed"
    job.name = "test.zip"
    job.file_path = "/tmp/test.zip"
    job.parameters = FixtureParameters().dict()
    job.result_data = {
        "locatingCandidates": candidates or [
            {"id": "pin-cand-d1", "drillId": "d1", "x": 5.0, "y": 5.0,
             "diameterMm": 3.0, "plated": False, "score": 8.0, "eligible": True,
             "selected": False, "pinDiameterMm": 2.9, "rejectionReasons": []},
            {"id": "pin-cand-d2", "drillId": "d2", "x": 95.0, "y": 75.0,
             "diameterMm": 1.5, "plated": True, "score": 1.0, "eligible": False,
             "selected": False, "pinDiameterMm": 1.4, "rejectionReasons": ["too small"]},
        ],
        "reviewItems": [],
        "manualLocatingPins": None,
        "geometrySha256": "sha_test",
    }
    job.created_at = MagicMock()
    job.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    job.logs = []
    job.current_step = ""
    return job


def _mock_db_with_job(job):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = job
    return db


class TestManualPinValidation:
    def test_rejects_nonexistent_drill(self):
        job = _mock_job()
        db = _mock_db_with_job(job)
        request = RegenerateRequest(manualLocatingPins=["nonexistent-drill"])

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                regenerate("test-job-pin", request, db)
            )
        assert exc_info.value.status_code == 422

    def test_rejects_small_hole(self):
        job = _mock_job()
        db = _mock_db_with_job(job)
        request = RegenerateRequest(manualLocatingPins=["d2"])

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                regenerate("test-job-pin", request, db)
            )
        assert exc_info.value.status_code == 422

    def test_accepts_valid_drill(self):
        job = _mock_job()
        db = _mock_db_with_job(job)
        request = RegenerateRequest(manualLocatingPins=["d1"])

        with patch("app.api.v1.jobs.process_gerber_job"), \
             patch("app.api.v1.jobs.add_log"):
            result = asyncio.get_event_loop().run_until_complete(
                regenerate("test-job-pin", request, db)
            )
            assert result is not None
