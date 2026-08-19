"""Tests for OCR RefDes engine (graceful degradation when tesseract not installed)."""
import pytest
import re

from app.services.ocr.refdes_ocr import (
    is_ocr_available,
    extract_refdes,
    OcrRefDesResult,
    REFDES_PATTERN,
)


class TestOcrRefDesPattern:
    def test_matches_standard_refdes(self):
        assert REFDES_PATTERN.match("R1")
        assert REFDES_PATTERN.match("C23")
        assert REFDES_PATTERN.match("U4")
        assert REFDES_PATTERN.match("J12")
        assert REFDES_PATTERN.match("D100")
        assert REFDES_PATTERN.match("Q5")
        assert REFDES_PATTERN.match("L1")

    def test_rejects_non_refdes(self):
        assert not REFDES_PATTERN.match("ABC")
        assert not REFDES_PATTERN.match("12345")
        assert not REFDES_PATTERN.match("")
        assert not REFDES_PATTERN.match("X99")

    def test_case_insensitive(self):
        assert REFDES_PATTERN.match("r1")
        assert REFDES_PATTERN.match("c23")


class TestOcrAvailability:
    def test_reports_availability(self):
        result = is_ocr_available()
        assert isinstance(result, bool)


class TestOcrExtractRefdes:
    def test_returns_empty_when_no_tesseract(self):
        if is_ocr_available():
            pytest.skip("Tesseract IS available, cannot test graceful skip")
        from shapely.geometry import Polygon
        silk = Polygon([(0, 0), (10, 0), (10, 5), (0, 5)])
        results = extract_refdes(silk, (0, 0, 100, 80))
        assert results == []

    def test_returns_empty_when_no_silkscreen(self):
        results = extract_refdes(None, (0, 0, 100, 80))
        assert results == []


class TestOcrRefDesResult:
    def test_to_dict(self):
        r = OcrRefDesResult(
            refdes="R1",
            x=10.123,
            y=20.456,
            confidence=0.85,
            bbox=(9.0, 19.0, 11.0, 21.0),
        )
        d = r.to_dict()
        assert d["refdes"] == "R1"
        assert d["x"] == 10.123
        assert d["confidence"] == 0.85
        assert len(d["bbox"]) == 4
