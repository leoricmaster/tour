# 经验 · 给未来的自己

> 这份文档用来记录制作旅行行程 HTML 时遇到的关键问题与通用经验，避免下次再踩坑。
> 文档**不保存任何特定方案的内容**（如"普吉岛某酒店价格"、"富国岛某景点 day 编号"等），这些都写在各自 HTML 的 `#data` 里。

---

## 1. HTML 渲染器架构（通用）

所有方案共用同一个渲染器（见 普吉岛清迈游.html 的 `<script>` 渲染器）。它的工作流程：

1. 读 `<script type="application/json" id="data">` 块的 JSON 数据
2. 克隆 `<template>` 生成 DOM
3. 调用 `renderTable / renderMap` 等工具函数

**维护原则**：未来增删内容只改 `#data` JSON；改样式只改 `:root` CSS 变量；JS 渲染器不要动。

## 2. 三级图片加载策略（通用）

每张景点图在 `#data.sights[*]` 中可填三个字段：

1. `imageData`  → `data:image/jpeg;base64,...`（内嵌，分享时用）
2. `imagePath` → 相对路径（本地，开发用）
3. **缺省兜底** → 渲染器自动用 `https://loremflickr.com/...` 占位

**重要**：**填了 `imagePath` 但本地图不存在 / 填了但本地图是错的**——渲染器仍按你填的 `imagePath` 加载，**不会**自动降级到 LoremFlickr。所以：

- 本地不存在 → 浏览器会显示 404 图标
- 本地存在但内容错误 → 浏览器会显示错误图

两种情况都不是 LoremFlickr 占位。**这是关键踩坑**（见 3a）。

## 3. 关键陷阱与对策（通用）

### 3.1 维基裸引 URL 容易失效
维基共享资源的 URL 含 MD5 前两位路径（如 `/thumb/4/4e/...`），**不能从文件名推算**，只能通过 API 取。

**正确做法**：用维基 API 拿真实 URL：
```
https://commons.wikimedia.org/w/api.php?action=query&titles=File:Karon_Beach.jpg&prop=imageinfo&iiprop=url|iiurlwidth=960&format=json
```
返回 JSON 里的 `thumburl` 才是稳定的图片 URL。

### 3.2 沙箱（Trae IDE）默认断网
curl / WebFetch 直连外网会被屏蔽。
**对策**：通过本地代理 `http://127.0.0.1:7897`（Clash/V2Ray 默认端口）出去。

### 3.3 维基限流 429
连续请求会触发 `HTTP 429 Too Many Requests`。**每个搜索之间 sleep 3-5 秒**。
若脚本大批量下载，加重试 + 指数退避（15s, 30s, 60s）。

### 3.4 维基 API 强制要求 User-Agent
裸 urllib 请求会被 403。**必须**加 User-Agent：
```python
opener.addheaders = [("User-Agent", "TourPlanner/1.0 (personal)")]
```

### 3.5 维基 API 关键词搜索不准
搜 "Karon Beach" 第一个结果可能是 "沙滩排球比赛"，而不是海景。
**对策**：
- 准备多个 fallback 关键词
- **下载完肉眼检查图片内容**——不合适的直接换
- 关键词加修饰：`"Karon Beach sunset"`、`"Karon Beach aerial"` 等

### 3.6 维基图床 HTTPS 偶尔 SSL EOF
代理链路下偶发 `SSL: UNEXPECTED_EOF_WHILE_READING`。
**对策**：下载加 3-4 次重试，每次 sleep 3 秒。

### 3.7 维基 API 文件名必须精确匹配（含空格/重音/标点）
搜索接口返回的 `File:xxx.jpg` 标题里有空格、各种语言重音（Phú Quốc）、下划线等；
直接复制搜索结果的标题去 `imageinfo` 查询才会成功，**不可改写为简化名**。

## 3a. 图片正确性是隐性 bug（关键）

`imagePath` 填了，本地图也存在，但**图片内容是错的**——这种情况渲染器不会报错，浏览器也不会降级，直接显示错图。

**踩坑案例**：维基搜 "VinWonders Phu Quoc" 可能返回普吉老城的彩色街照片（关键词命中"Vin"在旅游城市名），下载下来配 VinWonders 主题乐园完全错位。

**对策**：
1. **下载完必须肉眼检查每张图**
2. 不要相信"维基搜到了"就一定对——关键词歧义经常导致错配
3. 渲染器本身**无法发现**这种错误（文件存在即视为正确）

## 3b. MCP 工具覆盖范围（关键约束）

可用 MCP 工具的局限性：

- `mcp_RollingGo-Hotel`：**只对泰国境内酒店返回有效数据**。其他地区（香港/越南/日本/欧洲等）返回空或不相关结果
- `mcp_12306`：**只支持中国铁路**，不支持国际航班查询
- 其他通用搜索工具：可能不覆盖景点门票、餐厅、当地交通

**对策**：
- 国际航班 / 非泰国酒店：必须靠经验估算 + OTA 平台（Booking / Agoda / 航司官网）实时核实
- **不要假托 MCP 数据**：写"参考价，待核实"是诚实做法

## 3c. 多方案 ID/图片 冲突（关键）

同一项目目录放多个方案的 HTML 时，**图片 ID 冲突是隐性 bug**：
- 两个方案都用 `images/P.jpg` 命名，但语义不同
- 一个方案说 P=普吉大佛，另一个说 P=富国岛 Kem Beach
- 共享目录是危险的

**对策**：每个方案**独立的子目录**（不是再嵌套子目录，是按方案分子目录）：

