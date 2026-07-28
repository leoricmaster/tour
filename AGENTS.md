# AGENTS.md — AI 协作约定

> 本文件是给未来 AI 协作助手（Claude、Codex、Gemini 等）的工作约定。
> 每次会话开始时，AI 应**先读本文件**再行动。

---

## 0. 必读顺序

新会话开始，先读这些：

1. **本文件**（你正在读的）— 协作偏好
2. `README.md` — 项目结构
3. `tools/README.md` — 工具脚本（图片管理）
4. `guides/` — 参考知识（MCP 配置、后续方向）
5. `2026国庆假期/工作方法.md` — 行程规划流程

---

## 1. 协作偏好（最重要）

### 1.1 不要自动提交

- 修改文件后**先列出 diff 概要 + 询问确认**，再 `git commit`
- **绝不自动 `git push`**
- **绝不自动 `git commit --amend`** 除非用户明确同意
- 用户确认话术示例："好，提交" / "commit" / "可以"

### 1.2 改动前先描述计划

- 多文件改动：先列出"将改动哪些文件、改什么"，等用户确认
- 删除/重命名操作：必须事先说明，等用户确认（"全局不要重名"是反复强调的原则）
- 不要"先做了再说"

### 1.3 询问而非猜测

- 用户偏好模糊时，宁可多问一句
- 不要替用户做"是不是想要这样"的决定

---

## 2. 项目事实（写代码前必知）

### 2.1 项目性质

- **个人旅游行程规划库**（方案A/B/C 等）
- **自由行**，无领队、无旅行社；人员随家庭/朋友组合
- 真实出行前会被分享给同行人查看

### 2.2 真实性约束

行程信息（酒店/航班/景点/门票/费用）必须**可核验**，否则：

- ❌ 不要写 "省 ¥2,000+ 门票" / "VinWonders 住客免费入园" 等未验证省钱宣传
- ❌ 不要写未经核实的政策（如"联程行李直挂"）
- ✅ 改用中性表述："门票需单独购买，预订前可查官网"
- ✅ 标注"建议核实" / "参考值"

如果不确定，写明**信息源**或**建议核验渠道**。

### 2.3 人员规模提示

- 默认按**多人家庭**规划（每方案人数不同）
- 7 人 = 6 大 1 小 是当前典型规模
- 人数变化时同步检查：酒店房型（3 间房 vs 1 栋别墅）、机票张数、用餐安排

---

## 3. 文件管理约定

### 3.0 ⚠️ HTML 是构建产物，不是手编源

```text
templates/itinerary.{html,css,js}.tpl   ← 共享骨架（可手编）
<scheme>/data.json                     ← 逐方案数据（可手编）
<scheme>/<名>游.html                   ← 产物 ❌ 不要手编，改了会被覆盖
<scheme>/<名>游_分享版.html            ← 产物 ❌ 不要手编
```

主 HTML 是 `data.json` + `templates/` 的纯函数计算结果：

```bash
# 改 data.json 或 templates/ 后必须跑
python3 tools/build_itinerary.py <方案目录>          # 重新生成主 HTML
python3 tools/build_base64.py    <方案目录> \         # 生成分享版
  --html <名>游.html --output <名>游_分享版.html
```

**什么时候一定要跑 build**：

- 改了 `data.json`（价格、行程、说明、景点元数据等）
- 改了 `templates/`（CSS / JS / HTML 壳）
- 从其他机器拉取后没看到本地 HTML
- 调整 `image_credits.json`（图片路径虽然会被 build 读取，但分享版需要重建）

**什么时候不需要跑 build**：

- 只改 `images/` 里的图片文件本身
- 调整 `tools/` 里的校验脚本
- 修改文档（`README.md` / `AGENTS.md` / `tools/README.md`）

**如果意外手改了 HTML，验证是否能重新生成**：

```bash
# 跑 build 后 git diff HTML。如果 diff 只反映 data.json / templates/ 的预期变化，说明上游源已是最新，手改被覆盖了。
# 如果 diff 出现其他变化，要查清是手改了什么、是否要回写到上游。
```

### 3.1 模板 + data.json 数据/视图分离

项目走的是 "data.json + templates/ → HTML 构建产物" 的工作流：

```text
templates/itinerary.html.tpl   # HTML 壳（{{TITLE}} {{CSS}} {{DATA}} {{JS}}）
templates/itinerary.css.tpl    # 共享 CSS
templates/itinerary.js.tpl     # 共享 JS 渲染器

方案X/data.json                # 数据源（必填；含 title、cities、sights、dayPlan、dayColors…）
方案X/<名>游.html              # 构建产物，gitignore
方案X/<名>游_分享版.html       # 构建产物，gitignore
```

`data.json` 是源，HTML 是产物。不要在产物 HTML 里手改内容 — 下次 build 会被覆盖。

### 3.2 旧“分享版会覆盖原 HTML”的说法已过时

之前 `build_base64.py` 会覆盖原 HTML。项目现在的约定是：

- ❌ 不再保留 `富国岛香港游.html` 作为源
- ✅ 原 HTML 和 `_分享版.html` 都是产物（`build_itinerary.py` → `build_base64.py`）
- ✅ 修改走 `data.json`；跑 build 重新生成

