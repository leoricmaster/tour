# Tour 工具栈

跨方案、跨年度复用的基础设施脚本。所有方案目录（`2026国庆假期/方案X_*/`、`2027*/方案X_*/` …）的景点图片维护都依赖这套工具。

## 脚本

| 脚本 | 作用 | 输入 | 输出 |
|---|---|---|---|
| `fetch_image.py` | 从 Wikimedia Commons 下载景点图，按新规则命名 | 方案目录路径 + jobs.json（必填 `city`） | `images/<city>_<sid>_<sha1-8hex>.jpg` + 打印 image_credits.json 片段 |
| `validate_itinerary.py` | 校验 JSON 关系、图片、Hash、授权清单和 Base64 状态 | 方案目录路径 + `--html`；分享版加 `--share` | 校验报告 + 退出码 |
| `regress_itinerary.py` | 对比渲染器结构不变量与基线 JSON（按方案自动选） | 方案目录路径 + `--html`；分享版加 `--share` | 校验报告 + 退出码 |
| `build_itinerary.py` | 从 data.json + 共享模板生成方案主 HTML | 方案目录路径 | `<scheme>游.html` |
| `build_base64.py` | 清除历史 Base64 后重新内嵌全部图片，生成单文件分享版 | 方案目录路径 + `--html` + `--output` | 独立的分享版 HTML |

`fetch_image.py` 自动完成 `image_credits.json` 元数据生成所需的 info（author/license/title/url/sha1_8/sight_id/city）。

## 模板与数据分离

`templates/` 存放跨方案复用的骨架：

```text
templates/itinerary.html.tpl    # HTML 壳，含 {{TITLE}} / {{CSS}} / {{DATA}} / {{JS}} 占位
templates/itinerary.css.tpl     # 共享 CSS（主题、卡片、表格、Tab、地图）
templates/itinerary.js.tpl      # 共享 JS 渲染器（不包含 <script> 包装）
```

每个方案目录的数据与产物：

```text
方案X_<简述>/
  data.json             # 数据源（必填、提交；包含 title、cities、sights、schedule…）
  image_credits.json    # 图片授权清单（提交）
  images/               # 物理图片（提交）
  <原名>游.html         # 构建产物，gitignore，需 build_itinerary.py 生成
  <原名>游_分享版.html  # 构建产物，gitignore，需 build_base64.py 生成
```

为什么不提交 HTML：它们是 data.json + 模板的合并结果，提交后易与数据脱钩、也不便 review。CI 拉下仓库后 build 一次即可。

## 标准工作流

```bash
# 1. 修改数据（编辑 data.json）
vi 方案X/data.json

# 2. 构建主 HTML（可选步骤：validate / regress 也可直接对 data.json 读出后的结构跑）
python3 tools/build_itinerary.py 方案X
python3 tools/validate_itinerary.py 方案X --html 方案X/<原名>游.html
python3 tools/regress_itinerary.py 方案X --html 方案X/<原名>游.html

# 3. 构建分享版
python3 tools/build_base64.py 方案X \
  --html <原名>游.html --output <原名>游_分享版.html
python3 tools/validate_itinerary.py 方案X \
  --html <原名>游_分享版.html --share
python3 tools/regress_itinerary.py 方案X \
  --html <原名>游_分享版.html --share
```

职责划分：

- `validate_itinerary.py` 负责静态数据 / 资源层：JSON、表格、路径、Hash、授权清单、Base64 状态
- `regress_itinerary.py` 负责渲染器结构层：表、Tab、卡片、地图 div 等 DOM 不变量
- `build_itinerary.py` 负责将 `data.json` 套上 `templates/` 生成产物 HTML
- `build_base64.py` 负责为 HTML 嵌入图片、生成可独立转发的分享版
- `baseline_<scheme>.json` 集中存放每个方案的渲染器计数基线

## 基线 JSON 命名

回归基线按方案划分，工具自动选取：

```text
tools/baseline_<方案目录名>.json   # 优先，如 baseline_方案A_普吉岛清迈.json
tools/baseline.json                # 兑底
```