```
项目根/
├── 背景信息.md
├── lesson_learnt.md       ← 本文件
├── 方案A_普吉岛清迈/
│   ├── 普吉岛清迈游.html
│   ├── image_credits.json
│   └── images/             ← 该方案所有图片
├── 方案B_xxx/                  （将来扩展）
└── tools/
    ├── build_base64.py     ← 通用工具，不专属方案
    └── fetch_image.py      ← 通用维基下载工具
```

**关键**：
- HTML 内部的 `imagePath` 用相对路径 `images/X.jpg`（HTML 在子目录里，相对 `images/` 就是自己方案的 images）
- 工具脚本必须接受参数（`scheme_dir`），不写死任何方案名
- 这样加新方案时**只需复制一份方案子目录 + 改内容**即可，零冲突

## 4. 改图的标准流程（下次再用）

如果将来需要换图（比如某景点图不满意、或新增景点）：

1. **确认是哪个方案**：进入 `方案X_xxx/` 子目录
2. 在 `方案X_xxx/images/` 里存新图，命名为 `{ID}.jpg`
3. （可选）运行 `tools/fetch_image.py 方案X_xxx --jobs jobs.json` 查维基拿到作者/协议
4. 把图注对应的 `imageCredit` 字段更新到对应 HTML 的 `#data.sights` JSON 块里
5. **肉眼检查新图是否真的对应该景点**（防止关键词歧义）
6. 浏览器刷新即可

## 5. 维基 API 下载图片

用 `tools/fetch_image.py`（已模板化）：

```bash
cd tools
# 1) 准备 jobs.json
cat > /tmp/jobs.json <<EOF
[
  {"id": "A", "keyword": "Karon Beach Phuket", "title": null},
  {"id": "B", "keyword": null, "title": "File:Phuket_Viewpoint.jpg"}
]
EOF

# 2) 下载
python3 fetch_image.py ../方案A_普吉岛清迈 --jobs /tmp/jobs.json
# 强制重下：加 --force
```

模板核心代码（仅参考，不再单独用）：

```python
import urllib.request, urllib.parse, json

PROXY = "http://127.0.0.1:7897"
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)
opener.addheaders = [("User-Agent", "TourPlanner/1.0 (personal)")]

def api_get(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    with opener.open(url, timeout=20) as r:
        return json.load(r)

# 1) 搜索文件名
d = api_get({"action": "query", "list": "search", "srsearch": "Karon Beach Phuket",
             "srnamespace": "6", "srlimit": "5", "format": "json"})
title = d["query"]["search"][0]["title"]   # File:xxx.jpg

# 2) 取真实 URL
d = api_get({"action": "query", "titles": title, "prop": "imageinfo",
             "iiprop": "url|extmetadata", "iiurlwidth": "960", "format": "json"})
info = next(iter(d["query"]["pages"].values()))["imageinfo"][0]
thumb = info["thumburl"]
meta = info["extmetadata"]
author = meta["Artist"]["value"]
license = meta["LicenseShortName"]["value"]

# 3) 下载
import pathlib
out = pathlib.Path("images/方案名/A.jpg")
with opener.open(thumb, timeout=30) as r:
    out.write_bytes(r.read())

# 4) 肉眼检查图片内容
```

> **历史背景**：此模板早期独立放在 `工具/fetch_image.py`（中文目录），已迁移到 `tools/fetch_image.py` 避免 Python 编码坑，详见 commit `ce4892e`。

## 6. `build_base64.py` 用法（单方案分享，通用工具）

**用途**：把指定方案目录下的 `images/*.jpg` 内嵌进 HTML，生成单文件（约 1.5-2MB），方便微信/邮件转发。

**使用时机**：
- 整个行程规划**最终确定后**（不再改图）
- 准备分享给**没有该项目目录**的人时

**怎么用**：
```bash
cd tools
python3 build_base64.py ../方案A_普吉岛清迈 --html 普吉岛清迈游.html --output 普吉岛清迈游_分享版.html
```
脚本会：
1. 读 `方案A_普吉岛清迈/images/` 下的所有 jpg（按 HTML 里 `imagePath` 字段的引用）
2. base64 编码后写入 **新 HTML** 的 `#data.sights[*].imageData`（不修改原 HTML）
3. 新 HTML 文件变大到 ~2MB

之后整份 HTML 即可独立转发（不需要 images/ 目录）。

**参数**：
- `scheme_dir`（必填）：方案目录路径
- `--html`（必填）：源 HTML 文件名
- `--output`（必填）：输出文件名，必须以 `_分享版.html` / `_share.html` / `_base64.html` 结尾（脚本会拒绝覆盖原 HTML）

**注意**：`build_base64.py` 是**通用工具**（在 `tools/` 目录），不专属任何方案。所有方案共用一份。

**还原**：想恢复成"外部图片"版本，只需在 HTML 里把所有 `imageData` 字段删除（渲染器会自动降级到 imagePath）。

## 7. 文档维护原则（通用）

- **单源**：每个方案永远是 HTML 一份，不要再建 MD 副本
- **结构 vs 数据分离**：HTML 结构（template/render）只改模板；内容只改 JSON
- **图片本地化**：所有用到的图片下到对应方案的 `images/` 子目录（不再用 `images/<方案名>/`），不要依赖外链
- **方案隔离**：每个方案独立的 HTML / images 子目录 / image_credits JSON / fetch 脚本
- **修改零依赖**：脚本用纯 Python 标准库；CSS/JS 全部内联；不引入 npm/pip
- **可降级**：每个外部依赖都有兜底（imageData→imagePath→LoremFlickr）
- **离线优先**：打开 HTML 即可阅读，联网只是附加（地图瓦片）
- **肉眼检查图片**：下载完必须肉眼检查每张图是否对应正确景点

## 8. 一句话总结

> 图片正确性靠肉眼检查不靠程序；多方案用子目录隔离；维基搜索关键词歧义是错图最大来源。