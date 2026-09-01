#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validation.case_catalog import list_cases
from validation.metrics_aggregate import aggregate, render_markdown


def main() -> None:
    stats = aggregate(list_cases())
    text = render_markdown(stats)
    out = ROOT / "VALIDATION_METRICS.md"
    out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
