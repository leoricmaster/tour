# Tour

个人旅游行程规划与方案库。

```
.
├── tools/            跨方案复用的脚本（抓图 / 内嵌 base64 / 校验 / 构建）
├── templates/        跨方案复用的 HTML 骨架（css / js / html-shell）
├── guides/           跨方案复用的参考文档（MCP 备忘 / 后续方向）
└── 2026国庆假期/     具体方案目录
    ├── lesson_learnt.md
    ├── 工作方法.md
    ├── 背景信息.md
    └── 方案X_<简述>/
        ├── data.json              ← 数据源（提交）
        ├── image_credits.json     ← 图片授权清单（提交）
        ├── images/                ← 物理图片（提交）
        ├── <名>游.html            ← 构建产物（gitignore）
        └── <名>游_分享版.html     ← 构建产物（gitignore）
```

## 目录分工

- `tools/` 可执行脚本 — 详见 [tools/README.md](tools/README.md)
- `templates/` 跨方案 HTML 骨架（CSS / JS / HTML 壳）— 详见 [tools/README.md § 模板与数据分离](tools/README.md)
- `guides/` 参考文档 — 详见 [guides/README.md](guides/README.md)
- `2026国庆假期/` 项目产出（方案数据、图片、攻略、备忘记录）

## 新建方案的标准流程

1. 在 `2026国庆假期/` 下新建 `方案X_<简述>/` 目录
2. 拷贝 `data.json` / `image_credits.json` / `images/` 作为骨架（**不再拷贝 HTML**）
3. 维护 `data.sights[]`（必填 `id` / `name` / `city` / `lat` / `lng` / `imagePath`）
4. 用 `tools/fetch_image.py` 下载图片、`tools/build_itinerary.py` 生成 HTML、`tools/build_base64.py` 生成分享版
5. 用 `tools/validate_itinerary.py` + `tools/regress_itinerary.py` 跑校验
6. 详见 [tools/README.md](tools/README.md) 关于图片命名规则与构建流程
