#!/usr/bin/env python3
"""重新下载 富国岛 + 香港 的景点图片（之前 LoremFlickr 抓的图大多错误）。
本脚本严格按"维基文件标题 → 真实 URL"流程，下载到 images/hk_phuquoc/。
"""
import urllib.request, urllib.parse, json, pathlib, time, re, html

BASE = pathlib.Path(__file__).parent
IMG_DIR = BASE / "images" / "hk_phuquoc"
IMG_DIR.mkdir(parents=True, exist_ok=True)

PROXY = "http://127.0.0.1:7897"
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
opener.addheaders = [("User-Agent", "TourPlanner/1.0 (personal)")]


def api_get(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    with opener.open(url, timeout=20) as r:
        return json.load(r)


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


# 景点 ID → 维基文件标题
# 已验证 1 张：T = Grand World（2023-07-30 Grand World Phú Quốc DSCF2045）
# 已有 1 张：U = Phu Quoc Night Market（Cho Dem Phu Quoc - Welcome to Phu Quoc Night Market）
# 重做：P, Q, R, S, V, W, X
# 注意：W 和 V 实际都是香港夜景（同一作者 Diliff + Benh LIEU SONG）

# 重新搜索关键词
def search_files(keyword, limit=5):
    d = api_get({"action": "query", "list": "search", "srsearch": keyword,
                 "srnamespace": "6", "srlimit": str(limit), "format": "json"})
    return [hit["title"] for hit in d["query"]["search"]]


# 主流程：先 search 找真实文件
JOBS = [
    # (id, search_keyword, override_file_title or None)
    ("P", "Kem Beach Phu Quoc Vietnam sand palm", None),
    ("Q", "Sao Beach Phu Quoc Bãi Sao white sand", None),
    ("R", "Hon Thom cable car Phu Quoc", None),
    ("S", "VinWonders Phu Quoc theme park entrance", None),
    # V 实际是太平山顶俯瞰维港（Diliff），应改成庙街；但庙街是 W 的概念
    # 实际重新分配：
    #   W → 太平山顶俯瞰（Diliff），与 I 太平山顶匹配
    #   V → 庙街夜市 / 油麻地
    #   X → 香港海洋公园
    #   I 实际是 Benh LIEU SONG 的香港夜景俯瞰（从维港一侧看），更适合"尖沙咀天际线"
    # 重做：
    ("V", "Temple Street Night Market Hong Kong Yau Ma Tei", None),
    ("X", "Ocean Park Hong Kong entrance", None),
    # W 已对应"太平山顶天际线"，文件 OK
]

results = []
for sid, keyword, override in JOBS:
    out = IMG_DIR / f"{sid}.jpg"
    if out.exists() and out.stat().st_size > 10000:
        # 简单启发式：>10KB 才算正常
        print(f"{sid} 已存在且大小合理 ({out.stat().st_size//1024} KB)，跳过")
        continue
    print(f"-> {sid}: search '{keyword}'")
    try:
        if override:
            title = override
        else:
            titles = search_files(keyword, 5)
            if not titles:
                print(f"   搜索无结果")
                continue
            # 取第一个非 .svg 文件（维基可能优先返回 SVG 缩略图）
            for t in titles:
                if not t.lower().endswith((".svg", ".gif", ".webm")):
                    title = t
                    break
            else:
                title = titles[0]
        print(f"   选文件: {title}")
        url, author, lic = fetch_imageinfo(title)
        if not url:
            print(f"   imageinfo 无结果")
            continue
        print(f"   author={author[:50]}  license={lic}")
        if download(url, out):
            results.append((sid, title, author, lic))
            print(f"   写入 {out.name} ({out.stat().st_size//1024} KB)")
        else:
            print(f"   失败：下载 {url}")
    except Exception as e:
        print(f"   失败：{e}")
    time.sleep(4)

print(f"\n成功下载 {len(results)} 张")
for sid, title, author, lic in results:
    print(f"  {sid}: {title} | {author} | {lic}")