from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(prefix="/card", tags=["card"])


CARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spotify Rewrapped</title>
  <style>
    :root {
      --bg: #0b0c10;
      --panel: #111827;
      --border: rgba(255,255,255,0.08);
      --muted: #cbd5e1;
      --accent: #8ab4f8;
      --text: #f5f7fb;
      --shadow: 0 20px 60px rgba(0,0,0,0.35);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); display: flex; flex-direction: column; align-items: center; }
    .card { width: min(960px, 95vw); padding: 28px; margin: 32px 0; background: linear-gradient(135deg, var(--panel), var(--bg)); border-radius: 20px; box-shadow: var(--shadow); border: 1px solid var(--border); }
    h1 { margin: 0 0 4px; font-size: 26px; }
    .muted { color: var(--muted); font-size: 14px; margin: 0 0 12px; }
    .controls-card { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin: 14px 0 22px; }
    .controls { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
    select, button { background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; font-size: 14px; }
    button { cursor: pointer; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }
    .section { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 14px; padding: 14px; }
    .section h3 { margin: 0 0 10px; }
    .item { display: flex; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .item:last-child { border-bottom: none; }
    .rank { width: 32px; text-align: right; color: var(--accent); font-weight: 600; }
    .title { flex: 1; margin-left: 12px; }
    .subtitle { color: var(--muted); font-size: 13px; }
    .error { color: #f87171; margin-top: 12px; }
    .cover-row { display: flex; justify-content: center; align-items: center; gap: 0; margin-top: 12px; padding: 6px 0; }
    .cover-bubble { width: 96px; height: 96px; border-radius: 50%; overflow: hidden; border: 2px solid rgba(255,255,255,0.1); box-shadow: 0 8px 22px rgba(0,0,0,0.35); background: #111; margin-left: -24px; }
    .cover-bubble:first-child { margin-left: 0; }
    .cover-bubble img { width: 100%; height: 100%; object-fit: cover; display: block; }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>Spotify Rewrapped</h1>
      <p class="muted">Side-by-side top tracks and artists from your Spotify profile.</p>
    </div>
    <div class="controls-card">
      <div class="controls">
        <label>
          <span class="muted">Range</span><br>
          <select id="range">
            <option value="short">Short (last ~4 weeks)</option>
            <option value="medium">Medium (last ~6 months)</option>
            <option value="long" selected>Long (multi-year)</option>
          </select>
        </label>
        <label>
          <span class="muted">Top limit</span><br>
          <select id="limit">
            <option>5</option><option selected>10</option><option>20</option><option>50</option>
          </select>
        </label>
        <div>
          <button id="refresh">Refresh</button>
        </div>
      </div>
      <p class="muted">Short ~ last 4 weeks; Medium ~ last 6 months; Long = multi-year history (Spotify buckets).</p>
    </div>
    <h2 id="heading" style="margin: 0 0 12px;">Top 10 (multi-year)</h2>
    <div class="grid">
      <div class="section">
        <h3>Top Tracks</h3>
        <div id="tracks"></div>
      </div>
      <div class="section">
        <h3>Top Artists</h3>
        <div id="artists"></div>
      </div>
    </div>
    <div class="cover-row" id="covers"></div>
    <div id="error" class="error"></div>
  </div>
  <div style="width: min(960px, 95vw); display: flex; justify-content: center; margin: 0 0 32px;">
    <button id="save-basic">Save image</button>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
  <script>
    const rangeLabels = { short: "last ~4 weeks", medium: "last ~6 months", long: "multi-year" };
    async function fetchData() {
      const range = document.getElementById('range').value;
      const limit = document.getElementById('limit').value;
      const heading = document.getElementById('heading');
      const err = document.getElementById('error');
      err.textContent = '';
      try {
        const res = await fetch(`/wrapped/${range}?top_limit=${limit}`);
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        const data = await res.json();
        const user = (data.user && (data.user.display_name || data.user.id)) || "Unknown user";
        heading.textContent = `${user}'s Top ${limit} (${rangeLabels[range]})`;
        render('tracks', data.top_tracks || [], t => ({
          title: t.name,
          subtitle: (t.artists || []).join(', ')
        }));
        render('artists', data.top_artists || [], a => ({
          title: a.name,
          subtitle: (a.genres || []).slice(0,3).join(', ')
        }));
        renderCovers('covers', data.top_tracks || []);
      } catch (e) {
        err.textContent = e.message;
      }
    }
    function renderCovers(containerId, list) {
      const el = document.getElementById(containerId);
      el.innerHTML = '';
      (list || []).filter(t => t.image_url).slice(0, 20).forEach((track, i) => {
        const margin = i === 0 ? '0' : '-16px';
        el.insertAdjacentHTML('beforeend', `
          <div class="cover-bubble" style="margin-left:${margin}">
            <img src="${track.image_url}" alt="${track.name || ''}">
          </div>
        `);
      });
    }
    async function saveCard() {
      const card = document.querySelector('.card');
      const canvas = await html2canvas(card, { useCORS: true, scale: 2 });
      const link = document.createElement('a');
      link.download = 'spotify-rewrapped.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
    function render(containerId, list, mapFn) {
      const el = document.getElementById(containerId);
      el.innerHTML = '';
      (list || []).forEach((item, i) => {
        const mapped = mapFn(item);
        el.insertAdjacentHTML('beforeend', `
          <div class="item">
            <div class="rank">${i+1}</div>
            <div class="title">
              <div>${mapped.title || ''}</div>
              <div class="subtitle">${mapped.subtitle || ''}</div>
            </div>
          </div>
        `);
      });
    }
    document.getElementById('refresh').addEventListener('click', fetchData);
    document.getElementById('save-basic').addEventListener('click', saveCard);
    fetchData();
  </script>
</body>
</html>
"""


EXTENDED_CARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spotify Rewrapped - Themes</title>
  <style>
    :root {
      --bg: #0b0c10;
      --panel: #111827;
      --border: rgba(255,255,255,0.08);
      --muted: #cbd5e1;
      --accent: #8ab4f8;
      --text: #f5f7fb;
      --shadow: 0 20px 60px rgba(0,0,0,0.35);
      --pattern: radial-gradient(circle at 20% 20%, rgba(255,255,255,0.03) 0, transparent 40%), radial-gradient(circle at 80% 0%, rgba(255,255,255,0.05) 0, transparent 35%);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); display: flex; flex-direction: column; align-items: center; }
    .page { width: min(1100px, 95vw); padding: 28px; margin: 32px 0; background: var(--pattern), linear-gradient(135deg, var(--panel), var(--bg)); border-radius: 24px; box-shadow: var(--shadow); border: 1px solid var(--border); }
    h1 { margin: 0 0 6px; font-size: 28px; }
    .muted { color: var(--muted); font-size: 14px; margin: 0 0 12px; }
    .controls-card { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin: 16px 0 22px; }
    .controls { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
    select, button { background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; font-size: 14px; }
    button { cursor: pointer; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }
    .section { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 14px; padding: 14px; }
    .section h3 { margin: 0 0 10px; }
    .item { display: flex; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .item:last-child { border-bottom: none; }
    .rank { width: 32px; text-align: right; color: var(--accent); font-weight: 600; }
    .title { flex: 1; margin-left: 12px; }
    .subtitle { color: var(--muted); font-size: 13px; }
    .error { color: #f87171; margin-top: 12px; }
    .pill { display: inline-flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 999px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--muted); }
    .theme-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--accent); }
    .cover-row { display: flex; justify-content: center; align-items: center; gap: 0; margin-top: 12px; padding: 6px 0; }
    .cover-bubble { width: 96px; height: 96px; border-radius: 50%; overflow: hidden; border: 2px solid rgba(255,255,255,0.12); box-shadow: 0 8px 22px rgba(0,0,0,0.35); background: #111; margin-left: -24px; }
    .cover-bubble:first-child { margin-left: 0; }
    .cover-bubble img { width: 100%; height: 100%; object-fit: cover; display: block; }
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <h1>Spotify Rewrapped</h1>
      <p class="muted">Top tracks and artists with themed cards inspired by ML, cosmic travel, gothic whimsy, and entropy.</p>
    </div>
    <div class="controls-card">
      <div class="controls">
        <label>
          <span class="muted">Range</span><br>
          <select id="range">
            <option value="short">Short (last ~4 weeks)</option>
            <option value="medium">Medium (last ~6 months)</option>
            <option value="long" selected>Long (multi-year)</option>
          </select>
        </label>
        <label>
          <span class="muted">Top limit</span><br>
          <select id="limit">
            <option>5</option><option selected>10</option><option>20</option><option>50</option>
          </select>
        </label>
        <label>
          <span class="muted">Theme</span><br>
          <select id="theme">
            <option value="ml">Machine Learning</option>
            <option value="hitchhiker">Hitchhiker's Guide</option>
            <option value="unfortunate">Series of Unfortunate Events</option>
            <option value="entropy" selected>Entropy</option>
          </select>
        </label>
        <div>
          <button id="refresh">Refresh</button>
        </div>
      </div>
      <p class="muted">Short ~ last 4 weeks; Medium ~ last 6 months; Long = multi-year history (Spotify buckets).</p>
      <div class="pill" id="pill"><span class="theme-dot"></span><span id="pillText">Entropy - decay, glow, and noise</span></div>
    </div>
    <h2 id="heading" style="margin: 0 0 12px;">Top 10 (multi-year)</h2>
    <div class="grid">
      <div class="section">
        <h3>Top Tracks</h3>
        <div id="tracks"></div>
      </div>
      <div class="section">
        <h3>Top Artists</h3>
        <div id="artists"></div>
      </div>
    </div>
    <div class="cover-row" id="covers-extended"></div>
    <div id="error" class="error"></div>
  </div>
  <div style="width: min(1100px, 95vw); display: flex; justify-content: center; margin: 0 0 32px;">
    <button id="save-extended">Save image</button>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
  <script>
    const rangeLabels = { short: "last ~4 weeks", medium: "last ~6 months", long: "multi-year" };
    const themes = {
      ml: {
        bg: "#05060a",
        panel: "#0c111a",
        border: "rgba(0,255,163,0.18)",
        accent: "#35ffb2",
        muted: "#9fb8c6",
        pattern: "radial-gradient(circle at 20% 20%, rgba(53,255,178,0.12) 0, transparent 35%), radial-gradient(circle at 80% 0%, rgba(53,255,178,0.08) 0, transparent 35%)",
        pill: "Neon meshes and signal glow"
      },
      hitchhiker: {
        bg: "#0a1022",
        panel: "#0f1a34",
        border: "rgba(120,190,255,0.2)",
        accent: "#7cd7ff",
        muted: "#c5d7f2",
        pattern: "radial-gradient(circle at 20% 30%, rgba(124,215,255,0.1) 0, transparent 40%), radial-gradient(circle at 80% 10%, rgba(200,170,255,0.08) 0, transparent 35%)",
        pill: "Don't panic: galactic gradients"
      },
      unfortunate: {
        bg: "#0c0b0f",
        panel: "#15131c",
        border: "rgba(255,217,140,0.16)",
        accent: "#ffda7a",
        muted: "#e0cfa3",
        pattern: "radial-gradient(circle at 10% 20%, rgba(255,218,122,0.08) 0, transparent 35%), radial-gradient(circle at 70% 0%, rgba(255,218,122,0.05) 0, transparent 40%)",
        pill: "Gothic brass and sepia ink"
      },
      entropy: {
        bg: "#050505",
        panel: "#0f0f14",
        border: "rgba(255,255,255,0.08)",
        accent: "#f97316",
        muted: "#cdd2da",
        pattern: "radial-gradient(circle at 15% 15%, rgba(249,115,22,0.12) 0, transparent 35%), radial-gradient(circle at 75% 5%, rgba(255,255,255,0.06) 0, transparent 35%)",
        pill: "Decay, glow, and noise"
      }
    };
    function applyTheme(name) {
      const t = themes[name] || themes.entropy;
      const root = document.documentElement;
      root.style.setProperty('--bg', t.bg);
      root.style.setProperty('--panel', t.panel);
      root.style.setProperty('--border', t.border);
      root.style.setProperty('--accent', t.accent);
      root.style.setProperty('--muted', t.muted);
      root.style.setProperty('--pattern', t.pattern);
      document.getElementById('pillText').textContent = `${name.charAt(0).toUpperCase()}${name.slice(1)} - ${t.pill}`;
      document.querySelector('.theme-dot').style.background = t.accent;
    }
    async function fetchData() {
      const range = document.getElementById('range').value;
      const limit = document.getElementById('limit').value;
      const heading = document.getElementById('heading');
      const err = document.getElementById('error');
      err.textContent = '';
      try {
        const res = await fetch(`/wrapped/${range}?top_limit=${limit}`);
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        const data = await res.json();
        const user = (data.user && (data.user.display_name || data.user.id)) || "Unknown user";
        heading.textContent = `${user}'s Top ${limit} (${rangeLabels[range]})`;
        render('tracks', data.top_tracks || [], t => ({
          title: t.name,
          subtitle: (t.artists || []).join(', ')
        }));
        render('artists', data.top_artists || [], a => ({
          title: a.name,
          subtitle: (a.genres || []).slice(0,3).join(', ')
        }));
        renderCovers('covers-extended', data.top_tracks || []);
      } catch (e) {
        err.textContent = e.message;
      }
    }
    function renderCovers(containerId, list) {
      const el = document.getElementById(containerId);
      el.innerHTML = '';
      (list || []).filter(t => t.image_url).slice(0, 24).forEach((track, i) => {
        const margin = i === 0 ? '0' : '-16px';
        el.insertAdjacentHTML('beforeend', `
          <div class="cover-bubble" style="margin-left:${margin}">
            <img src="${track.image_url}" alt="${track.name || ''}">
          </div>
        `);
      });
    }
    async function saveCard() {
      const page = document.querySelector('.page');
      const canvas = await html2canvas(page, { useCORS: true, scale: 2 });
      const link = document.createElement('a');
      link.download = 'spotify-rewrapped-themed.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
    function render(containerId, list, mapFn) {
      const el = document.getElementById(containerId);
      el.innerHTML = '';
      (list || []).forEach((item, i) => {
        const mapped = mapFn(item);
        el.insertAdjacentHTML('beforeend', `
          <div class="item">
            <div class="rank">${i+1}</div>
            <div class="title">
              <div>${mapped.title || ''}</div>
              <div class="subtitle">${mapped.subtitle || ''}</div>
            </div>
          </div>
        `);
      });
    }
    document.getElementById('refresh').addEventListener('click', fetchData);
    document.getElementById('theme').addEventListener('change', (e) => applyTheme(e.target.value));
    document.getElementById('save-extended').addEventListener('click', saveCard);
    applyTheme('entropy');
    fetchData();
  </script>
</body>
</html>
"""


MONTHLY_CARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spotify Rewrapped</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #05060d;
      --panel: #0c1220;
      --panel-2: #0f172a;
      --border: rgba(255,255,255,0.08);
      --accent: #f97316;
      --accent-2: #22c55e;
      --muted: #c7d2fe;
      --text: #eef2ff;
      --shadow: 0 24px 60px rgba(0,0,0,0.45);
      --pattern: radial-gradient(circle at 18% 22%, rgba(249,115,22,0.14) 0, transparent 32%), radial-gradient(circle at 82% 10%, rgba(34,197,94,0.12) 0, transparent 34%);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Space Grotesk", "Inter", system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); display: flex; flex-direction: column; align-items: center; }
    .page { width: min(1200px, 96vw); padding: 28px; margin: 32px 0; background: var(--pattern), linear-gradient(135deg, var(--panel), var(--panel-2)); border-radius: 26px; box-shadow: var(--shadow); border: 1px solid var(--border); }
    h1 { margin: 0 0 8px; font-size: 30px; letter-spacing: -0.02em; }
    .muted { color: var(--muted); font-size: 14px; margin: 0 0 12px; }
    .pill { display: inline-flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 999px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); color: var(--muted); }
    .pill .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 6px rgba(249,115,22,0.15); }
    .controls-card { background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: 16px; padding: 14px; margin: 16px 0 22px; display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
    label { color: var(--muted); font-size: 13px; }
    select, button { background: rgba(255,255,255,0.03); color: var(--text); border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; font-size: 14px; }
    option { background: var(--panel); color: var(--text); }
    button { cursor: pointer; transition: transform 0.15s ease, box-shadow 0.15s ease; }
    button:hover { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(0,0,0,0.25); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-top: 14px; }
    .section { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 16px; padding: 14px; }
    .section h3 { margin: 0 0 10px; display: flex; align-items: center; justify-content: space-between; }
    .meta { color: var(--muted); font-size: 13px; }
    .item { display: flex; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06); align-items: center; }
    .item:last-child { border-bottom: none; }
    .rank { width: 32px; text-align: right; color: var(--accent); font-weight: 700; }
    .title { flex: 1; margin-left: 12px; }
    .subtitle { color: var(--muted); font-size: 13px; }
    .badge { font-size: 12px; color: var(--accent-2); }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin: 12px 0 4px; }
    .stat { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 14px; padding: 12px; }
    .stat .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
    .stat .value { font-size: 22px; font-weight: 700; margin-top: 6px; }
    .album-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .album-card { display: flex; gap: 12px; align-items: center; padding: 10px; border: 1px solid var(--border); border-radius: 14px; background: rgba(255,255,255,0.02); }
    .album-cover { width: 64px; height: 64px; border-radius: 10px; overflow: hidden; background: #0b0f1a; border: 1px solid rgba(255,255,255,0.06); }
    .album-cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .error { color: #f87171; margin-top: 12px; }
    .footer-actions { display: flex; justify-content: center; margin: 14px 0 4px; gap: 10px; }
  </style>
</head>
<body>
  <div class="page" id="monthly-card">
    <div class="header">
      <h1>Spotify Rewrapped</h1>
      <p class="muted">Stats built from stored plays in MongoDB: plays, duration, albums, and artists.</p>
      <div class="pill"><span class="dot"></span><span id="period-label">Loading...</span></div>
    </div>
    <div class="controls-card">
      <label>
        View<br>
        <select id="view-type">
          <option value="month" selected>Month</option>
          <option value="year">Year</option>
        </select>
      </label>
      <label>
        Month<br>
        <select id="month" data-field="month"></select>
      </label>
      <label>
        Year<br>
        <select id="year"></select>
      </label>
      <label>
        Top limit<br>
        <select id="limit-monthly">
          <option>10</option>
          <option selected>20</option>
          <option>30</option>
          <option>50</option>
        </select>
      </label>
      <div>
        <button id="refresh-monthly">Refresh</button>
      </div>
    </div>
    <div class="stats">
      <div class="stat"><div class="label">Total plays</div><div class="value" id="stat-plays">0</div></div>
      <div class="stat"><div class="label">Minutes</div><div class="value" id="stat-minutes">0</div></div>
      <div class="stat"><div class="label">Unique tracks</div><div class="value" id="stat-tracks">0</div></div>
      <div class="stat"><div class="label">Unique artists</div><div class="value" id="stat-artists">0</div></div>
      <div class="stat"><div class="label">Unique albums</div><div class="value" id="stat-albums">0</div></div>
      <div class="stat"><div class="label">Active days</div><div class="value" id="stat-days">0</div></div>
    </div>
    <div class="grid">
      <div class="section">
        <h3>Top Tracks <span class="meta" id="period-tracks"></span></h3>
        <div id="tracks-monthly"></div>
      </div>
      <div class="section">
        <h3>Top Artists</h3>
        <div id="artists-monthly"></div>
      </div>
      <div class="section">
        <h3>Top Albums</h3>
        <div id="albums-monthly" class="album-grid"></div>
      </div>
    </div>
    <div id="error-monthly" class="error"></div>
  </div>
  <div class="footer-actions">
    <button id="save-monthly">Save image</button>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
  <script>
    const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];

    function populateSelectors() {
      const monthSel = document.getElementById('month');
      const yearSel = document.getElementById('year');
      monthSel.innerHTML = '';
      yearSel.innerHTML = '';
      monthNames.forEach((name, idx) => {
        const opt = document.createElement('option');
        opt.value = idx + 1;
        opt.textContent = name;
        monthSel.appendChild(opt);
      });
      const currentYear = new Date().getFullYear();
      for (let y = currentYear; y >= currentYear - 5; y--) {
        const opt = document.createElement('option');
        opt.value = y;
        opt.textContent = y;
        yearSel.appendChild(opt);
      }
      const anchor = new Date();
      anchor.setDate(1);
      anchor.setMonth(anchor.getMonth() - 1);
      monthSel.value = anchor.getMonth() + 1;
      yearSel.value = anchor.getFullYear();
    }

    async function fetchPeriod() {
      const view = document.getElementById('view-type').value;
      const month = document.getElementById('month').value;
      const year = document.getElementById('year').value;
      const limit = document.getElementById('limit-monthly').value;
      const err = document.getElementById('error-monthly');
      err.textContent = '';
      try {
        const url = view === 'year'
          ? `/wrapped/yearly?year=${year}&limit=${limit}`
          : `/wrapped/monthly?month=${month}&year=${year}&limit=${limit}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        const data = await res.json();
        const label = view === 'year' ? `${year}` : `${monthNames[month - 1]} ${year}`;
        document.getElementById('period-label').textContent = `Showing ${view === 'year' ? 'Year' : ''} ${label}`;
        document.getElementById('period-tracks').textContent = label;
        renderStats(data);
        renderList('tracks-monthly', data.top_tracks || [], (t, i) => `
          <div class=item>
            <div class=rank>${i+1}</div>
            <div class=title>
              <div>${t.name || ''}</div>
              <div class=subtitle>${(t.artists || []).join(', ')}</div>
            </div>
            <div class="badge">${t.play_count || 0} plays &middot; ${t.minutes || 0} min</div>
          </div>
        `);
        renderList('artists-monthly', data.top_artists || [], (a, i) => `
          <div class=item>
            <div class=rank>${i+1}</div>
            <div class=title>
              <div>${a.name || ''}</div>
              <div class=subtitle>${a.play_count || 0} plays &middot; ${a.minutes || 0} min</div>
            </div>
          </div>
        `);
        renderAlbums(data.top_albums || []);
      } catch (e) {
        err.textContent = e.message;
      }
    }
    function renderStats(data) {
      document.getElementById('stat-plays').textContent = data.play_count || 0;
      document.getElementById('stat-minutes').textContent = data.total_minutes || 0;
      document.getElementById('stat-tracks').textContent = data.unique_tracks || 0;
      document.getElementById('stat-artists').textContent = data.unique_artists || 0;
      document.getElementById('stat-albums').textContent = data.unique_albums || 0;
      document.getElementById('stat-days').textContent = data.days_active || 0;
    }

    function renderList(containerId, list, templateFn) {
      const el = document.getElementById(containerId);
      el.innerHTML = '';
      list.forEach((item, idx) => {
        el.insertAdjacentHTML('beforeend', templateFn(item, idx));
      });
    }

    function renderAlbums(albums) {
      const el = document.getElementById('albums-monthly');
      el.innerHTML = '';
      albums.forEach((album, i) => {
        el.insertAdjacentHTML('beforeend', `
          <div class="album-card">
            <div class="album-cover">${album.image_url ? `<img src="${album.image_url}" alt="${album.name || ''}">` : ''}</div>
            <div>
              <div>${i+1}. ${album.name || ''}</div>
              <div class="subtitle">${(album.artists || []).join(', ')}</div>
              <div class="badge">${album.play_count || 0} plays &middot; ${album.minutes || 0} min</div>
            </div>
          </div>
        `);
      });
    }

    async function saveCard() {
      const page = document.getElementById('monthly-card');
      const canvas = await html2canvas(page, { useCORS: true, scale: 2 });
      const link = document.createElement('a');
      link.download = 'period-rewrapped.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
    }

    function toggleViewState() {
      const view = document.getElementById('view-type').value;
      const monthLabel = document.querySelector('select[data-field=\"month\"]').parentElement;
      monthLabel.style.display = view === 'month' ? 'block' : 'none';
    }

    document.getElementById('refresh-monthly').addEventListener('click', fetchPeriod);
    document.getElementById('save-monthly').addEventListener('click', saveCard);
    document.getElementById('view-type').addEventListener('change', () => {
      toggleViewState();
      fetchPeriod();
    });
    populateSelectors();
    toggleViewState();
    fetchPeriod();
  </script>
</body>
</html>
"""


@router.get("", response_class=HTMLResponse)
async def card() -> HTMLResponse:
    return HTMLResponse(content=CARD_HTML)


@router.get("/extended", response_class=HTMLResponse)
async def extended_card() -> HTMLResponse:
    return HTMLResponse(content=EXTENDED_CARD_HTML)


@router.get("/rewrapped", response_class=HTMLResponse)
async def monthly_card() -> HTMLResponse:
    return HTMLResponse(content=MONTHLY_CARD_HTML)
