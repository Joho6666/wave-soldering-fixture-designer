"""Tests for complete_all_reviews rejecting pending mandatory reviews."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import asyncio

from app.api.v1.jobs import complete_all_reviews
from app.models.job import Job


def _mock_job(reviews, job_id="test-job-001"):
    job = MagicMock(spec=Job)
    job.id = job_id
    job.status = "review_required"
    job.result_data = {
        "reviewItems": reviews,
        "manualLocatingPins": None,
        "geometrySha256": "abc123",
    }
    job.logs = []
    return job


def _mock_db_with_job(job):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = job
    return db


class TestCompleteReviewsRejectsPending:
    def test_rejects_when_mandatory_pending(self):
        reviews = [
            {"id": "r1", "type": "CONFIRM_NO_BOTTOM_SMD", "status": "pending", "mandatory": True,
             "title": "test", "description": "test", "confidence": 0.5},
        ]
        job = _mock_job(reviews)
        db = _mock_db_with_job(job)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                complete_all_reviews("test-job-001", db)
            )
        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert detail["code"] == "PENDING_REVIEWS_EXIST"

    def test_allows_when_no_mandatory_pending(self):
        reviews = [
            {"id": "r1", "type": "CONFIRM_NO_BOTTOM_SMD", "status": "accepted", "mandatory": True,
             "title": "test", "description": "test", "confidence": 0.5},
            {"id": "r2", "type": "bot_keepout_region", "status": "pending", "mandatory": False,
             "title": "test", "description": "test", "confidence": 0.9},
        ]
        job = _mock_job(reviews)
        db = _mock_db_with_job(job)

        with patch("app.api.v1.jobs.process_gerber_job"), \
             patch("app.api.v1.jobs.add_log"):
            result = asyncio.get_event_loop().run_until_complete(
                complete_all_reviews("test-job-001", db)
            )
            assert result["status"] == "ok"

    def test_nonmandatory_pending_not_blocking(self):
        reviews = [
            {"id": "r1", "type": "bot_keepout_region", "status": "pending", "mandatory": False,
             "title": "test", "description": "test", "confidence": 0.9},
        ]
        job = _mock_job(reviews)
        db = _mock_db_with_job(job)

        with patch("app.api.v1.jobs.process_gerber_job"), \
             patch("app.api.v1.jobs.add_log"):
            result = asyncio.get_event_loop().run_until_complete(
                complete_all_reviews("test-job-001", db)
            )
            assert result["status"] == "ok"
