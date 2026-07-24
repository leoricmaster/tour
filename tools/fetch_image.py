#!/usr/bin/env python3
"""
通用维基图片下载工具：把景点图片下载到指定方案目录的 images/ 子目录。

用法：
  python3 fetch_image.py <方案目录> --jobs JOBS_JSON
  python3 fetch_image.py ../方案A_普吉岛清迈 --jobs jobs.json

JOBS_JSON 格式（json 文件）：
  [
    {"id": "A", "keyword": "Karon Beach Phuket", "title": null, "city": "phuket"},
    {"id": "B", "keyword": null, "title": "File:Phuket_Viewpoint.jpg", "city": "phuket"}
  ]
  - keyword：维基搜索关键词（None 跳过搜索）
  - title：维基文件标题（None 用搜索结果的第一个非 SVG）
  - city：景点所在城市（必填）。值域：hk / phuquoc / phuket / ...
         文件名会用 city 前缀（hk_/pq_/ph_...），与 sight id 字母解耦

维基 API：commons.wikimedia.org（图片都在这里，免费 CC 协议）

文件命名格式（新）：<city-prefix>_<sight-id>_<sha1-8hex>.jpg
  - 改图后 hash 自动变 → 旧文件残留，新文件独立
  - 改 sight id 字母（如 A->X）不会撞名（哈希才是真身份）
  - 杜绝 sight id 与文件名隐式耦合腐烂
"""
import urllib.request, urllib.parse, json, pathlib, time, re, html, sys, argparse, hashlib

PROXY = "http://127.0.0.1:7897"  # 沙箱默认断网，需代理
UA = "TourPlanner/1.0 (personal)"

CITY_PREFIX = {
    "hk": "hk",
    "phuquoc": "pq",
    "phuket": "ph",
    "chiangmai": "cm",
}
DEFAULT_PREFIX = "img"  # 未知 city 的兜底前缀

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
opener.addheaders = [("User-Agent", UA)]


