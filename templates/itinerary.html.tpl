<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>

<!-- Leaflet 地图库（CDN · 国内静态资源 · 大陆可访问） -->
<link rel="stylesheet" href="https://cdn.staticfile.net/leaflet/1.9.4/leaflet.min.css" crossorigin="">
<script src="https://cdn.staticfile.net/leaflet/1.9.4/leaflet.min.js" crossorigin=""></script>
<style>
{{CSS}}
</style>
</head>
<body>

<header>
  <h1>{{TITLE}}</h1>
  <div class="sub" id="gen-time"></div>
</header>

<main id="app"></main>

<template id="tpl-sight">
  <div class="card">
    <img alt="" onerror="this.classList.add('broken')">
    <div class="body">
      <h3></h3>
      <div class="meta"></div>
      <p class="desc"></p>
      <div class="img-credit"></div>
    </div>
  </div>
</template>

<template id="tpl-table">
  <table>
    <thead></thead>
    <tbody></tbody>
  </table>
</template>

<script type="application/json" id="data">
{{DATA}}
</script>

<script>
{{JS}}
</script>

</body>
</html>
