# Tour

个人旅游行程规划与方案库。

```
.
├── tools/            跨方案复用的脚本（抓图 / 内嵌 base64）
├── guides/           跨方案复用的参考文档（MCP 备忘 / 后续方向）
└── 2026国庆假期/     具体方案目录
    ├── lesson_learnt.md
    ├── 工作方法.md
    ├── 背景信息.md
    └── 方案X_*/      每个方案 = 自己的 HTML + images/ + image_credits.json
```

## 目录分工

- `tools/` 可执行脚本 — 详见 [tools/README.md](tools/README.md)
- `guides/` 参考文档 — 详见 [guides/README.md](guides/README.md)
- `2026国庆假期/` 项目产出（方案 HTML、攻略、备忘记录）

## 新建方案的标准流程

1. 在 `2026国庆假期/` 下新建 `方案X_<简述>/` 目录
2. 拷贝已有方案作为模板（HTML + images/ + image_credits.json）
3. 维护 `data.sights[]`（必填 `id` / `name` / `city` / `lat` / `lng` / `imagePath`）
4. 用 `tools/fetch_image.py` + `tools/build_base64.py` 下载并内嵌图片
5. 详见 [tools/README.md](tools/README.md) 关于图片命名规则
