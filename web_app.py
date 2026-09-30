# -*- coding: utf-8 -*-
"""
ONYX CINEMA v12.5 - Flask + Discord Bot + TMDB + Multi Sources
Complete single-file version with embedded HTML
"""

from flask import Flask, jsonify, request, render_template_string
import os
import time
import json
import urllib.request
import urllib.parse
import threading
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "a6288fc42fb7de2837e2756a101397e5")
SECRET_SALT = os.getenv("SECRET_SALT", "onyx_cinema_2026_secret")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
RUN_BOT = os.getenv("RUN_BOT", "true").lower() == "true"

# =========================================================
# SECURITY
# =========================================================
_rate = defaultdict(list)
_banned = {}
_log = defaultdict(int)

def get_ip():
    for h in ("CF-Connecting-IP", "X-Forwarded-For", "X-Real-IP"):
        if request.headers.get(h):
            return request.headers.get(h).split(",")[0].strip()
    return request.remote_addr or "unknown"

@app.before_request
def gate():
    # تجاهل الـ API من Rate limit للسماح للـ Activity
    if request.path.startswith("/api/") or request.path in ("/health",):
        return
    ip = get_ip()
    if ip in _banned and time.time() < _banned[ip]:
        return jsonify({"error": "banned"}), 429
    now = time.time()
    _rate[ip] = [t for t in _rate[ip] if now - t < 60]
    _rate[ip].append(now)
    _log[ip] += 1
    if _log[ip] > 5000:
        _banned[ip] = now + 1800
        return jsonify({"error": "rate limit"}), 429
    if len(_rate[ip]) > 500:
        return jsonify({"error": "rate limit"}), 429

