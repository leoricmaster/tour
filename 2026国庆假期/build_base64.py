#!/usr/bin/env python3
"""
将来转单文件分享时使用：
  python3 build_base64.py
会把 images/*.jpg 读出来，base64 编码后写入 HTML 的 #data.sights[*].imageData，
并改用 data: URL 显示图片。完成后整个文档可以单文件转发，无需 images/ 目录。

前置：
- images/ 目录下已下载 A.jpg ~ O.jpg（15 张）
- 普吉岛清迈游.html 在同目录
"""
import re, json, base64, pathlib

BASE = pathlib.Path(__file__).parent
HTML = BASE / "普吉岛清迈游.html"
IMG_DIR = BASE / "images"

html = HTML.read_text(encoding="utf-8")
m = re.search(r'(<script type="application/json" id="data">)(.*?)(</script>)', html, re.S)
data = json.loads(m.group(2))

count, missing = 0, []
for sg in data["sights"]:
    path = BASE / sg.get("imagePath", "images/" + sg["id"] + ".jpg")
    if not path.exists():
        missing.append(sg["id"] + " (" + str(path) + ")")
        continue
    ext = path.suffix.lower().lstrip(".") or "jpeg"
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    sg["imageData"] = "data:" + mime + ";base64," + b64
    count += 1

print("已嵌入", count, "张图片到 #data.sights[*].imageData")
if missing:
    print("缺失：", missing)

new_js = json.dumps(data, ensure_ascii=False, indent=2)
HTML.write_text(html[:m.start(2)] + new_js + html[m.end(2):], encoding="utf-8")
print("OK | HTML size =", HTML.stat().st_size, "bytes")
print("提示：渲染器已支持 imageData 字段；保留 imagePath 不影响。")