`--baseline` 可显式指定其他路径。调整页面结构 / 表格行数 / Tab 数时同步更新对应基线。

## 图片命名规则（与 sight id 解耦）

所有景点图采用**全局唯一**文件名：

```
images/<city-prefix>_<sight-id>_<sha1-8hex>.jpg
```

- `city-prefix`: 2 字母城市缩写（`hk` / `pq` 富国岛 / `ph` 普吉 / `cm` 清迈 / …）
- `sight-id`: 业务标识字母（A/B/C/…，**仅作 label，不再作文件名**）
- `sha1-8hex`: 文件内容的 SHA1 前 8 位 — 才是图片的"真身份"

### 为什么引入 hash？

旧规则 `images/<sight-id>.jpg` 存在 3 个隐式约束：
1. 文件名 = sight id 字母 → 改 sight id 必须重命名 + 改引用
2. 不同 sight 共享字母（A 想用 Q.jpg，但 P 也想用）→ 撞名覆盖（真实腐烂案例：方案C 的 A/C/D/M/F 5 张图实际显示着别人的图）
3. 跨 city 同 sight id 必然撞名

新规则的好处：
- 改图（重新下载）→ 自动重命名，旧引用立即失效（断裂报警）
- 改 sight id 字母 → 文件名不变（hash 才是真身份），引用不变
- 跨 city 同 sight id → `hk_A_<hash>.jpg` vs `pq_A_<hash>.jpg`，不撞名
- 物理文件名 ↔ sight id 字母 完全解耦，**杜绝隐式耦合腐烂**

### 自动健康检查

`validate_itinerary.py` 会检查以下完整规则；`build_base64.py` 也会在内嵌前检查图片路径、城市前缀和 Hash：

1. `#data` JSON 可解析，必填数据结构存在
2. 景点 ID 唯一，日期与每日路线引用一致
3. 所有表格的列数一致
4. 图片文件存在，且路径不能逃出方案目录
5. 文件名前缀匹配 `sight.city`（`hk_` 对 hk，`pq_` 对 phuquoc）
6. 文件名里的 Hash 与文件实际 SHA1 一致
7. `image_credits.json` 与当前图片引用一一对应，关键元数据与 HTML 一致
8. 原版不得包含 Base64；分享版必须完整内嵌且内容与物理图片一致

任一硬错误都会退出码 1，**不静默通过**。未引用的物理图片只报警，不自动删除。

`build_base64.py` 每次都会先删除旧的 `imageData` / `extraImageData`，再从物理图片重建，避免残留过期图片。

## CITY_PREFIX 常量

`fetch_image.py`、`build_base64.py` 和 `validate_itinerary.py` 都维护同一组城市前缀：

```python
CITY_PREFIX = {
    "hk": "hk",
    "phuquoc": "pq",
    "phuket": "ph",
    "chiangmai": "cm",
}
```

新增城市时应同步补到三个脚本。`fetch_image.py` 对未知城市会暂用 `img` 前缀，但严格校验和分享版构建会要求先登记城市，避免产物带着临时前缀流出。

## image_credits.json 结构

新版按**物理文件名**作 key（不再按 sight id 字母），sight id 仅作 metadata：

```json
{
  "images/hk_J_be602af7.jpg": {
    "title": "File:Hong_Kong,_A_Symphony_of_Lights_(1).jpg",
    "author": "Krimuk2.0",
    "license": "CC BY-SA 4.0",
    "url": "https://commons.wikimedia.org/wiki/File:Hong_Kong,_A_Symphony_of_Lights_(1).jpg",
    "sha1_8": "be602af7",
    "sight_id": "J",
    "city": "hk",
    "role": "main"
  }
}
```

## 历史与原则

- 这套工具的引入背景：2026国庆方案C 在改图时发现 5 个 sights 因 sight id 隐式耦合而错位（详见 commit `0aa40bb`）。
- 教训：**任何"业务标识字母 + 物理文件名"的两边绑定都是腐烂信号**，必须用内容 hash 切断。
- 迁移是一次性的（旧的 `rename_images.py` 已删除），未来新方案从第一天就用新规则。