@app.after_request
def sec(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-XSS-Protection"] = "1; mode=block"
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # السماح بالـ iframe من Activity
    r.headers.pop("X-Frame-Options", None)
    r.headers["Content-Security-Policy"] = "frame-ancestors 'self' https://*.discord.com https://discord.com"
    return r

# =========================================================
# SOURCES
# =========================================================
REAL_SOURCES = [
    ("VidLink", "https://vidlink.pro/movie/{id}", "https://vidlink.pro/tv/{id}/{s}/{e}"),
    ("Videasy", "https://player.videasy.net/movie/{id}", "https://player.videasy.net/tv/{id}/{s}/{e}"),
    ("AutoEmbed", "https://player.autoembed.cc/embed/movie/{id}", "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}"),
    ("SmashyStream", "https://player.smashy.stream/movie/{id}", "https://player.smashy.stream/tv/{id}?s={s}&e={e}"),
    ("VidSrc XYZ", "https://vidsrc.xyz/embed/movie?tmdb={id}", "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrc ME", "https://vidsrc.me/embed/movie?tmdb={id}", "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrc CC", "https://vidsrc.cc/v2/embed/movie/{id}", "https://vidsrc.cc/v2/embed/tv/{id}/{s}/{e}"),
    ("2Embed", "https://www.2embed.to/embed/tmdb/movie?id={id}", "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("Embed SU", "https://embed.su/embed/movie/{id}", "https://embed.su/embed/tv/{id}/{s}/{e}"),
    ("MultiEmbed", "https://multiembed.mov/?video_id={id}&tmdb=1", "https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("VidPlus", "https://vidplus.to/embed/movie/{id}", "https://vidplus.to/embed/tv/{id}/{s}/{e}"),
    ("VidCloud", "https://vidcloud.stream/movie/{id}", "https://vidcloud.stream/tv/{id}/{s}/{e}"),
    ("VidPlay", "https://vidplay.site/movie/{id}", "https://vidplay.site/tv/{id}/{s}/{e}"),
    ("VidFast", "https://vidfast.pro/movie/{id}", "https://vidfast.pro/tv/{id}/{s}/{e}"),
    ("VidEasy", "https://videasy.net/movie/{id}", "https://videasy.net/tv/{id}/{s}/{e}"),
]

QUALITY_VARIANTS = ["4K", "HD", "SD"]
QUALITY_SUFFIX = {
    "4K": "?quality=4k",
    "HD": "?quality=hd",
    "SD": "?quality=sd",
}

def build_sources():
    sources = []
    for name, movie_url, tv_url in REAL_SOURCES:
        for q in QUALITY_VARIANTS:
            suffix = QUALITY_SUFFIX[q]
            m = movie_url + ("&" + suffix[1:] if "?" in movie_url else suffix)
            t = tv_url + ("&" + suffix[1:] if "?" in tv_url else suffix)
            sources.append({"name": name + " " + q, "q": q, "movie": m, "tv": t})
    return sources

PLAYER_SOURCES = build_sources()
SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)

SPORTS_SOURCES = [
    {"name": "YallaShoot 4K", "q": "4K", "movie": "https://yallashoot.com/embed/{id}", "tv": "https://yallashoot.com/embed/{id}"},
    {"name": "KoraLive HD", "q": "HD", "movie": "https://koralive.com/embed/{id}", "tv": "https://koralive.com/embed/{id}"},
    {"name": "BeinSport HD", "q": "HD", "movie": "https://beinsport.com/embed/{id}", "tv": "https://beinsport.com/embed/{id}"},
    {"name": "HesGoal HD", "q": "HD", "movie": "https://hesgoal.com/embed/{id}", "tv": "https://hesgoal.com/embed/{id}"},
]
MATCH_SOURCES_JSON = json.dumps(SPORTS_SOURCES, ensure_ascii=False)


# =========================================================
# TMDB HELPER
# =========================================================
def tmdb(ep, params=None):
    if not TMDB_API_KEY:
        return {"error": "no key", "results": []}
    p = params or {}
    p["api_key"] = TMDB_API_KEY
    p["language"] = "ar"
    url = f"{TMDB_BASE}{ep}?{urllib.parse.urlencode(p)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/12.5"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


# =========================================================
# FOOTBALL DATA
# =========================================================
FOOTBALL_LEAGUES = [
    {"id": "saudi", "name": "الدوري السعودي"},
    {"id": "egypt", "name": "الدوري المصري"},
    {"id": "spain", "name": "الدوري الإسباني"},
    {"id": "england", "name": "الدوري الإنجليزي"},
    {"id": "italy", "name": "الدوري الإيطالي"},
    {"id": "germany", "name": "الدوري الألماني"},
    {"id": "france", "name": "الدوري الفرنسي"},
    {"id": "ucl", "name": "دوري أبطال أوروبا"},
]


def get_matches(league=None, date=None):
    today = datetime.now().strftime("%Y-%m-%d")
    date = date or today
    base_matches = [
        {"league": "الدوري السعودي", "league_id": "saudi", "team1": "النصر", "team2": "الهلال",
         "s1": "2", "s2": "1", "status": "live", "ch": "SSC", "date": today, "time": "21:00",
         "quality": "4K", "stream_id": "saudi_1"},
        {"league": "الدوري المصري", "league_id": "egypt", "team1": "الأهلي", "team2": "الزمالك",
         "s1": "-", "s2": "-", "status": "upcoming", "ch": "ON TV", "date": today, "time": "19:00",
         "quality": "HD", "stream_id": "egypt_1"},
        {"league": "الدوري الإسباني", "league_id": "spain", "team1": "ريال مدريد", "team2": "برشلونة",
         "s1": "3", "s2": "2", "status": "finished", "ch": "beIN", "date": today, "time": "22:00",
         "quality": "4K", "stream_id": "spain_1"},
        {"league": "دوري أبطال أوروبا", "league_id": "ucl", "team1": "مان سيتي", "team2": "ريال مدريد",
         "s1": "1", "s2": "1", "status": "live", "ch": "beIN", "date": today, "time": "22:00",
         "quality": "4K", "stream_id": "ucl_1"},
        {"league": "الدوري الإنجليزي", "league_id": "england", "team1": "ليفربول", "team2": "أرسنال",
         "s1": "-", "s2": "-", "status": "upcoming", "ch": "beIN", "date": today, "time": "20:30",
         "quality": "HD", "stream_id": "england_1"},
        {"league": "الدوري الإيطالي", "league_id": "italy", "team1": "إنتر", "team2": "ميلان",
         "s1": "2", "s2": "0", "status": "finished", "ch": "beIN", "date": today, "time": "21:45",
         "quality": "4K", "stream_id": "italy_1"},
    ]
    if league:
        return [m for m in base_matches if m["league_id"] == league]
    return base_matches


# =========================================================
# HTML - PLAYER (Discord Activity)
# =========================================================
PLAYER_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>ONYX CINEMA</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--surface:#16161f;--surface2:#1f1f2e;--accent:#e8b84b;--text:#e8e8f0;--text2:#a0a0b8;--border:rgba(255,255,255,0.08)}
html,body{width:100%;height:100%;background:var(--bg);color:var(--text);font-family:Arial,sans-serif;overflow-x:hidden}
body{display:flex;flex-direction:column;min-height:100vh}
#header{padding:14px 18px;background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;position:sticky;top:0;z-index:100}
#logo{font-size:1.5rem;color:var(--accent);letter-spacing:3px;font-weight:900}
#search-box{flex:1;max-width:500px;display:flex;gap:8px;min-width:200px}
#search-input{flex:1;padding:10px 16px;background:var(--surface2);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:0.95rem;outline:none;font-family:inherit}
#search-input:focus{border-color:var(--accent)}
#search-btn{padding:10px 20px;background:var(--accent);color:#000;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-family:inherit}
#tabs{display:flex;gap:8px;padding:12px 18px;background:var(--surface);border-bottom:1px solid var(--border);overflow-x:auto;scrollbar-width:none}
#tabs::-webkit-scrollbar{display:none}
.tab{padding:8px 18px;background:var(--surface2);color:var(--text2);border:1px solid var(--border);border-radius:8px;font-size:0.85rem;font-weight:600;cursor:pointer;white-space:nowrap;font-family:inherit}
.tab:hover{border-color:var(--accent);color:var(--accent)}
.tab.active{background:var(--accent);color:#000;border-color:var(--accent)}
#content{flex:1;overflow-y:auto;padding:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:16px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;cursor:pointer;transition:0.2s}
.card:hover{transform:translateY(-4px);border-color:var(--accent)}
.card-poster{width:100%;aspect-ratio:2/3;object-fit:cover;background:var(--surface2);display:block}
.card-info{padding:10px}
.card-title{font-size:0.8rem;font-weight:700;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.3;min-height:2.1em}
.card-meta{font-size:0.7rem;color:var(--text2);display:flex;justify-content:space-between}
.card-rating{color:var(--accent);font-weight:700}
#detail{display:none;padding:18px;flex-direction:column;gap:18px}
#detail.active{display:flex}
.back-btn{padding:8px 18px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:0.85rem;font-family:inherit;align-self:flex-start}
.detail-header{display:flex;gap:20px;flex-wrap:wrap}
.detail-poster{width:200px;aspect-ratio:2/3;border-radius:12px;object-fit:cover;background:var(--surface2);flex-shrink:0}
.detail-info{flex:1;min-width:220px}
.detail-title{font-size:1.6rem;font-weight:900;margin-bottom:10px}
.detail-meta{display:flex;gap:12px;flex-wrap:wrap;font-size:0.85rem;color:var(--text2);margin-bottom:14px}
.detail-meta .accent{color:var(--accent);font-weight:700}
.detail-desc{font-size:0.9rem;color:#a8a8c4;line-height:1.8;margin-bottom:16px}
.detail-actions{display:flex;gap:10px;flex-wrap:wrap}
.btn-primary{padding:12px 28px;background:var(--accent);color:#000;border:none;border-radius:8px;font-weight:700;cursor:pointer;font-size:0.92rem;font-family:inherit}
.btn-ghost{padding:12px 24px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:8px;font-weight:600;cursor:pointer;font-family:inherit}
#player-wrap{width:100%;aspect-ratio:16/9;background:#000;border-radius:12px;overflow:hidden;display:none}
#player-wrap.active{display:block}
#player-frame{width:100%;height:100%;border:none}
.episodes-section{margin-top:20px;display:none}
.episodes-section.active{display:block}
.seasons-row{display:flex;gap:8px;overflow-x:auto;margin-bottom:14px;padding-bottom:8px}
.season-btn{padding:8px 16px;background:var(--surface2);color:var(--text2);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:0.8rem;font-family:inherit;white-space:nowrap}
.season-btn.active{background:var(--accent);color:#000;border-color:var(--accent)}
.episodes-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:8px}
.ep-btn{padding:12px 6px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:0.85rem;font-weight:700;font-family:inherit}
.ep-btn:hover{border-color:var(--accent);color:var(--accent)}
.loading{text-align:center;padding:60px 20px;color:var(--text2);grid-column:1/-1}
.spinner{width:40px;height:40px;border:3px solid var(--surface2);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
#toast{position:fixed;bottom:30px;left:50%;transform:translateX(-50%) translateY(80px);padding:12px 24px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:10px;font-size:0.85rem;font-weight:600;z-index:9999;transition:0.3s;opacity:0}
#toast.show{transform:translateX(-50%) translateY(0);opacity:1}
@media(max-width:600px){
  .grid{grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:12px}
  .detail-poster{width:140px}
  .detail-title{font-size:1.3rem}
}
</style>
</head>
<body>

<div id="header">
  <div id="logo">ONYX CINEMA</div>
  <div id="search-box">
    <input id="search-input" type="text" placeholder="ابحث عن فيلم أو مسلسل..." />
    <button id="search-btn" onclick="doSearch()">بحث</button>
  </div>
</div>

<div id="tabs">
  <button class="tab active" onclick="loadCategory('trending', this)">رائج</button>
  <button class="tab" onclick="loadCategory('popular', this)">شائع</button>
  <button class="tab" onclick="loadCategory('top_rated', this)">الأعلى</button>
  <button class="tab" onclick="loadCategory('now_playing', this)">في السينما</button>
  <button class="tab" onclick="loadCategory('upcoming', this)">قادم</button>
  <button class="tab" onclick="loadCategory('tv_popular', this)">مسلسلات</button>
</div>

<div id="content">
  <div class="grid" id="movies-grid">
    <div class="loading"><div class="spinner"></div>جار التحميل...</div>
  </div>
</div>

<div id="detail">
  <button class="back-btn" onclick="showGrid()">← رجوع</button>
  <div class="detail-header">
    <img class="detail-poster" id="d-poster" src="" alt="" />
    <div class="detail-info">
      <h1 class="detail-title" id="d-title">-</h1>
      <div class="detail-meta" id="d-meta"></div>
      <p class="detail-desc" id="d-desc"></p>
      <div class="detail-actions">
        <button class="btn-primary" onclick="playContent()">▶ مشاهدة الآن</button>
        <button class="btn-ghost" onclick="addFav()">❤ المفضلة</button>
      </div>
    </div>
  </div>
  <div id="player-wrap">
    <iframe id="player-frame" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerpolicy="origin"></iframe>
  </div>
  <div class="episodes-section" id="episodes-section">
    <div class="seasons-row" id="seasons-row"></div>
    <div class="episodes-grid" id="episodes-grid"></div>
  </div>
</div>

<div id="toast"></div>

<script>
const IMG_BASE = 'https://image.tmdb.org/t/p/w500';
let currentContent = null;
let currentList = [];

async function api(path) {
  try {
    const r = await fetch(path);
    return await r.json();
  } catch (e) {
    console.error(e);
    return { results: [] };
  }
}

async function loadCategory(type, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');
  showGrid();
  const grid = document.getElementById('movies-grid');
  grid.innerHTML = '<div class="loading"><div class="spinner"></div>جار التحميل...</div>';
  let url = '/api/trending';
  if (type === 'popular') url = '/api/popular/movie';
  else if (type === 'top_rated') url = '/api/top_rated/movie';
  else if (type === 'now_playing') url = '/api/now_playing';
  else if (type === 'upcoming') url = '/api/upcoming';
  else if (type === 'tv_popular') url = '/api/popular/tv';
  const data = await api(url);
  const results = data.results || [];
  currentList = results;
  if (!results.length) {
    grid.innerHTML = '<div class="loading">لا توجد نتائج</div>';
    return;
  }
  renderGrid(results);
}

function renderGrid(results) {
  const grid = document.getElementById('movies-grid');
  grid.innerHTML = results.slice(0, 20).map((m, i) => {
    const title = m.title || m.name || '?';
    const year = (m.release_date || m.first_air_date || '').substring(0, 4);
    const rating = m.vote_average ? m.vote_average.toFixed(1) : 'N/A';
    const poster = m.poster_path ? IMG_BASE + m.poster_path : '';
    return '<div class="card" onclick="openDetail(' + i + ')">' +
      (poster ? '<img class="card-poster" src="' + poster + '" loading="lazy" alt="" />' :
        '<div class="card-poster" style="display:flex;align-items:center;justify-content:center;color:var(--text2)">لا صورة</div>') +
      '<div class="card-info"><div class="card-title">' + title + '</div>' +
      '<div class="card-meta"><span>' + year + '</span><span class="card-rating">★ ' + rating + '</span></div>' +
      '</div></div>';
  }).join('');
}

async function doSearch() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) return;
  showGrid();
  const grid = document.getElementById('movies-grid');
  grid.innerHTML = '<div class="loading"><div class="spinner"></div>جار البحث...</div>';
  const data = await api('/api/search?q=' + encodeURIComponent(q));
  const results = data.results || [];
  currentList = results;
  if (!results.length) {
    grid.innerHTML = '<div class="loading">لا توجد نتائج</div>';
    return;
  }
  renderGrid(results);
}

document.getElementById('search-input').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') doSearch();
});

async function openDetail(idx) {
  const item = currentList[idx];
  if (!item) return;
  const mtype = item.media_type || (item.name ? 'tv' : 'movie');
  currentContent = { id: item.id, type: mtype, title: item.title || item.name };
  document.getElementById('content').style.display = 'none';
  document.getElementById('detail').classList.add('active');
  document.getElementById('player-wrap').classList.remove('active');
  document.getElementById('episodes-section').classList.remove('active');
  const title = item.title || item.name || '?';
  const year = (item.release_date || item.first_air_date || '').substring(0, 4);
  const rating = item.vote_average ? item.vote_average.toFixed(1) : 'N/A';
  const poster = item.poster_path ? IMG_BASE + item.poster_path : '';
  const desc = item.overview || 'لا يوجد وصف متاح';
  document.getElementById('d-poster').src = poster;
  document.getElementById('d-title').textContent = title;
  document.getElementById('d-meta').innerHTML =
    '<span class="accent">★ ' + rating + '</span>' +
    '<span>' + year + '</span>' +
    '<span>' + (mtype === 'tv' ? 'مسلسل' : 'فيلم') + '</span>';
  document.getElementById('d-desc').textContent = desc;
  if (mtype === 'tv') await loadSeasons(item.id);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadSeasons(tvId) {
  const data = await api('/api/tv/' + tvId);
  const seasons = (data.seasons || []).filter(s => s.season_number > 0);
  if (!seasons.length) return;
  const section = document.getElementById('episodes-section');
  const row = document.getElementById('seasons-row');
  section.classList.add('active');
  row.innerHTML = seasons.map((s, i) =>
    '<button class="season-btn' + (i === 0 ? ' active' : '') + '" onclick="loadEpisodes(' + tvId + ',' + s.season_number + ', this)">' +
    (s.name || 'الموسم ' + s.season_number) + '</button>').join('');
  if (seasons[0]) loadEpisodes(tvId, seasons[0].season_number);
}

async function loadEpisodes(tvId, seasonNum, btn) {
  if (btn) {
    document.querySelectorAll('.season-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }
  const grid = document.getElementById('episodes-grid');
  grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  const data = await api('/api/tv/' + tvId + '/season/' + seasonNum);
  const episodes = data.episodes || [];
  if (!episodes.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text2);padding:20px">لا توجد حلقات</div>';
    return;
  }
  grid.innerHTML = episodes.map(e =>
    '<button class="ep-btn" onclick="playEpisode(' + tvId + ',' + seasonNum + ',' + e.episode_number + ')">' +
    'حلقة ' + e.episode_number + '</button>').join('');
}

function playContent() {
  if (!currentContent) return;
  const { id, type } = currentContent;
  let url = type === 'tv' ? 'https://vidlink.pro/tv/' + id + '/1/1' : 'https://vidlink.pro/movie/' + id;
  const wrap = document.getElementById('player-wrap');
  const frame = document.getElementById('player-frame');
  frame.src = url;
  wrap.classList.add('active');
  showToast('▶ جاري التشغيل بجودة 4K');
  wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function playEpisode(tvId, seasonNum, epNum) {
  const url = 'https://vidlink.pro/tv/' + tvId + '/' + seasonNum + '/' + epNum;
  const wrap = document.getElementById('player-wrap');
  const frame = document.getElementById('player-frame');
  frame.src = url;
  wrap.classList.add('active');
  showToast('▶ الموسم ' + seasonNum + ' - الحلقة ' + epNum);
  wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showGrid() {
  document.getElementById('detail').classList.remove('active');
  document.getElementById('content').style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function addFav() {
  if (!currentContent) return;
  const favs = JSON.parse(localStorage.getItem('onyx_favs') || '[]');
  if (!favs.includes(currentContent.id)) {
    favs.push(currentContent.id);
    localStorage.setItem('onyx_favs', JSON.stringify(favs));
    showToast('❤ أضيف للمفضلة');
  } else {
    showToast('موجود في المفضلة');
  }
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2500);
}

window.addEventListener('DOMContentLoaded', () => {
  console.log('[ONYX] Loaded');
  loadCategory('trending', document.querySelector('.tab.active'));
});
</script>
</body>
</html>
"""


# =========================================================
# HTML - INDEX (full site)
# =========================================================
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ONYX CINEMA</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--surface:#16161f;--surface2:#1f1f2e;--accent:#e8b84b;--text:#e8e8f0;--text2:#a0a0b8;--border:rgba(255,255,255,0.08)}
body{background:var(--bg);color:var(--text);font-family:Arial,sans-serif;padding:40px}
h1{color:var(--accent);text-align:center;margin-bottom:20px;letter-spacing:3px}
p{text-align:center;color:var(--text2);margin-bottom:30px}
.links{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
a{padding:14px 28px;background:var(--surface2);color:var(--text);text-decoration:none;border-radius:10px;border:1px solid var(--border);font-weight:700;transition:0.2s}
a:hover{background:var(--accent);color:#000}
</style>
</head>
<body>
<h1>ONYX CINEMA</h1>
<p>اختر الوجهة</p>
<div class="links">
  <a href="/player">صفحة المشاهدة</a>
  <a href="/match">المباريات</a>
  <a href="/api/trending">API الرائج</a>
  <a href="/health">حالة الخدمة</a>
</div>
</body>
</html>
"""


# =========================================================
# HTML - MATCH PLAYER
# =========================================================
MATCH_PLAYER_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ONYX Sports</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;overflow:hidden;font-family:Arial,sans-serif}
#wrap{position:relative;width:100vw;height:100vh;background:#000}
iframe{position:absolute;top:52px;left:0;width:100%;height:calc(100% - 52px);border:none;background:#000}
#topbar{position:absolute;top:0;left:0;right:0;height:52px;background:linear-gradient(180deg,rgba(10,10,15,.98),rgba(10,10,15,.85));color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 18px;z-index:20;border-bottom:1px solid rgba(255,255,255,.08)}
#topbar .info{font-size:14px;font-weight:700;color:#e8b84b}
#topbar .btns{display:flex;gap:6px;flex-wrap:wrap}
#topbar button{background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.12);padding:7px 13px;border-radius:6px;cursor:pointer;font-size:11px;font-weight:700;font-family:inherit}
#topbar button:hover{background:#e8b84b;color:#000}
#topbar button.active{background:#e8b84b;color:#000}
#loading{position:absolute;inset:52px 0 0 0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:18px;background:linear-gradient(135deg,#0a0a15,#1a1a2e);color:#a0a0b8;z-index:15}
#loading.hide{opacity:0;pointer-events:none}
.spinner{width:54px;height:54px;border:4px solid rgba(232,184,75,.15);border-top-color:#e8b84b;border-radius:50%;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div id="wrap">
  <div id="topbar">
    <div class="info" id="match-info">ONYX SPORTS - بث مباشر</div>
    <div class="btns" id="servers"></div>
  </div>
  <div id="loading">
    <div class="spinner"></div>
    <div style="font-size:14px;font-weight:600">جار تحميل البث المباشر...</div>
  </div>
  <iframe id="player" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerpolicy="origin"></iframe>
</div>
<script>
const SOURCES = __SOURCES__;
const p = new URLSearchParams(location.search);
const id = p.get('id') || 'match_1';
const team1 = p.get('team1') || '';
const team2 = p.get('team2') || '';
let currentIdx = 0;

if (team1 && team2) {
  document.getElementById('match-info').textContent = team1 + ' ضد ' + team2;
}

function buildServers() {
  const box = document.getElementById('servers');
  box.innerHTML = '';
  SOURCES.forEach((s, i) => {
    const b = document.createElement('button');
    b.textContent = s.name;
    b.onclick = () => loadMatchSource(i);
    box.appendChild(b);
  });
}

function loadMatchSource(idx) {
  currentIdx = idx;
  const src = SOURCES[idx];
  const url = (src.movie || src.tv).replace(/{id}/g, id);
  document.getElementById('player').src = url;
  document.querySelectorAll('#servers button').forEach((b, i) => b.classList.toggle('active', i === idx));
  document.getElementById('loading').classList.remove('hide');
}

document.getElementById('player').onload = () => {
  setTimeout(() => document.getElementById('loading').classList.add('hide'), 800);
};

buildServers();
loadMatchSource(0);
</script>
</body>
</html>
"""


# =========================================================
# ROUTES
# =========================================================
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/player")
def player():
    return render_template_string(PLAYER_HTML)

@app.route("/match")
def match_player():
    return render_template_string(MATCH_PLAYER_HTML.replace("__SOURCES__", MATCH_SOURCES_JSON))

@app.route("/api/trending")
def api_trending():
    return jsonify(tmdb("/trending/all/week"))

@app.route("/api/popular/<mt>")
def api_popular(mt):
    if mt not in ("movie", "tv"):
        return jsonify({"error": "invalid"}), 400
    return jsonify(tmdb(f"/{mt}/popular"))

@app.route("/api/top_rated/<mt>")
def api_top_rated(mt):
    if mt not in ("movie", "tv"):
        return jsonify({"error": "invalid"}), 400
    return jsonify(tmdb(f"/{mt}/top_rated"))

@app.route("/api/now_playing")
def api_now_playing():
    return jsonify(tmdb("/movie/now_playing"))

@app.route("/api/upcoming")
def api_upcoming():
    return jsonify(tmdb("/movie/upcoming"))

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()[:100]
    if not q:
        return jsonify({"results": []})
    return jsonify(tmdb("/search/multi", {"query": q}))

@app.route("/api/movie/<int:mid>")
def api_movie(mid):
    return jsonify(tmdb(f"/movie/{mid}", {"append_to_response": "credits,videos,similar,images,recommendations"}))

@app.route("/api/tv/<int:tid>")
def api_tv(tid):
    return jsonify(tmdb(f"/tv/{tid}", {"append_to_response": "credits,videos,similar,images,recommendations"}))

@app.route("/api/tv/<int:tid>/season/<int:s>")
def api_tv_season(tid, s):
    return jsonify(tmdb(f"/tv/{tid}/season/{s}"))

@app.route("/api/person/<int:pid>")
def api_person(pid):
    return jsonify(tmdb(f"/person/{pid}", {"append_to_response": "combined_credits,images,external_ids"}))

@app.route("/api/matches")
def api_matches():
    league = request.args.get("league")
    date = request.args.get("date")
    matches = get_matches(league, date)
    return jsonify({"matches": matches, "count": len(matches), "league": league or "all"})

@app.route("/api/leagues")
def api_leagues():
    return jsonify({"leagues": FOOTBALL_LEAGUES})

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ONYX CINEMA v12.5",
        "tmdb": "ok" if TMDB_API_KEY else "missing",
        "sources": len(PLAYER_SOURCES),
        "match_sources": len(SPORTS_SOURCES),
    })


# =========================================================
# DISCORD BOT (background)
# =========================================================
_bot_started = False

def start_discord_bot():
    global _bot_started
    if _bot_started:
        return
    _bot_started = True
    try:
        print("[ONYX] Starting Discord bot...")
        subprocess.Popen([sys.executable, "bot.py"])
    except Exception as e:
        print(f"[ONYX] Bot failed: {e}")

if RUN_BOT and os.getenv("WERKZEUG_RUN_MAIN") != "true":
    _bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
    _bot_thread.start()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
