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
    <h2 id="heading" style="margin: 0 0 12px;">Top 10 - multi-year</h2>
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
        heading.textContent = `${user}'s Top ${limit} — ${rangeLabels[range]}`;
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
  <title>Spotify Rewrapped — Themes</title>
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
    <h2 id="heading" style="margin: 0 0 12px;">Top 10 - multi-year</h2>
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
        heading.textContent = `${user}'s Top ${limit} — ${rangeLabels[range]}`;
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


@router.get("", response_class=HTMLResponse)
async def card() -> HTMLResponse:
    return HTMLResponse(content=CARD_HTML)


@router.get("/extended", response_class=HTMLResponse)
async def extended_card() -> HTMLResponse:
    return HTMLResponse(content=EXTENDED_CARD_HTML)
