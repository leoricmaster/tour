#!/usr/bin/env python3
"""
通用维基图片下载工具：把景点图片下载到指定方案目录的 images/ 子目录。

用法：
  python3 fetch_image.py <方案目录> --jobs JOBS_JSON
  python3 fetch_image.py ../方案A_普吉岛清迈 --jobs jobs.json

JOBS_JSON 格式（json 文件）：
  [
    {"id": "A", "keyword": "Karon Beach Phuket", "title": null},
    {"id": "B", "keyword": null, "title": "File:Phuket_Viewpoint.jpg"}
  ]
  - keyword：维基搜索关键词（None 跳过搜索）
  - title：维基文件标题（None 用搜索结果的第一个非 SVG）

维基 API：commons.wikimedia.org（图片都在这里，免费 CC 协议）
"""
import urllib.request, urllib.parse, json, pathlib, time, re, html, sys, argparse

PROXY = "http://127.0.0.1:7897"  # 沙箱默认断网，需代理
UA = "TourPlanner/1.0 (personal)"

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
        out = img_dir / f"{sid}.jpg"

        if out.exists() and out.stat().st_size > 10000 and not args.force:
            print(f"{sid} 已存在且大小合理 ({out.stat().st_size//1024} KB)，跳过")
            skipped.append(sid)
            continue

        print(f"-> {sid}: ", end="")
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
            if download(url, out):
                results.append({"id": sid, "title": title, "author": author, "license": lic})
                print(f"   写入 {out.name} ({out.stat().st_size//1024} KB)")
            else:
                print(f"   下载失败 {url}")
        except Exception as e:
            print(f"  失败：{e}")
        time.sleep(4)  # 避免维基限流

    print(f"\n=== 完成 ===")
    print(f"下载 {len(results)} 张，跳过 {len(skipped)} 张")
    for r in results:
        print(f"  {r['id']}: {r['title']} | {r['author']} | {r['license']}")

    # 顺便输出可写入 image_credits.json 的格式
    if results:
        print("\n=== image_credits.json 片段 ===")
        for r in results:
            print(f'  "{r["id"]}": {{"title": "{r["title"]}", "author": "{r["author"]}", "license": "{r["license"]}"}},')

if __name__ == "__main__":
    main()