`.gitignore` 已包含：

```
*_分享版.html
*_share.html
*_base64.html
2026国庆假期/方案*/*.html
```

### 3.3 图片命名规则（与 sight id 解耦）

**新规则**（已迁移完成）：

```
images/<city-prefix>_<sight-id>_<sha1-8hex>.jpg
```

- `city-prefix`: `hk_` / `pq_`（phuquoc）/`ph_`（phuket）/ `cm_`（chiangmai）
- `sight-id`: 业务标识字母（**仅作 label，不再作文件名**）
- `sha1-8hex`: 文件 SHA1 前 8 位 = 图片的"真身份"

**全局不重名** 是硬性约束 — 改图/换图时必须重新算 SHA1 重命名。

详见 `tools/README.md`。

---

## 4. 技术约束

### 4.1 网络/大陆可访问性

分享版 HTML 是给同行人在中国大陆打开的，**默认假设无 VPN**：

- ✅ CDN 优先 `cdn.staticfile.net` / `cdn.bootcdn.net` / `lib.baomitu.com`
- ❌ 避免 `unpkg.com` / `cdn.jsdelivr.net`（不稳定）
- ❌ 避免 `tile.openstreetmap.org`（被墙）

### 4.2 地图瓦片（核心踩坑）

| 城市 | 推荐瓦片源 | 备选 |
|---|---|---|
| **香港** | 高德矢量 (`webrd0{s}.is.autonavi.com/appmaptile?style=8`) | — |
| **富国岛（越南）** | `tile.openstreetmap.de`（Fastly CDN） | `basemaps.cartocdn.com/light_all` |
| **中国大陆** | 高德矢量 / 高德卫星图 | — |

**踩坑记录**：
- 高德矢量（`style=8`）对越南（胡志明市、富国岛）**全 zoom 空白**（179B 占位 PNG）
- 高德卫星图（`style=6`）对越南显示"此区域无卫星图"
- 智图 GeoQ / 天地图 / 谷歌 / OSM.org 国内均不可达
- 智图 GeoQ / OSM 中文镜像 不存在或 404

实现位置：HTML 内 `renderMap(city, ...)` 函数按 city 切换瓦片 URL。

### 4.3 HTML 渲染器约定

- 不在 HTML 里写 Markdown 语法（如 `**bold**`、`# header`）
- 描述文本是纯文本
- 代码中 emoji 可用，但避免花哨 Unicode（部分环境渲染异常）

---

## 5. 工具使用

### 5.1 必用工具（跨方案复用）

```bash
# 1. 抓图（Wikimedia Commons） — 写 data.json 后跑
python3 tools/fetch_image.py <方案目录>

# 2. 校验 data.json
python3 tools/validate_itinerary.py <方案目录> --html <方案目录>/<名>游.html
python3 tools/regress_itinerary.py  <方案目录> --html <方案目录>/<名>游.html

# 3. 构建产物
python3 tools/build_itinerary.py  <方案目录>        # 生成 <名>游.html
python3 tools/build_base64.py     <方案目录> \
  --html <名>游.html --output <名>游_分享版.html
```

详细用法见 `tools/README.md`。`build_base64.py` 默认拒绝覆盖原 HTML — 输出名必须以 `_分享版.html` / `_share.html` / `_base64.html` 结尾。

### 5.2 校验与构建职责

- `validate_itinerary.py` — 静态层（数据/图片/Hash/授权清单/Base64 状态）
- `regress_itinerary.py` — 渲染器结构层（Tab / 卡片 / 表格 / 地图 div 等 DOM 不变量）
- `build_itinerary.py` — 从 `data.json` 套模板生成 HTML
- `build_base64.py` — 为 HTML 嵌入图片、生成独立可转发的分享版
- `baseline_<方案目录名>.json` — 每个方案的渲染器计数基线

任何硬错误都会退出码 1，不静默通过。

---

## 6. 工作流备忘

### 6.1 行程优化类任务

典型流程（参考 2026 国庆方案C）：

1. 改航班 → 同步改 schedule / dayPlan / flights 表 / 预算
2. 改酒店 → 同步改 hotel 表 / 预算 / dayPlan 住宿列 / questions
3. 改人数 → 同步改预算/酒店房型/机票张数
4. 清理未验证信息 → 全文搜索后删除

### 6.2 提交信息风格

参考最近提交风格：

```
feat: 行程优化 — 航班改廉航 + 酒店精简 + 别墅方案
docs: 移除领队相关描述（自由行无领队）
chore: 清理图片命名 + 移除 MD 加粗 + 忽略分享版
fix: 富国岛地图切换到 OSM-DE
```

格式：`type: 中文一句话描述`，正文展开。

---

## 7. 沟通风格

- **简洁**：能 1 句说清不写 3 句
- **可执行**：给具体路径、命令、参数
- **不啰嗦**：不要每步都说"如果你想..."
- **明确报错**：遇到错误先报告再问"是否继续"
- **可视化数据**：用表格/列表代替段落