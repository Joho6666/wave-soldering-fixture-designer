import pytest
from fastapi import HTTPException

from app.api.v1.jobs import _safe_upload_name


def test_safe_upload_name_accepts_zip():
    assert _safe_upload_name("board.zip") == "board.zip"
    assert _safe_upload_name("C:/tmp/panel.ZIP") == "panel.ZIP"


def test_safe_upload_name_rejects_path_escape():
    with pytest.raises(HTTPException) as exc:
        _safe_upload_name("../secret.zip")
    assert exc.value.status_code == 400


def test_safe_upload_name_rejects_non_zip():
    with pytest.raises(HTTPException) as exc:
        _safe_upload_name("board.gbr")
    assert exc.value.status_code == 400


def test_safe_upload_name_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        _safe_upload_name(None)
    assert exc.value.status_code == 400
