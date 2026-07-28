#!/usr/bin/env python3
"""Regression check for itinerary HTML renderer structure.

This is a static structural check; it does not run JavaScript. It compares
the data block and the HTML source against a baseline of renderer invariants.
For a behavioural check (pixel / DOM) use a real browser in a separate script.

Usage:
  python3 tools/regress_itinerary.py <scheme_dir> --html <file.html>
  python3 tools/regress_itinerary.py <scheme_dir> --html <share.html> --share
  python3 tools/regress_itinerary.py <scheme_dir> --html <file.html> --baseline <other.json>

The baseline is resolved in this order:
  1. --baseline CLI flag
  2. tools/baseline_<scheme_dir_basename>.json (per-scheme)
  3. tools/baseline.json (default)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

DATA_RE = re.compile(
    r'<script\b(?=[^>]*\bid=["\']data["\'])(?=[^>]*\btype=["\']application/json["\'])[^>]*>(.*?)</script>',
    re.S | re.I,
)


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def expect(report: Report, label: str, expected: Any, actual: Any) -> None:
    if expected == actual:
        return
    report.error(f"{label}: expected {expected!r}, got {actual!r}")


def load_data(html_path: pathlib.Path, report: Report) -> tuple[dict[str, Any], str] | None:
    html = html_path.read_text(encoding="utf-8")
    match = DATA_RE.search(html)
    if not match:
        report.error("cannot find <script type=\"application/json\" id=\"data\">")
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        report.error(f"invalid #data JSON: {exc.msg} (line {exc.lineno})")
        return None
    return data, html


def count_inline_styles(html: str) -> int:
    outside = re.sub(DATA_RE, "", html)
    return len(re.findall(r'\sstyle="', outside))


def check_data(report: Report, data: dict[str, Any], expected: dict[str, Any]) -> None:
    cities = data.get("cities") or []
    by_city = {c["id"]: c for c in cities if isinstance(c, dict) and c.get("id")}

    sights = data.get("sights") or []
    expect(report, "sights_total", expected["sights_total"], len(sights))
    for cid, expected_count in expected.get("sights_by_city", {}).items():
        actual = sum(1 for s in sights if isinstance(s, dict) and s.get("city") == cid)
        expect(report, f"sights_by_city[{cid}]", expected_count, actual)
    expect(report, "cities", expected["cities"], len(cities))
    expect(report, "day_colors", expected["day_colors"], len(data.get("dayColors") or []))
    routes = data.get("dayRoutes") or {}
    for cid, expected_count in expected.get("day_routes_by_city", {}).items():
        expect(report, f"day_routes_by_city[{cid}]", expected_count, len(routes.get(cid) or []))

    expect(report, "schedule_rows", expected["schedule_rows"], len(data.get("schedule") or []))
    expect(report, "flights_rows", expected["flights_rows"], len(data.get("flights") or []))
    hotels = data.get("hotels") or {}
    for cid, expected_count in expected.get("hotels_by_city_rows", {}).items():
        expect(report, f"hotels_by_city_rows[{cid}]", expected_count, len(hotels.get(cid) or []))
    day_plan = data.get("dayPlan") or {}
    for cid, expected_count in expected.get("day_plan_by_city_rows", {}).items():
        plan = day_plan.get(cid) or {}
        expect(report, f"day_plan_by_city_rows[{cid}]", expected_count, len(plan.get("rows") or []))
    if "budget_rows" in expected:
        expect(report, "budget_rows", expected["budget_rows"], len((data.get("budget") or {}).get("rows") or []))
    if "notes_items" in expected:
        expect(report, "notes_items", expected["notes_items"], len(data.get("notes") or []))


def check_rendered(report: Report, data: dict[str, Any], expected: dict[str, Any]) -> None:
    cities = data.get("cities") or []
    expect(report, "tab_buttons", expected["tab_buttons"], 1 + len(cities))
    expect(report, "tab_panels", expected["tab_panels"], 1 + len(cities))
    expect(report, "map_divs", expected["map_divs"], len(cities))
    expect(report, "card_elements", expected["card_elements"], len(data.get("sights") or []))
    expected_wrappers = 3 + 2 * len(cities)
    if data.get("plans") and not data.get("budget"):
        expected_wrappers += len(data["plans"])
    expect(report, "table_scroll_wrappers", expected["table_scroll_wrappers"], expected_wrappers)
    h2_total = expected["h2_in_overview"] + expected["h2_per_city"] * len(cities)
    expect(report, "h2_total", expected["h2_total"], h2_total)
    expect(report, "h4_in_overview", expected["h4_in_overview"], len(cities))


def check_html_invariants(report: Report, html: str, expected: dict[str, Any], mode: str) -> None:
    inline = count_inline_styles(html)
    if inline > expected["inline_style_count_max"]:
        report.error(
            f"inline style count {inline} exceeds baseline max {expected['inline_style_count_max']}"
        )
    if mode == "source" and expected["image_data_present"]:
        report.error("source HTML must not contain imageData fields")


def check_share(report: Report, data: dict[str, Any], expected: dict[str, Any]) -> None:
    main = sum("imageData" in s for s in (data.get("sights") or []))
    extra = sum("extraImageData" in s for s in (data.get("sights") or []))
    expect(report, "share.main_embedded", expected["main_embedded"], main)
    expect(report, "share.extra_embedded", expected["extra_embedded"], extra)


def resolve_baseline(scheme_dir: pathlib.Path, override: str | None) -> pathlib.Path:
    tools_dir = pathlib.Path(__file__).parent
    if override:
        return pathlib.Path(override)
    per_scheme = tools_dir / f"baseline_{scheme_dir.name}.json"
    if per_scheme.is_file():
        return per_scheme
    return tools_dir / "baseline.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="校验行程 HTML 的渲染器回归基线")
    parser.add_argument("scheme_dir", help="方案目录")
    parser.add_argument("--html", required=True, help="目录内的 HTML 文件名")
    parser.add_argument("--baseline", default=None, help="基线 JSON 路径")
    parser.add_argument("--share", action="store_true", help="按 Base64 分享版规则校验")
    args = parser.parse_args()

    base = pathlib.Path(args.scheme_dir).resolve()
    html_path = (base / args.html).resolve()
    if not html_path.is_file():
        print(f"ERROR: HTML 不存在：{html_path}")
        return 1

    baseline_path = resolve_baseline(base, args.baseline)
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: 无法读取基线 {baseline_path}: {exc}")
        return 1

    report = Report()
    loaded = load_data(html_path, report)
    if loaded is None:
        for error in report.errors:
            print(f"ERROR: {error}")
        return 1
    data, html = loaded

    check_data(report, data, baseline["data"])
    check_rendered(report, data, baseline["rendered"])
    check_html_invariants(report, html, baseline["html_source_invariants"], "share" if args.share else "source")
    if args.share:
        check_share(report, data, baseline["share"])

    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    if report.errors:
        print(f"\nFAILED | {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        return 1
    print(f"\nOK | {html_path.name} | {len(report.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
