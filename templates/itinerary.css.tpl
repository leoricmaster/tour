/* ============================================================
     主题与布局：所有视觉变量集中在 :root，便于未来换皮
     ============================================================ */
  :root {
    --bg: #f7f8fa;
    --card: #ffffff;
    --border: #e5e7eb;
    --text: #1f2937;
    --muted: #6b7280;
    --primary: #0ea5e9;
    --primary-dark: #0369a1;
    --accent: #f59e0b;
    --radius: 10px;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    margin: 0;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
  }
  header {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: #fff;
    padding: 28px 24px;
  }
  header h1 { margin: 0 0 6px; font-size: 26px; }
  header .sub { opacity: 0.9; font-size: 14px; }

  main { max-width: 1100px; margin: 0 auto; padding: 24px; }
  section { margin-bottom: 32px; }
  h2 {
    border-left: 4px solid var(--primary);
    padding-left: 12px;
    font-size: 22px;
    margin: 24px 0 16px;
  }
  section > h2:first-child { margin-top: 0; }
  h3 { font-size: 17px; margin: 0 0 8px; color: var(--primary-dark); }
  h4 { font-size: 15px; margin: 0 0 8px; color: var(--text); font-weight: 600; }

  /* 卡片栅格（景点卡 / 方案卡） */
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 16px;
    display: grid;
    grid-template-columns: 280px 1fr;
    transition: box-shadow 0.2s;
  }
  .card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
  .card img {
    width: 100%;
    height: 200px;
    object-fit: cover;
    display: block;
    background: #e5e7eb;
  }
  .card .body { padding: 14px 18px; }
  .meta { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
  .stars { color: var(--accent); font-weight: 600; }

  /* 表格（航班 / 每日行程 / 酒店 / 机酒预算） */
  table {
    width: 100%;
    border-collapse: collapse;
    background: var(--card);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  th {
    background: var(--primary-dark);
    color: #fff;
    padding: 10px 12px;
    text-align: left;
    font-size: 14px;
  }
  th abbr { cursor: help; border-bottom: 1px dotted rgba(255,255,255,0.6); text-decoration: none; }
  td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
    vertical-align: top;
  }
  tr:last-child td { border-bottom: none; }

  /* 提示块 / 引用 */
  .note {
    background: #fef3c7;
    border-left: 4px solid var(--accent);
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 14px;
    color: #78350f;
    margin-bottom: 12px;
  }
  blockquote {
    background: #eef9ff;
    border-left: 4px solid var(--primary);
    margin: 0 0 12px;
    padding: 8px 14px;
    color: #0c4a6e;
    border-radius: 0 6px 6px 0;
  }
  ul.check { list-style: none; padding-left: 0; }
  ul.check li { padding-left: 20px; position: relative; margin-bottom: 4px; }
  ul.check li::before { content: "✓"; color: var(--primary); position: absolute; left: 0; font-weight: 700; }

  .img-credit { font-size: 11px; color: var(--muted); margin-top: 4px; }
  .map-intro { color: var(--muted); font-size: 14px; margin-top: 0; }
  .section-spaced { margin-top: 16px; }
  img.broken { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); }

  /* 方案卡内的总费用高亮 */
  .plan-total { font-weight: 700; color: var(--primary-dark); }

  /* 计划卡（机酒方案 / 行程预算） */
  .plan-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 16px;
    overflow: hidden;
  }
  .plan-card .body { padding: 14px 18px; }
  .plan-card .plan-title { font-size: 18px; margin-bottom: 6px; }

  /* Leaflet 地图容器 */
  .leaflet-map {
    height: 520px;
    width: 100%;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: #e5e7eb;
  }
  /* 自定义 marker（按日着色） */
  .day-marker {
    width: 32px;
    height: 32px;
    border-radius: 50% 50% 50% 0;
    transform: rotate(-45deg);
    border: 2px solid #fff;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-weight: 700;
    font-size: 13px;
  }
  .day-marker span { transform: rotate(45deg); }
  /* 弹窗样式覆盖 */
  .leaflet-popup-content { margin: 10px 14px; font-size: 13px; line-height: 1.5; }
  .leaflet-popup-content h4 { margin: 0 0 4px; font-size: 14px; color: var(--primary-dark); }
  /* 地图图例 */
  .map-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    margin-top: 8px;
    padding: 8px 12px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 12px;
  }
  .map-legend .lg-item { display: flex; align-items: center; gap: 6px; }
  .map-legend .lg-dot { width: 14px; height: 14px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }

  /* Tab 导航 */
  .tab-bar {
    display: flex;
    gap: 4px;
    background: var(--card);
    border-bottom: 2px solid var(--border);
    padding: 0 8px;
    margin: 0 0 20px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
    overflow-x: auto;
    white-space: nowrap;
  }
  .tab-bar button {
    background: transparent;
    border: 0;
    padding: 12px 18px;
    font-size: 15px;
    font-weight: 600;
    color: var(--muted);
    cursor: pointer;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    transition: color 0.15s, border-color 0.15s;
    font-family: inherit;
  }
  .tab-bar button:hover { color: var(--primary-dark); }
  .tab-bar button.active {
    color: var(--primary-dark);
    border-bottom-color: var(--primary);
  }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* 表格横向滚动容器（移动端友好） */
  .table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }

  @media (max-width: 720px) {
    .card { grid-template-columns: 1fr; }
    .card img { height: 180px; }
    .leaflet-map { height: 420px; }
    .tab-bar button { padding: 10px 12px; font-size: 14px; }
  }
