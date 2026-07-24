#!/usr/bin/env python3
"""
图片命名彻底重构：把 images/<sight-id>.jpg 改为 images/<city>_<sight-id>_<sha1-8hex>.jpg
并一次性更新 #data 里的 imagePath / extraImagePath。

核心原则（根治 sight id 字母与文件名错位腐烂）：
  1. 物理文件名 = city 缩写 + sight id 业务标识 + 文件内容 SHA1 前 8 位
     - 文件名包含 hash：改图 / 换图 → hash 变 → 文件名变 → 旧引用立即失效（断裂报警）
     - 文件名不依赖 sight id 字母顺序：重命名 sight id 不会撞到别人的文件
  2. #data 里只存 imagePath（新的物理路径），不再有 sight id 与文件名的隐式约定
  3. image_credits.json 改为按 新 filename 作 key（彻底脱离 sight id 依赖）

用法：
  python3 rename_images.py <方案目录>
"""
import hashlib, json, pathlib, re, sys


def sha1_8(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:8]


def migrate(scheme_dir: pathlib.Path) -> None:
    img_dir = scheme_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    html_path = scheme_dir / "富国岛香港游.html"
    if not html_path.exists():
        # 尝试其他常见名
        for cand in scheme_dir.glob("*.html"):
            html_path = cand
            break

    text = html_path.read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', text, re.S)
    if not m:
        raise SystemExit("找不到 #data JSON 块")
    data = json.loads(m.group(1))

    # city -> prefix 映射
    city_prefix = {"phuquoc": "pq", "hk": "hk"}

    # 1) 收集所有 (sight, role) -> 老路径
    # role: "main" or "extra"
    # 给每个 sight 按出现顺序生成 sort key (city 内部按 id 字母序，保持稳定)
    items = []  # (sight, role, old_path)
    for sg in sorted(data["sights"], key=lambda x: (x.get("city", ""), x.get("id", ""))):
        if sg.get("imagePath"):
            items.append((sg, "main", sg["imagePath"]))
        if sg.get("extraImagePath"):
            items.append((sg, "extra", sg["extraImagePath"]))

    # 2) 计算每个老文件的新文件名（city + sight id + sha1_8）
    #    同一文件可能被多个 sight 引用（目前不会，但留防），以首次出现的 sight 为准
    old_to_new = {}  # old_relpath -> new_relpath
    name_counter = {}  # 防止同 sight+role 重复（不该发生）
    for sg, role, old_rel in items:
        old_path = scheme_dir / old_rel
        if not old_path.exists():
            print(f"  警告：{old_rel} 不存在，跳过")
            continue
        if old_rel in old_to_new:
            # 复用首次结果
            continue
        city = sg.get("city", "?")
        prefix = city_prefix.get(city, city[:2])
        sid = sg.get("id", "X")
        data_bytes = old_path.read_bytes()
        h = sha1_8(data_bytes)
        new_name = f"{prefix}_{sid}_{h}.jpg"
        # 去重保险
        key = (prefix, sid, role)
        if key in name_counter:
            # 同 sight+role 不应该重复，强制加后缀
            new_name = f"{prefix}_{sid}_{h}_{name_counter[key]}.jpg"
        name_counter[key] = name_counter.get(key, 0) + 1
        new_rel = f"images/{new_name}"
        old_to_new[old_rel] = new_rel

    # 3) 重命名物理文件
    for old_rel, new_rel in old_to_new.items():
        old_p = scheme_dir / old_rel
        new_p = scheme_dir / new_rel
        if old_p == new_p:
            continue
        if new_p.exists():
            new_p.unlink()  # 覆盖
        old_p.rename(new_p)
        print(f"  {old_rel} -> {new_rel}")

    # 4) 扫一遍 images/，删掉不参与 manifest 的孤儿文件
    #    注意：只删文件名不在 keep 且 #data 也不引用的（旧文件名已被重命名）
    keep = set(old_to_new.values())
    # 收集 #data 里所有还引用的文件名（防止误删）
    referenced = set()
    for sg in data["sights"]:
        for k in ("imagePath", "extraImagePath"):
            if sg.get(k):
                referenced.add(sg[k])
    for p in img_dir.iterdir():
        rel = f"images/{p.name}"
        if rel not in keep and rel not in referenced:
            # 文件名是旧的（已经被重命名过）
            if any(p.name.startswith(prefix + "_") for prefix in ("hk_", "pq_")):
                continue  # 已经是新格式，跳过
            # 也不在 #data 引用里 → 真孤儿
            if rel in old_to_new:
                continue  # 正在被本次重命名
            print(f"  删除孤儿: {rel}")
            p.unlink()

    # 5) 更新 #data：替换 imagePath / extraImagePath
    for sg in data["sights"]:
        if sg.get("imagePath") in old_to_new:
            sg["imagePath"] = old_to_new[sg["imagePath"]]
        if sg.get("extraImagePath") in old_to_new:
            sg["extraImagePath"] = old_to_new[sg["extraImagePath"]]

    # 6) 写回 #data
    new_js = json.dumps(data, ensure_ascii=False, indent=2)
    html_path.write_text(text[:m.start(1)] + new_js + text[m.end(1):], encoding="utf-8")
    print(f"  #data 同步完成（{len(old_to_new)} 张图）")

    # 7) 重写 image_credits.json：按新 filename 作 key
    #    优先用 HTML 里的 credit；image_credits.json 作为补足（如有遗留 sight id key）
    try:
        credits = json.loads((scheme_dir / "image_credits.json").read_text(encoding="utf-8"))
    except Exception:
        credits = {}
    new_credits = {}
    for sg in data["sights"]:
        for role, key, rel in [
            ("main", "imageCredit", sg.get("imagePath")),
            ("extra", "extraImageCredit", sg.get("extraImagePath")),
        ]:
            if not rel:
                continue
            cred = sg.get(key) or {}
            # 用文件名（含 hash）作 key
            fname = pathlib.Path(rel).name
            full_path = scheme_dir / rel
            h = sha1_8(full_path.read_bytes()) if full_path.exists() else None
            # 保留 metadata：title/author/license/url + sight info
            entry = {
                "title": cred.get("title") or cred.get("url", "").split("/")[-1] or fname,
                "author": cred.get("author", "Unknown"),
                "license": cred.get("license", "CC"),
                "url": cred.get("url", ""),
                "sha1_8": h,
                "sight_id": sg.get("id"),
                "city": sg.get("city"),
                "role": role,
            }
            new_credits[fname] = entry
    (scheme_dir / "image_credits.json").write_text(
        json.dumps(new_credits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  image_credits.json 重写：{len(new_credits)} 项（按新 filename）")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法：python3 rename_images.py <方案目录>")
    migrate(pathlib.Path(sys.argv[1]).resolve())