#!/usr/bin/env python3
"""
通用 build_base64 工具：把指定方案目录下的 images/*.jpg 内嵌到 HTML，生成单文件分享版。

用法：
  python3 build_base64.py <方案目录> [--html HTML文件名]
  python3 build_base64.py ../方案A_普吉岛清迈
  python3 build_base64.py ../方案A_普吉岛清迈 --html 普吉岛清迈游.html

默认 HTML 文件名 = <方案目录名>.html（如"方案A_普吉岛清迈"→"方案A_普吉岛清迈.html"，
但实际可能叫"普吉岛清迈游.html"，所以通常需要 --html 显式指定）。

完成后整份 HTML 可独立转发（不需要 images/ 目录）。

健康检查：
  1) #data.sights[*].imagePath 必须指向真实存在的物理文件
  2) 文件名应符合新格式：<city-prefix>_<sight-id>_<sha1-8hex>.jpg（如 hk_J_be602af7.jpg）
  3) 文件名前缀必须匹配 sight.city（hk_ 对 hk，pq_ 对 phuquoc），杜绝 sight id 字母与文件隐式耦合
  4) 如果文件名不含 hash（旧格式），报警但不阻塞（向后兼容）
"""
import re, json, base64, pathlib, sys, argparse, hashlib

CITY_PREFIX = {"hk": "hk_", "phuquoc": "pq_"}


def main():
    parser = argparse.ArgumentParser(description="将方案的 images/*.jpg 内嵌到 HTML")
    parser.add_argument("scheme_dir", help="方案目录的路径（包含 .html 和 images/）")
    parser.add_argument("--html", help="HTML 文件名（默认 = 方案目录名.html）")
    args = parser.parse_args()

    base = pathlib.Path(args.scheme_dir).resolve()
    if not base.is_dir():
        print(f"错误：{base} 不是目录")
        sys.exit(1)

    html_name = args.html or (base.name + ".html")
    html_path = base / html_name
    if not html_path.exists():
        print(f"错误：HTML 文件不存在 {html_path}")
        sys.exit(1)

    html = html_path.read_text(encoding="utf-8")
    m = re.search(r'(<script type="application/json" id="data">)(.*?)(</script>)', html, re.S)
    if not m:
        print(f"错误：HTML 中找不到 #data JSON 块")
        sys.exit(1)
    data = json.loads(m.group(2))

    count, missing = 0, []
    warnings = []
    for sg in data["sights"]:
        sid = sg.get("id", "?")
        city = sg.get("city", "")
        for role, key, dest in [
            ("main", "imagePath", "imageData"),
            ("extra", "extraImagePath", "extraImageData"),
        ]:
            rel = sg.get(key)
            if not rel:
                continue
            path = base / rel
            if not path.exists():
                missing.append(f"{sid}.{role}({rel})")
                continue

            # 健康检查：文件名格式
            fname = path.name
            expected_prefix = CITY_PREFIX.get(city, "")
            if expected_prefix and fname.startswith(expected_prefix):
                # 校验 hash
                mhash = re.match(r'^[a-z]+_[A-Za-z0-9_]+_([0-9a-f]{8})\.jpg$', fname)
                if mhash:
                    actual_hash = hashlib.sha1(path.read_bytes()).hexdigest()[:8]
                    if actual_hash != mhash.group(1):
                        warnings.append(
                            f"{sid}.{role}：文件名 hash {mhash.group(1)} 与实际 {actual_hash} 不符！"
                            f"（说明有人改图但没改文件名）"
                        )
            elif expected_prefix:
                warnings.append(
                    f"{sid}.{role}：文件名 {fname} 仍为旧格式（无 city prefix），"
                    f"建议运行 rename_images.py 迁移"
                )

            ext = path.suffix.lower().lstrip(".") or "jpeg"
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            sg[dest] = "data:" + mime + ";base64," + b64
            count += 1

    print(f"已嵌入 {count} 张图片到 #data.sights[*].imageData")
    if missing:
        print(f"\n缺失 {len(missing)} 张（必须修复！）：")
        for m_ in missing:
            print(f"  - {m_}")
    if warnings:
        print(f"\n警告 {len(warnings)} 条：")
        for w_ in warnings:
            print(f"  - {w_}")
    if missing:
        sys.exit(1)

    new_js = json.dumps(data, ensure_ascii=False, indent=2)
    html_path.write_text(html[:m.start(2)] + new_js + html[m.end(2):], encoding="utf-8")
    print(f"\nOK | HTML size = {html_path.stat().st_size} bytes")
    print(f"提示：渲染器已支持 imageData 字段；保留 imagePath 不影响。")

if __name__ == "__main__":
    main()