def api_get(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    with opener.open(url, timeout=20) as r:
        return json.load(r)


def search_files(keyword, limit=5):
    d = api_get({"action": "query", "list": "search", "srsearch": keyword,
                 "srnamespace": "6", "srlimit": str(limit), "format": "json"})
    return [hit["title"] for hit in d["query"]["search"]]


def fetch_imageinfo(file_title, width=960):
    d = api_get({"action": "query", "titles": file_title, "prop": "imageinfo",
                 "iiprop": "url|extmetadata", "iiurlwidth": str(width), "format": "json"})
    info = next(iter(d["query"]["pages"].values()))
    if "imageinfo" not in info:
        return None, None, None
    info0 = info["imageinfo"][0]
    thumb = info0["thumburl"]
    meta = info0.get("extmetadata", {})
    author = meta.get("Artist", {}).get("value", "Unknown")
    author = re.sub(r"<[^>]+>", "", html.unescape(author)).strip()
    license_ = meta.get("LicenseShortName", {}).get("value", "CC")
    return thumb, author, license_


def download(url, out_path, retries=3):
    for i in range(retries):
        try:
            with opener.open(url, timeout=30) as r:
                data = r.read()
            if len(data) < 5000:
                print(f"   跳过：文件太小（{len(data)} bytes）")
                return False
            out_path.write_bytes(data)
            return True
        except Exception as e:
            print(f"   重试 {i+1}/{retries}: {e}")
            time.sleep(3)
    return False


def main():
    parser = argparse.ArgumentParser(description="从维基下载景点图片到方案目录")
    parser.add_argument("scheme_dir", help="方案目录（包含 images/）")
    parser.add_argument("--jobs", required=True, help="JSON 文件，定义每个 ID 的搜索词或文件标题")
    parser.add_argument("--force", action="store_true", help="强制重下已存在的图")
    args = parser.parse_args()

    base = pathlib.Path(args.scheme_dir).resolve()
    img_dir = base / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    with open(args.jobs, encoding="utf-8") as f:
        jobs = json.load(f)

    results, skipped = [], []
    for job in jobs:
        sid = job["id"]
        keyword = job.get("keyword")
        title = job.get("title")
        city = job.get("city")
        if not city:
            print(f"-> {sid}: 缺少 city 字段，跳过（请在 jobs.json 中补 city）")
            continue
        prefix = CITY_PREFIX.get(city, DEFAULT_PREFIX)
        # 新格式：<prefix>_<sid>_<sha1-8hex>.jpg
        # 但下载前不知道 hash，所以先下载到临时文件，下载完再算 hash 重命名
        tmp_out = img_dir / f"{prefix}_{sid}.tmp.jpg"
        final_out = img_dir / f"{prefix}_{sid}.jpg"  # 占位（实际最终名带 hash）

        # 检查是否已有目标 sight 的图（按 sight id + city 找到现有 file）
        # 用 image_credits.json 找到 sight id 已有图，避免重下
        existing_for_sight = None
        credits_path = base / "image_credits.json"
        if credits_path.exists():
            try:
                creds = json.loads(credits_path.read_text(encoding="utf-8"))
                for fname, meta in creds.items():
                    if meta.get("sight_id") == sid and meta.get("city") == city:
                        existing_for_sight = img_dir / fname
                        break
            except Exception:
                pass

        if existing_for_sight and existing_for_sight.exists() and existing_for_sight.stat().st_size > 10000 and not args.force:
            print(f"{sid} 已存在 ({existing_for_sight.name}, {existing_for_sight.stat().st_size//1024} KB)，跳过")
            skipped.append(sid)
            continue

        print(f"-> {sid} (city={city}): ", end="")
        try:
            if not title and keyword:
                titles = search_files(keyword, 5)
                if not titles:
                    print("搜索无结果")
                    continue
                # 取第一个非 SVG/GIF/WebM
                title = next((t for t in titles if not t.lower().endswith((".svg", ".gif", ".webm"))), titles[0])
                print(f"搜到 '{title}'", end="")
            if not title:
                print("既无 keyword 也无 title，跳过")
                continue

            url, author, lic = fetch_imageinfo(title)
            if not url:
                print("imageinfo 无结果")
                continue
            print(f"  author={author[:30]}  license={lic}")
            if download(url, tmp_out):
                # 算 hash，重命名为最终名
                data_bytes = tmp_out.read_bytes()
                h = hashlib.sha1(data_bytes).hexdigest()[:8]
                final_out = img_dir / f"{prefix}_{sid}_{h}.jpg"
                # 如果目标已存在，删除后再 rename
                if final_out.exists():
                    final_out.unlink()
                tmp_out.rename(final_out)
                results.append({
                    "id": sid, "city": city, "title": title,
                    "author": author, "license": lic,
                    "filename": final_out.name, "sha1_8": h,
                })
                print(f"   写入 {final_out.name} ({final_out.stat().st_size//1024} KB)")
            else:
                if tmp_out.exists():
                    tmp_out.unlink()
                print(f"   下载失败 {url}")
        except Exception as e:
            print(f"  失败：{e}")
            if tmp_out.exists():
                tmp_out.unlink()
        time.sleep(4)  # 避免维基限流

    print(f"\n=== 完成 ===")
    print(f"下载 {len(results)} 张，跳过 {len(skipped)} 张")
    for r in results:
        print(f"  {r['id']}: {r['title']} | {r['author']} | {r['license']} | {r['filename']}")

    # 顺便输出可写入 image_credits.json 的格式
    if results:
        print("\n=== image_credits.json 片段（按新 filename 作 key） ===")
        for r in results:
            print(f'  "{r["filename"]}": {{"title": "{r["title"]}", "author": "{r["author"]}", "license": "{r["license"]}", "sha1_8": "{r["sha1_8"]}", "sight_id": "{r["id"]}", "city": "{r["city"]}"}},')

if __name__ == "__main__":
    main()