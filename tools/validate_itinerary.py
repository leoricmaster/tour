#!/usr/bin/env python3
"""Validate a tour itinerary HTML and its image assets.

Usage:
  python3 tools/validate_itinerary.py <scheme_dir> --html <file.html>
  python3 tools/validate_itinerary.py <scheme_dir> --html <share.html> --share

The default mode validates a maintainable source HTML and rejects embedded
Base64 images. --share requires every referenced image to be embedded and to
match its physical source file.
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

CITY_PREFIX = {
    "hk": "hk",
    "phuquoc": "pq",
    "phuket": "ph",
    "chiangmai": "cm",
}
IMAGE_FIELDS = (
    ("main", "imagePath", "imageData", "imageCredit"),
    ("extra", "extraImagePath", "extraImageData", "extraImageCredit"),
)
DATA_RE = re.compile(
    r'<script\b(?=[^>]*\bid=["\']data["\'])(?=[^>]*\btype=["\']application/json["\'])[^>]*>(.*?)</script>',
    re.S | re.I,
)
HASHED_IMAGE_RE = re.compile(r"^(?P<prefix>[a-z]+)_.+_(?P<hash>[0-9a-f]{8})\.(?:jpg|jpeg|png)$", re.I)
DATA_URI_RE = re.compile(r"^data:image/(?:jpeg|png);base64,(.+)$", re.S)


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def inside(base: pathlib.Path, path: pathlib.Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def load_document(html_path: pathlib.Path, report: Report) -> tuple[str, dict[str, Any]]:
    try:
        html = html_path.read_text(encoding="utf-8")
    except OSError as exc:
        report.error(f"cannot read HTML: {exc}")
        return "", {}

    match = DATA_RE.search(html)
    if not match:
        report.error("cannot find <script type=\"application/json\" id=\"data\">")
        return html, {}
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        report.error(f"invalid #data JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return html, {}
    if not isinstance(data, dict):
        report.error("#data must be a JSON object")
        return html, {}
    return html, data


def check_table(rows: Any, label: str, report: Report) -> None:
    if not isinstance(rows, list) or not rows:
        report.error(f"{label} must be a non-empty array")
        return
    if not all(isinstance(row, list) for row in rows):
        report.error(f"{label} must contain only row arrays")
        return
    widths = {len(row) for row in rows}
    if len(widths) != 1:
        report.error(f"{label} has inconsistent row widths: {sorted(widths)}")
    elif 0 in widths:
        report.error(f"{label} rows must not be empty")


def check_tables(data: dict[str, Any], report: Report) -> None:
    check_table(data.get("schedule"), "schedule", report)
    check_table(data.get("flights"), "flights", report)

    hotels = data.get("hotels")
    if not isinstance(hotels, dict) or not hotels:
        report.error("hotels must be a non-empty object")
    else:
        for city, rows in hotels.items():
            check_table(rows, f"hotels.{city}", report)

    budget = data.get("budget")
    if budget is not None:
        if not isinstance(budget, dict):
            report.error("budget must be an object")
        else:
            check_table(budget.get("rows"), "budget.rows", report)

    day_plan = data.get("dayPlan")
    if not isinstance(day_plan, dict) or not day_plan:
        report.error("dayPlan must be a non-empty object")
    else:
        for city, plan in day_plan.items():
            if not isinstance(plan, dict):
                report.error(f"dayPlan.{city} must be an object")
                continue
            check_table(plan.get("rows"), f"dayPlan.{city}.rows", report)


def check_relations(data: dict[str, Any], report: Report) -> dict[str, dict[str, Any]]:
    sights = data.get("sights")
    if not isinstance(sights, list) or not sights:
        report.error("sights must be a non-empty array")
        return {}

    by_id: dict[str, dict[str, Any]] = {}
    required = ("id", "name", "city", "lat", "lng", "imagePath", "imageCredit")
    for index, sight in enumerate(sights):
        label = f"sights[{index}]"
        if not isinstance(sight, dict):
            report.error(f"{label} must be an object")
            continue
        missing = [key for key in required if key not in sight]
        if missing:
            report.error(f"{label} missing fields: {', '.join(missing)}")
        sid = sight.get("id")
        if not isinstance(sid, str) or not sid.strip():
            report.error(f"{label}.id must be a non-empty string")
        elif sid in by_id:
            report.error(f"duplicate sight id: {sid}")
        else:
            by_id[sid] = sight

        lat, lng = sight.get("lat"), sight.get("lng")
        if not isinstance(lat, (int, float)) or isinstance(lat, bool) or not -90 <= lat <= 90:
            report.error(f"{label}.lat is outside [-90, 90]")
        if not isinstance(lng, (int, float)) or isinstance(lng, bool) or not -180 <= lng <= 180:
            report.error(f"{label}.lng is outside [-180, 180]")

    colors = data.get("dayColors")
    color_ids: set[Any] = set()
    if not isinstance(colors, list):
        report.error("dayColors must be an array")
    else:
        for index, color in enumerate(colors):
            if not isinstance(color, dict) or "id" not in color:
                report.error(f"dayColors[{index}] must contain id")
                continue
            if color["id"] in color_ids:
                report.error(f"duplicate dayColors id: {color['id']}")
            color_ids.add(color["id"])
    for sid, sight in by_id.items():
        day = sight.get("day")
        if day is not None and day not in color_ids:
            report.error(f"sight {sid} references unknown day: {day}")

    routes = data.get("dayRoutes")
    if not isinstance(routes, dict):
        report.error("dayRoutes must be an object")
        return by_id
    for city, city_routes in routes.items():
        if not isinstance(city_routes, list):
            report.error(f"dayRoutes.{city} must be an array")
            continue
        for index, route in enumerate(city_routes):
            label = f"dayRoutes.{city}[{index}]"
            if not isinstance(route, dict) or not isinstance(route.get("sights"), list):
                report.error(f"{label} must contain a sights array")
                continue
            day = route.get("day")
            if day not in color_ids:
                report.error(f"{label} references unknown day: {day}")
            for sid in route["sights"]:
                sight = by_id.get(sid)
                if sight is None:
                    report.error(f"{label} references unknown sight: {sid}")
                elif sight.get("city") != city:
                    report.error(f"{label} references sight {sid} from city {sight.get('city')}")
                elif sight.get("day") != day:
                    report.warn(
                        f"{label} uses sight {sid} (primary day {sight.get('day')}); "
                        f"recurring sights (e.g. night markets) may appear on multiple days"
                    )
    return by_id


def decode_image_data(value: Any, label: str, report: Report) -> bytes | None:
    if not isinstance(value, str):
        report.error(f"{label} must be a Base64 image data URI")
        return None
    match = DATA_URI_RE.match(value)
    if not match:
        report.error(f"{label} must be a JPEG/PNG Base64 data URI")
        return None
    try:
        return base64.b64decode(match.group(1), validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        report.error(f"{label} contains invalid Base64: {exc}")
        return None


def check_images(
    base: pathlib.Path,
    data: dict[str, Any],
    manifest: dict[str, Any],
    mode: str,
    report: Report,
) -> None:
    references: dict[str, tuple[dict[str, Any], str, str, str]] = {}
    sights = data.get("sights")
    if not isinstance(sights, list):
        return

    for sight in sights:
        if not isinstance(sight, dict):
            continue
        sid, city = sight.get("id", "?"), sight.get("city")
        expected_prefix = CITY_PREFIX.get(city)
        if expected_prefix is None:
            report.error(f"sight {sid} uses unsupported city prefix: {city}")
        for role, path_key, data_key, credit_key in IMAGE_FIELDS:
            rel = sight.get(path_key)
            embedded_present = data_key in sight
            if not rel:
                if embedded_present:
                    report.error(f"sight {sid}.{data_key} is orphaned because {path_key} is empty")
                continue
            if not isinstance(rel, str):
                report.error(f"sight {sid}.{path_key} must be a string")
                continue
            if rel in references:
                other = references[rel][0].get("id", "?")
                report.error(f"image {rel} is referenced by both {other} and {sid}")
            references[rel] = (sight, role, data_key, credit_key)

            path = (base / rel).resolve()
            if not inside(base, path):
                report.error(f"sight {sid}.{path_key} escapes the scheme directory: {rel}")
                continue
            if not path.is_file():
                report.error(f"sight {sid}.{path_key} does not exist: {rel}")
                continue

            match = HASHED_IMAGE_RE.match(path.name)
            if not match:
                report.error(f"sight {sid} image has invalid hashed filename: {path.name}")
                continue
            if expected_prefix is not None and match.group("prefix").lower() != expected_prefix:
                report.error(
                    f"sight {sid} city {city} requires prefix {expected_prefix}_, got {path.name}"
                )
            raw = path.read_bytes()
            actual_hash = hashlib.sha1(raw).hexdigest()[:8]
            if match.group("hash").lower() != actual_hash:
                report.error(
                    f"sight {sid} image hash mismatch: filename={match.group('hash')}, actual={actual_hash}"
                )

            if mode == "source" and embedded_present:
                report.error(f"source HTML must not contain sight {sid}.{data_key}")
            elif mode == "share":
                if not embedded_present:
                    report.error(f"share HTML is missing sight {sid}.{data_key}")
                else:
                    embedded = decode_image_data(sight.get(data_key), f"sight {sid}.{data_key}", report)
                    if embedded is not None and hashlib.sha1(embedded).digest() != hashlib.sha1(raw).digest():
                        report.error(f"sight {sid}.{data_key} does not match {rel}")

    manifest_keys = {k: v for k, v in manifest.items() if not (isinstance(k, str) and k.startswith("_"))}
    reference_keys = set(references)
    for rel in sorted(reference_keys - set(manifest_keys)):
        report.error(f"image credit missing from image_credits.json: {rel}")
    for rel in sorted(set(manifest_keys) - reference_keys):
        report.error(f"stale image credit not referenced by HTML: {rel}")

    required_credit_fields = ("title", "author", "license", "url", "sha1_8", "sight_id", "city", "role")
    for rel in sorted(reference_keys & set(manifest_keys)):
        sight, role, _, credit_key = references[rel]
        entry = manifest_keys[rel]
        if not isinstance(entry, dict):
            report.error(f"image credit {rel} must be an object")
            continue
        missing = [key for key in required_credit_fields if key != "author" and not entry.get(key)]
        if missing:
            report.error(f"image credit {rel} missing fields: {', '.join(missing)}")
        if "author" in entry and not entry["author"]:
            report.warn(f"image credit {rel}.author is empty (Wikimedia image with no machine-readable author)")
        expected = {
            "sha1_8": hashlib.sha1((base / rel).read_bytes()).hexdigest()[:8],
            "sight_id": sight.get("id"),
            "city": sight.get("city"),
            "role": role,
        }
        for key, value in expected.items():
            if entry.get(key) != value:
                report.error(f"image credit {rel}.{key}={entry.get(key)!r}, expected {value!r}")
        if not str(entry.get("url", "")).startswith("https://commons.wikimedia.org/"):
            report.error(f"image credit {rel}.url is not a Wikimedia Commons HTTPS URL")

        inline = sight.get(credit_key)
        if not isinstance(inline, dict):
            report.error(f"sight {sight.get('id')}.{credit_key} must be an object")
        else:
            for key in ("author", "license", "url"):
                if inline.get(key) != entry.get(key):
                    report.error(
                        f"sight {sight.get('id')}.{credit_key}.{key} disagrees with image_credits.json"
                    )

    image_dir = base / "images"
    if image_dir.is_dir():
        physical = {
            path.relative_to(base).as_posix()
            for path in image_dir.iterdir()
            if path.is_file()
        }
        for rel in sorted(physical - reference_keys):
            report.warn(f"unreferenced physical image retained: {rel}")


def validate(base: pathlib.Path, html_path: pathlib.Path, mode: str) -> Report:
    report = Report()
    if not base.is_dir():
        report.error(f"scheme directory does not exist: {base}")
        return report
    if not inside(base, html_path):
        report.error(f"HTML must be inside scheme directory: {html_path}")
        return report

    _, data = load_document(html_path, report)
    if not data:
        return report

    required_top_level = (
        "schedule", "flights", "hotels", "sights", "dayPlan", "dayRoutes",
        "dayColors", "cities",
    )
    optional_budget = {"budget", "plans", "notes", "nextSteps", "questions", "overview", "flightNote", "hotelNote", "plansNote", "flightStatus", "hotelStatus", "meta", "mapHK", "mapPhuQuoc", "sightsExcludes", "title"}
    missing = [key for key in required_top_level if key not in data]
    if missing:
        report.error(f"#data missing top-level fields: {', '.join(missing)}")
    if "budget" not in data and "plans" not in data:
        report.error("either data.budget or data.plans is required")
    unknown_top = sorted(set(data) - set(required_top_level) - optional_budget)
    if unknown_top:
        report.warn(f"#data has unknown top-level fields: {', '.join(unknown_top)}")

    meta = data.get("meta")
    updated_at = meta.get("updatedAt") if isinstance(meta, dict) else None
    if not isinstance(updated_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated_at):
        report.error("meta.updatedAt must use YYYY-MM-DD format")

    check_tables(data, report)
    cities = data.get("cities")
    if not isinstance(cities, list) or not cities:
        report.error("cities must be a non-empty array")
    else:
        city_ids = set()
        for index, city in enumerate(cities):
            label = f"cities[{index}]"
            if not isinstance(city, dict):
                report.error(f"{label} must be an object")
                continue
            cid = city.get("id")
            if not isinstance(cid, str) or not cid.strip():
                report.error(f"{label}.id must be a non-empty string")
            elif cid in city_ids:
                report.error(f"duplicate city id: {cid}")
            else:
                city_ids.add(cid)
            for key in ("label", "tabLabel", "hotelHeading", "map"):
                if not city.get(key):
                    report.error(f"{label}.{key} is required")
            cmap = city.get("map")
            if not isinstance(cmap, dict):
                report.error(f"{label}.map must be an object")
            else:
                for key in ("intro", "credit", "tile"):
                    if not cmap.get(key):
                        report.error(f"{label}.map.{key} is required")
                if cmap.get("tile") not in ("amap", "osm-de"):
                    report.error(f"{label}.map.tile must be 'amap' or 'osm-de'")
        for key in ("hotels", "dayPlan", "dayRoutes"):
            container = data.get(key)
            if isinstance(container, dict):
                unknown = sorted(set(container) - city_ids)
                if unknown:
                    report.error(f"{key} has keys not in cities: {', '.join(unknown)}")
        sight_cities = {s.get("city") for s in data["sights"] if isinstance(s, dict)}
        unknown_sight = sorted(sight_cities - city_ids - {None})
        if unknown_sight:
            report.error(f"sights reference unknown city ids: {', '.join(unknown_sight)}")
    check_relations(data, report)

    manifest_path = base / "image_credits.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            report.error("image_credits.json must contain an object")
            manifest = {}
    except FileNotFoundError:
        report.error("image_credits.json does not exist")
        manifest = {}
    except json.JSONDecodeError as exc:
        report.error(f"invalid image_credits.json: line {exc.lineno}: {exc.msg}")
        manifest = {}

    check_images(base, data, manifest, mode, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="校验行程 HTML、数据关系、图片和授权清单")
    parser.add_argument("scheme_dir", help="方案目录")
    parser.add_argument("--html", required=True, help="目录内的 HTML 文件名")
    parser.add_argument("--share", action="store_true", help="按 Base64 分享版规则校验")
    args = parser.parse_args()

    base = pathlib.Path(args.scheme_dir).resolve()
    html_path = (base / args.html).resolve()
    mode = "share" if args.share else "source"
    report = validate(base, html_path, mode)

    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    if report.errors:
        print(f"\nFAILED | {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        return 1
    print(f"\nOK | {html_path.name} | mode={mode} | {len(report.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
