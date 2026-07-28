#!/usr/bin/env python3
"""Build a scheme HTML from data.json + shared templates.

Usage:
  python3 tools/build_itinerary.py <scheme_dir>
  python3 tools/build_itinerary.py <scheme_dir> --data data.json --html 普吉岛清迈游.html

Outputs the scheme HTML next to data.json. The HTML is the same as the
historical single-file deliverable; it is gitignored (regenerate on demand).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


def default_html_name(scheme_dir_name: str) -> str:
    """Strip ``方案X_`` prefix and append ``游.html``.

    Examples
    --------
    >>> default_html_name("方案A_普吉岛清迈")
    '普吉岛清迈游.html'
    >>> default_html_name("方案C_富国岛香港")
    '富国岛香港游.html'
    """
    import re
    short = re.sub(r"^方案[A-Za-z0-9]+_", "", scheme_dir_name)
    return f"{short}游.html"


def render(scheme_dir: pathlib.Path, data_path: pathlib.Path, html_path: pathlib.Path | None) -> pathlib.Path:
    template_dir = pathlib.Path(__file__).resolve().parent.parent / "templates"
    html_tpl = (template_dir / "itinerary.html.tpl").read_text(encoding="utf-8")
    css_tpl = (template_dir / "itinerary.css.tpl").read_text(encoding="utf-8")
    js_tpl = (template_dir / "itinerary.js.tpl").read_text(encoding="utf-8")

    data = json.loads(data_path.read_text(encoding="utf-8"))
    title = data.get("title") or "行程"

    if html_path is None:
        html_path = scheme_dir / default_html_name(scheme_dir.name)

    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    output = html_tpl
    output = output.replace("{{TITLE}}", title)
    output = output.replace("{{CSS}}", css_tpl)
    output = output.replace("{{DATA}}", json_text)
    output = output.replace("{{JS}}", js_tpl)

    html_path.write_text(output, encoding="utf-8")
    return html_path


def main() -> int:
    parser = argparse.ArgumentParser(description="从 data.json + 模板生成方案 HTML")
    parser.add_argument("scheme_dir", help="方案目录（包含 data.json）")
    parser.add_argument("--data", default="data.json", help="数据文件名（默认 data.json）")
    parser.add_argument("--html", default=None, help="输出 HTML 文件名（默认 <scheme_dir.name>.html）")
    args = parser.parse_args()

    scheme_dir = pathlib.Path(args.scheme_dir).resolve()
    if not scheme_dir.is_dir():
        print(f"ERROR: 方案目录不存在：{scheme_dir}")
        return 1
    data_path = scheme_dir / args.data
    if not data_path.is_file():
        print(f"ERROR: 数据文件不存在：{data_path}")
        return 1

    try:
        output = render(scheme_dir, data_path, pathlib.Path(args.html) if args.html else None)
    except KeyError as exc:
        print(f"ERROR: 模板占位符未替换：{exc}")
        return 1

    print(f"OK | data: {args.data}")
    print(f"OK | html: {output.name}")
    print(f"OK | size: {output.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
