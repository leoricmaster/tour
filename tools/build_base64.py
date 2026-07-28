#!/usr/bin/env python3
"""Build a self-contained Base64 sharing copy of an itinerary HTML.

Preferred usage:
  python3 tools/build_base64.py <scheme_dir> \
    --html source.html --output source_分享版.html

Backward-compatible in-place builds are allowed only when --html already names
an explicit sharing file (_分享版.html, _share.html, or _base64.html).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
from typing import Any

CITY_PREFIX = {
    "hk": "hk",
    "phuquoc": "pq",
    "phuket": "ph",
    "chiangmai": "cm",
}
DATA_RE = re.compile(
    r'(<script\b(?=[^>]*\bid=["\']data["\'])(?=[^>]*\btype=["\']application/json["\'])[^>]*>)(.*?)(</script>)',
    re.S | re.I,
)
HASHED_IMAGE_RE = re.compile(r"^(?P<prefix>[a-z]+)_.+_(?P<hash>[0-9a-f]{8})\.(?P<ext>jpg|jpeg|png)$", re.I)
SHARE_SUFFIXES = ("_分享版.html", "_share.html", "_base64.html")
IMAGE_FIELDS = (
    ("main", "imagePath", "imageData"),
    ("extra", "extraImagePath", "extraImageData"),
)


def is_share_name(name: str) -> bool:
    return name.lower().endswith(tuple(s.lower() for s in SHARE_SUFFIXES))


def resolve_inside(base: pathlib.Path, value: str, label: str) -> pathlib.Path:
    path = (base / value).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise ValueError(f"{label} 超出方案目录：{value}") from None
    return path


def choose_default_html(base: pathlib.Path) -> pathlib.Path:
    expected = base / f"{base.name}.html"
    if expected.is_file():
        return expected
    candidates = sorted(path for path in base.glob("*.html") if not is_share_name(path.name))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError("找不到原版 HTML，请用 --html 指定")
    raise ValueError("存在多个原版 HTML，请用 --html 指定")


def atomic_write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        handle.write(content)
        temporary = pathlib.Path(handle.name)
    try:
        temporary.chmod(output_mode)
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="生成图片完整内嵌的单文件分享版")
    parser.add_argument("scheme_dir", help="方案目录（包含 HTML、images/ 和 image_credits.json）")
    parser.add_argument("--html", help="输入 HTML 文件名；省略时自动选择唯一原版")
    parser.add_argument("--output", help="输出分享版文件名；省略时仅允许原地更新显式分享版")
    args = parser.parse_args()

    base = pathlib.Path(args.scheme_dir).resolve()
    if not base.is_dir():
        print(f"ERROR: 方案目录不存在：{base}")
        return 1

    try:
        input_path = resolve_inside(base, args.html, "输入 HTML") if args.html else choose_default_html(base)
        output_path = resolve_inside(base, args.output, "输出 HTML") if args.output else input_path
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    if not input_path.is_file():
        print(f"ERROR: 输入 HTML 不存在：{input_path}")
        return 1
    if not is_share_name(output_path.name):
        print(
            "ERROR: 为防止覆盖原版，输出文件名必须以 "
            "_分享版.html、_share.html 或 _base64.html 结尾"
        )
        print("提示：使用 --output <原名>_分享版.html")
        return 1

    html = input_path.read_text(encoding="utf-8")
    match = DATA_RE.search(html)
    if not match:
        print("ERROR: HTML 中找不到 #data JSON 块")
        return 1
    try:
        data: dict[str, Any] = json.loads(match.group(2))
    except json.JSONDecodeError as exc:
        print(f"ERROR: #data JSON 解析失败：第 {exc.lineno} 行：{exc.msg}")
        return 1
    sights = data.get("sights")
    if not isinstance(sights, list):
        print("ERROR: #data.sights 必须是数组")
        return 1

    # Always rebuild from clean data. This removes stale or orphaned Base64
    # fields and makes repeated builds deterministic.
    removed = 0
    for sight in sights:
        if not isinstance(sight, dict):
            continue
        for _, _, data_key in IMAGE_FIELDS:
            if data_key in sight:
                sight.pop(data_key)
                removed += 1

    errors: list[str] = []
    embedded = 0
    for index, sight in enumerate(sights):
        if not isinstance(sight, dict):
            errors.append(f"sights[{index}] 不是对象")
            continue
        sid = sight.get("id", "?")
        city = sight.get("city")
        expected_prefix = CITY_PREFIX.get(city)
        if expected_prefix is None:
            errors.append(f"{sid}: 不支持的 city={city!r}，请先在 CITY_PREFIX 中登记")
            continue

        for role, path_key, data_key in IMAGE_FIELDS:
            rel = sight.get(path_key)
            if not rel:
                continue
            if not isinstance(rel, str):
                errors.append(f"{sid}.{path_key}: 必须是字符串")
                continue
            try:
                path = resolve_inside(base, rel, f"{sid}.{path_key}")
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not path.is_file():
                errors.append(f"{sid}.{role}: 图片不存在：{rel}")
                continue

            filename_match = HASHED_IMAGE_RE.match(path.name)
            if not filename_match:
                errors.append(f"{sid}.{role}: 文件名不符合 <city>_<label>_<sha1-8> 格式：{path.name}")
                continue
            actual_prefix = filename_match.group("prefix").lower()
            if actual_prefix != expected_prefix:
                errors.append(
                    f"{sid}.{role}: city={city} 应使用 {expected_prefix}_ 前缀，实际为 {path.name}"
                )
            raw = path.read_bytes()
            actual_hash = hashlib.sha1(raw).hexdigest()[:8]
            filename_hash = filename_match.group("hash").lower()
            if filename_hash != actual_hash:
                errors.append(
                    f"{sid}.{role}: 文件名 hash={filename_hash}，实际 SHA1={actual_hash}：{path.name}"
                )
            if actual_prefix != expected_prefix or filename_hash != actual_hash:
                continue

            ext = filename_match.group("ext").lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            sight[data_key] = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
            embedded += 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"\nFAILED | {len(errors)} error(s)；未写入输出文件")
        return 1

    new_json = json.dumps(data, ensure_ascii=False, indent=2)
    output = html[: match.start(2)] + new_json + html[match.end(2) :]
    atomic_write(output_path, output)

    print(f"OK | 输入：{input_path.name}")
    print(f"OK | 输出：{output_path.name}")
    print(f"OK | 清理旧 Base64 字段：{removed} 个；重新内嵌图片：{embedded} 张")
    print(f"OK | HTML size = {output_path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
