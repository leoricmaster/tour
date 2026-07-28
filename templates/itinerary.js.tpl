(function () {
  'use strict';
  const app = document.getElementById('app');
  let data;
  try {
    data = JSON.parse(document.getElementById('data').textContent);
  } catch (err) {
    app.innerHTML =
      '<section><h2>数据加载失败</h2>' +
      '<div class="note"><strong>JSON 解析错误</strong>：' +
      err.message + '<br><br>' +
      '请打开 <code>#data</code> 脚本块检查引号、逗号、方括号是否成对。' +
      '常见原因：描述中误用了英文双引号 " 而非中文弯引号 " "。</div></section>';
    console.error(err);
    return;
  }

  // 工具：从 <template> 克隆
  function tpl(id) {
    return document.getElementById(id).content.firstElementChild.cloneNode(true);
  }
  // 工具：构建景点卡片
  function buildSightCard(sg) {
    const c = tpl('tpl-sight');
    const tags = (sg.tags || []).join(',');
    const img = c.querySelector('img');
    img.src = sg.imageData || sg.imagePath || ('https://loremflickr.com/640/400/' + tags);
    img.loading = 'lazy';
    img.decoding = 'async';
    img.addEventListener('error', function once() {
      img.removeEventListener('error', once);
      if (sg.imageData) {
        img.src = sg.imagePath || ('https://loremflickr.com/640/400/' + tags);
      }
      img.classList.add('broken');
    });
    img.alt = sg.name;
    const h3 = c.querySelector('h3');
    h3.appendChild(document.createTextNode(sg.id + '. ' + sg.name + ' '));
    const stars = document.createElement('span');
    stars.className = 'stars';
    stars.textContent = '⭐'.repeat(sg.stars);
    h3.appendChild(stars);
    c.querySelector('.meta').textContent = '📍 ' + sg.area + ' · 建议 ' + sg.duration;
    c.querySelector('.desc').textContent = sg.desc;
    const credit = c.querySelector('.img-credit');
    if (sg.imagePath) {
      const cred = sg.imageCredit || {};
      const author = cred.author || 'Anonymous';
      const license = cred.license || 'CC';
      credit.textContent = '图：' + author + ' · ' + license + ' · via Wikimedia Commons';
    } else {
      credit.textContent = '图：LoremFlickr（关键词 ' + tags + '）';
    }
    return c;
  }
  // 工具：插入 section（可选 h2；title 为空则不创建 h2，避免与 tab 标题重复），可指定父容器（默认 app）
  function section(title, num, parent) {
    const s = document.createElement('section');
    if (title) {
      const h = document.createElement('h2');
      h.textContent = (num != null ? (num + '. ') : '') + title;
      s.appendChild(h);
    }
    (parent || app).appendChild(s);
    return s;
  }
  // 工具：把二维数组渲染成 table（外层加横向滚动容器）
  function renderTable(rows, opts) {
    const highlightLast = !(opts && opts.highlightLast === false);
    const wrap = document.createElement('div');
    wrap.className = 'table-scroll';
    const tbl = tpl('tpl-table');
    const thead = tbl.querySelector('thead');
    const tbody = tbl.querySelector('tbody');
    const head = rows[0];
    const headRow = document.createElement('tr');
    head.forEach(c => {
      const th = document.createElement('th');
      th.textContent = c;
      th.setAttribute('scope', 'col');
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    rows.slice(1).forEach(r => {
      const tr = document.createElement('tr');
      r.forEach((c, idx) => {
        const td = document.createElement('td');
        td.textContent = c;
        if (highlightLast && idx === r.length - 1) td.className = 'plan-total';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    wrap.appendChild(tbl);
    return wrap;
  }
  // 工具：把重点信息渲染为 blockquote
  function renderStatus(text) {
    const el = document.createElement('blockquote');
    el.textContent = text;
    return el;
  }
  // 工具：把重点信息提示块（高亮 + 描述）渲染为 note
  function renderNote(label, text) {
    const note = document.createElement('div');
    note.className = 'note';
    const strong = document.createElement('strong');
    strong.textContent = label + '：';
    note.appendChild(strong);
    note.appendChild(document.createTextNode(text));
    return note;
  }

  // Tab UI：3 个顶层 tab（行程概览 / 城市行程 / 城市行程）
  const tabs = [
    { id: 'tab-overview', label: '行程概览（9/25-10/4）' }
  ].concat(
    data.cities.map(city => ({ id: 'tab-' + city.id, label: city.tabLabel, cityId: city.id }))
  );
  const tabBar = document.createElement('nav');
  tabBar.className = 'tab-bar';
  tabBar.setAttribute('role', 'tablist');
  tabs.forEach((t, i) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'btn-' + t.id;
    btn.textContent = t.label;
    btn.dataset.target = t.id;
    btn.setAttribute('role', 'tab');
    btn.setAttribute('aria-controls', t.id);
    btn.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
    btn.setAttribute('tabindex', i === 0 ? '0' : '-1');
    if (i === 0) btn.classList.add('active');
    btn.addEventListener('click', () => switchTab(t.id));
    tabBar.appendChild(btn);
  });
  app.appendChild(tabBar);
  const tabPanels = {};
  tabs.forEach((t, i) => {
    const panel = document.createElement('div');
    panel.id = t.id;
    panel.className = 'tab-panel' + (i === 0 ? ' active' : '');
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', 'btn-' + t.id);
    app.appendChild(panel);
    tabPanels[t.id] = panel;
  });
  function switchTab(id) {
    const buttons = document.querySelectorAll('.tab-bar button');
    buttons.forEach(b => {
      const active = b.dataset.target === id;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active ? 'true' : 'false');
      b.setAttribute('tabindex', active ? '0' : '-1');
    });
    document.querySelectorAll('.tab-panel').forEach(p =>
      p.classList.toggle('active', p.id === id));
    window.__mapInstances = window.__mapInstances || {};
    Object.keys(window.__mapPending || {}).forEach(city => {
      if (id !== 'tab-' + city) return;
      if (!window.__mapInstances[city] && window.__mapPending[city]) {
        window.__mapInstances[city] = window.__mapPending[city]() || null;
      } else if (window.__mapInstances[city]) {
        window.__mapInstances[city].invalidateSize();
      }
    });
  }
  tabBar.addEventListener('keydown', (ev) => {
    if (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return;
    const buttons = Array.from(tabBar.querySelectorAll('button'));
    const current = buttons.findIndex(b => b === document.activeElement);
    if (current === -1) return;
    const next = (current + (ev.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
    ev.preventDefault();
    buttons[next].focus();
    switchTab(buttons[next].dataset.target);
  });
  const tabOverview = tabPanels['tab-overview'];

  // 1) Tab 1：行程概览（overview + 行程安排 + 航班 + 酒店 + 机酒方案 + 注意事项 + 下一步 + 待确认）
  {
    const s = section(null, null, tabOverview);

    // 1.1 行程概览（数组：label/value）
    if (Array.isArray(data.overview) && data.overview.length) {
      const h = document.createElement('h2');
      h.textContent = '行程概览';
      s.appendChild(h);
      const ul = document.createElement('ul');
      ul.className = 'check';
      data.overview.forEach(o => {
        const li = document.createElement('li');
        const strong = document.createElement('strong');
        strong.textContent = o.label;
        li.appendChild(strong);
        li.appendChild(document.createTextNode('：' + o.value));
        ul.appendChild(li);
      });
      s.appendChild(ul);
    }

    // 1.2 行程安排
    const h1 = document.createElement('h2');
    h1.textContent = '行程安排';
    s.appendChild(h1);
    s.appendChild(renderTable(data.schedule, { highlightLast: false }));

    // 1.3 航班概览
    const h2 = document.createElement('h2');
    h2.textContent = '航班概览';
    s.appendChild(h2);
    s.appendChild(renderStatus(data.flightStatus));
    s.appendChild(renderTable(data.flights, { highlightLast: false }));
    if (data.flightNote) s.appendChild(renderNote('航班说明', data.flightNote));

    // 1.4 酒店概览
    const h3 = document.createElement('h2');
    h3.textContent = '酒店概览';
    s.appendChild(h3);
    s.appendChild(renderStatus(data.hotelStatus));
    if (data.hotelNote) s.appendChild(renderNote('价格说明', data.hotelNote));
    data.cities.forEach((city, idx) => {
      const sub = document.createElement('h4');
      if (idx > 0) sub.className = 'section-spaced';
      sub.textContent = city.hotelHeading;
      s.appendChild(sub);
      s.appendChild(renderTable(data.hotels[city.id], { highlightLast: false }));
    });

    // 1.5 行程预算（budget 或 plans 二选一）
    if (data.budget) {
      const h4 = document.createElement('h2');
      h4.textContent = '行程预算';
      s.appendChild(h4);
      s.appendChild(renderTable(data.budget.rows, { highlightLast: false }));
      if (data.budget.note) s.appendChild(renderNote('价格说明', data.budget.note));
    } else if (Array.isArray(data.plans) && data.plans.length) {
      const h4 = document.createElement('h2');
      h4.textContent = '机酒方案';
      s.appendChild(h4);
      if (Array.isArray(data.plansNote) && data.plansNote.length) {
        const note = document.createElement('div');
        note.className = 'note';
        const strong = document.createElement('strong');
        strong.textContent = '重要说明';
        note.appendChild(strong);
        const ol = document.createElement('ol');
        ol.style.margin = '6px 0 0 18px';
        ol.style.padding = '0';
        data.plansNote.forEach(t => {
          const li = document.createElement('li');
          li.textContent = t;
          ol.appendChild(li);
        });
        note.appendChild(ol);
        s.appendChild(note);
      }
      data.plans.forEach(p => {
        const card = document.createElement('div');
        card.className = 'plan-card';
        const body = document.createElement('div');
        body.className = 'body';
        const title = document.createElement('div');
        title.className = 'plan-title';
        title.textContent = p.name;
        body.appendChild(title);
        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = p.meta;
        body.appendChild(meta);
        body.appendChild(renderTable(p.rows));
        card.appendChild(body);
        s.appendChild(card);
      });
    }

    // 1.6 注意事项
    if (Array.isArray(data.notes) && data.notes.length) {
      const h5 = document.createElement('h2');
      h5.textContent = '注意事项';
      s.appendChild(h5);
      const ul = document.createElement('ul');
      data.notes.forEach(n => {
        const li = document.createElement('li');
        li.textContent = n;
        ul.appendChild(li);
      });
      s.appendChild(ul);
    }

    // 1.7 下一步
    if (Array.isArray(data.nextSteps) && data.nextSteps.length) {
      const h6 = document.createElement('h2');
      h6.textContent = '下一步';
      s.appendChild(h6);
      const ol = document.createElement('ol');
      data.nextSteps.forEach(n => {
        const li = document.createElement('li');
        li.textContent = n;
        ol.appendChild(li);
      });
      s.appendChild(ol);
    }

    // 1.8 待确认
    if (Array.isArray(data.questions) && data.questions.length) {
      const h7 = document.createElement('h2');
      h7.textContent = '待确认';
      s.appendChild(h7);
      const ol = document.createElement('ol');
      data.questions.forEach(q => {
        const li = document.createElement('li');
        li.textContent = q;
        ol.appendChild(li);
      });
      s.appendChild(ol);
    }
  }

  // 2/3) Tab 2-N：城市行程（行程规划 + 景点介绍）
  data.cities.forEach(city => {
    const panel = tabPanels['tab-' + city.id];
    const s = section(null, null, panel);

    const h1 = document.createElement('h2');
    h1.textContent = '行程规划';
    s.appendChild(h1);

    const mapIntro = document.createElement('p');
    mapIntro.className = 'map-intro';
    mapIntro.textContent = city.map.intro;
    s.appendChild(mapIntro);
    const div = document.createElement('div');
    div.id = 'map-' + city.id;
    div.className = 'leaflet-map';
    s.appendChild(div);
    const credit = document.createElement('p');
    credit.className = 'img-credit';
    credit.textContent = city.map.credit;
    s.appendChild(credit);
    window.__mapPending = window.__mapPending || {};
    window.__mapPending[city.id] = () => renderMap(
      city.id, 'map-' + city.id, city.map, data.sights, data.dayColors, data.dayRoutes
    );

    const plan = data.dayPlan[city.id];
    if (plan) {
      s.appendChild(renderTable(plan.rows));
      if (Array.isArray(plan.reasons) && plan.reasons.length) {
        const reasons = document.createElement('div');
        reasons.className = 'note';
        const strong = document.createElement('strong');
        strong.textContent = '地理分块理由';
        reasons.appendChild(strong);
        reasons.appendChild(document.createTextNode('：'));
        const ul = document.createElement('ul');
        ul.style.margin = '6px 0 0 18px';
        ul.style.padding = '0';
        plan.reasons.forEach(r => {
          const li = document.createElement('li');
          li.textContent = r;
          ul.appendChild(li);
        });
        reasons.appendChild(ul);
        s.appendChild(reasons);
      }
    }

    const h2 = document.createElement('h2');
    h2.textContent = '景点介绍';
    s.appendChild(h2);

    if (city.sightsExcludes) {
      const ex = document.createElement('blockquote');
      ex.textContent = city.sightsExcludes;
      s.appendChild(ex);
    }

    data.sights.filter(x => x.city === city.id).forEach(sg => {
      s.appendChild(buildSightCard(sg));
    });
  });

  // 最后维护日期来自数据
  document.getElementById('gen-time').textContent =
    '统一维护版（HTML 唯一源） · 最后更新：' + data.meta.updatedAt;

  /**
   * Leaflet 地图渲染：
   *   - 多 marker（每日编号+按日着色）
   *   - 弹窗（景点名 + 推荐指数 + 区域）
   *   - 每日路线连线（按 dayRoutes.sights 顺序）
   *   - 自定义图例（按日色块）
   *
   * mapCfg 支持字段：
   *   tile     'amap'（高德）或 'osm-de'（OSM 德国镜像）
   *   maxZoom  fitBounds 限制的最大缩放级别（可选）
   *   center/zoom 由 dayPlan 之外的全局配置给出（不在本函数读取）
   */
  function renderMap(city, divId, mapCfg, allSights, dayColors, dayRoutes) {
    if (typeof L === 'undefined') {
      document.getElementById(divId).innerHTML =
        '<div style="padding:24px;color:#b91c1c;">Leaflet CDN 加载失败，请检查网络。</div>';
      return;
    }
    // 中心/缩放：用 dayRoutes 第一天非空路线 → 中心，否则默认普吉/清迈
    const citySights = allSights.filter(sg => sg.city === city && sg.lat && sg.lng);
    const fallbackCenter = city === 'phuket' ? [7.85, 98.3] : [18.85, 98.97];
    const fallbackZoom = city === 'phuket' ? 11 : 10;
    let center = fallbackCenter, zoom = fallbackZoom;
    if (citySights.length) {
      const lats = citySights.map(sg => sg.lat);
      const lngs = citySights.map(sg => sg.lng);
      center = [(Math.min(...lats) + Math.max(...lats)) / 2, (Math.min(...lngs) + Math.max(...lngs)) / 2];
      zoom = fallbackZoom;
    }
    const map = L.map(divId).setView(center, zoom);
    const tile = (mapCfg && mapCfg.tile) || 'osm-de';
    const tileCfg = (tile === 'osm-de')
      ? {
          url: 'https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png',
          subdomains: ['a', 'b', 'c'],
          maxZoom: 18,
          attribution: '© OpenStreetMap-DE / OSM contributors'
        }
      : {
          url: 'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
          subdomains: ['1', '2', '3', '4'],
          maxZoom: 19,
          attribution: '© 高德地图 AutoNavi'
        };
    L.tileLayer(tileCfg.url, {
      maxZoom: tileCfg.maxZoom,
      subdomains: tileCfg.subdomains,
      attribution: tileCfg.attribution
    }).addTo(map);

    const colorByDay = {};
    dayColors.forEach(d => colorByDay[d.id] = d.color);

    const markers = [];
    const group = L.featureGroup();
    citySights.forEach(sg => {
      const color = colorByDay[sg.day] || '#666';
      const icon = L.divIcon({
        className: '',
        html: '<div class="day-marker" style="background:' + color + ';"><span>' + sg.id + '</span></div>',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
      });
      const m = L.marker([sg.lat, sg.lng], { icon: icon });
      m.bindPopup(
        '<h4>' + sg.id + '. ' + sg.name + '</h4>' +
        '<div style="color:' + color + ';font-weight:600;">' +
        (dayColors.find(d => d.id === sg.day) || {}).label + '</div>' +
        '<div style="color:#6b7280;font-size:12px;">📍 ' + sg.area + '</div>' +
        '<div style="margin-top:4px;">⏱ ' + sg.duration + '</div>' +
        '<div style="margin-top:4px;">推荐指数：<span style="color:#f59e0b;">' + '⭐'.repeat(sg.stars) + '</span></div>'
      );
      group.addLayer(m);
      markers.push({ id: sg.id, latlng: [sg.lat, sg.lng], day: sg.day });
    });
    group.addTo(map);

    const routes = (dayRoutes[city] || []).filter(d => d.sights.length >= 2);
    routes.forEach(d => {
      const pts = d.sights.map(sid => {
        const m = markers.find(x => x.id === sid);
        return m ? m.latlng : null;
      }).filter(Boolean);
      if (pts.length >= 2) {
        const color = colorByDay[d.day] || '#666';
        const line = L.polyline(pts, {
          color: color,
          weight: 3,
          opacity: 0.7,
          dashArray: '6, 6'
        }).addTo(map);
        line.getLatLngs().forEach(ll => group.addLayer(L.marker(ll, { opacity: 0, interactive: false })));
      }
    });

    if (group.getLayers().length > 0) {
      const maxZoom = (mapCfg && typeof mapCfg.maxZoom === 'number') ? mapCfg.maxZoom : 13;
      map.fitBounds(group.getBounds().pad(0.12), { maxZoom: maxZoom });
    }

    const legend = document.createElement('div');
    legend.className = 'map-legend';
    const usedDays = Array.from(new Set(citySights.map(sg => sg.day)))
      .filter(d => d !== null && d !== undefined)
      .sort((a, b) => a - b);
    usedDays.forEach(dayId => {
      const d = dayColors.find(x => x.id === dayId);
      if (!d) return;
      const item = document.createElement('div');
      item.className = 'lg-item';
      item.innerHTML = '<span class="lg-dot" style="background:' + d.color + ';"></span>' + d.label;
      legend.appendChild(item);
    });
    document.getElementById(divId).parentNode.insertBefore(legend, document.getElementById(divId).nextSibling);
    return map;
  }
})();