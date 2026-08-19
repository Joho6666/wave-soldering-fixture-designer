"""Tests for DRC Override geometry SHA expiry."""
import pytest
from unittest.mock import MagicMock, patch

from app.api.v1.jobs import _compute_production_gate
from app.models.job import Job


def _mock_job_with_overrides(current_sha, override_sha, issues=None):
    job = MagicMock(spec=Job)
    job.status = "completed"
    job.result_data = {
        "geometrySha256": current_sha,
        "drcOverrides": [
            {
                "issueId": "drc-test-issue",
                "operator": "engineer",
                "reason": "verified",
                "timestamp": "2026-01-01T00:00:00",
                "originalSeverity": "error",
                "geometrySha256": override_sha,
                "status": "active",
            }
        ],
        "issues": issues or [
            {
                "id": "drc-test-issue",
                "code": "BARRIER_HOLE_COLLISION",
                "title": "Test",
                "description": "Test issue",
                "severity": "error",
                "confirmed": False,
            }
        ],
        "reviewItems": [],
    }
    return job


class TestDrcOverrideShaExpiry:
    def test_active_override_when_sha_matches(self):
        job = _mock_job_with_overrides("sha_v1", "sha_v1")
        gate = _compute_production_gate(job)
        assert gate.blocking_drc_errors == 0
        assert gate.production_ready is True

    def test_expired_override_when_sha_differs(self):
        job = _mock_job_with_overrides("sha_v2", "sha_v1")
        gate = _compute_production_gate(job)
        assert gate.blocking_drc_errors == 1
        assert gate.production_ready is False
        assert any("过期" in r for r in gate.blocking_reasons)

    def test_expired_override_when_current_sha_none(self):
        job = _mock_job_with_overrides(None, "sha_v1")
        gate = _compute_production_gate(job)
        assert gate.blocking_drc_errors == 1
        assert gate.production_ready is False
