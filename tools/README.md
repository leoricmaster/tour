# Tour 工具栈

跨方案、跨年度复用的基础设施脚本。所有方案目录（`2026国庆假期/方案X_*/`、`2027*/方案X_*/` …）的景点图片维护都依赖这套工具。

## 脚本

| 脚本 | 作用 | 输入 | 输出 |
|---|---|---|---|
| `fetch_image.py` | 从 Wikimedia Commons 下载景点图，按新规则命名 | 方案目录路径 + jobs.json（必填 `city`） | `images/<city>_<sid>_<sha1-8hex>.jpg` + 打印 image_credits.json 片段 |
| `build_base64.py` | 内嵌 `images/*.jpg` 到 HTML，生成自包含单文件分享版 | 方案目录路径 + 可选 `--html` | 更新后的 HTML（含 `imageData` 字段） |

`fetch_image.py` 自动完成 `image_credits.json` 元数据生成所需的 info（author/license/title/url/sha1_8/sight_id/city）。

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

### build_base64.py 的健康检查

嵌入时强制校验每个 imagePath：
1. 文件存在
2. 文件名前缀匹配 sight.city（`hk_` 对 hk，`pq_` 对 phuquoc）
3. 文件名里的 hash 与文件实际 SHA1 一致（防止改图但忘改文件名）

不一致会报警 + 退出码 1，**不静默通过**。

## CITY_PREFIX 常量

`fetch_image.py` 顶部维护：

```python
CITY_PREFIX = {
    "hk": "hk",
    "phuquoc": "pq",
    "phuket": "ph",
    "chiangmai": "cm",
}
```

新增城市时补一行即可。未知 city 降级到 `img` 前缀。

## image_credits.json 结构

新版按**物理文件名**作 key（不再按 sight id 字母），sight id 仅作 metadata：

```json
{
  "hk_J_be602af7.jpg": {
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
