# -*- coding: utf-8 -*-
"""
ONYX CINEMA — Ultimate Single File (Flask + Cinematic UI + Multi-Audio 4K Player)
"""

from flask import Flask, jsonify, request
import os
import time
import json
import urllib.request
import urllib.parse
from collections import defaultdict

app = Flask(__name__)

# جلب المفتاح تلقائياً من متغيرات البيئة (.env)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"

# ══════════════════════════════════════════════════════════
# SECURITY & RATE LIMITING
# ══════════════════════════════════════════════════════════
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
    ip = get_ip()
    if ip in _banned and time.time() < _banned[ip]:
        return jsonify({"error": "banned"}), 429
    now = time.time()
    _rate[ip] = [t for t in _rate[ip] if now - t < 60]
    _rate[ip].append(now)
    _log[ip] += 1
    if _log[ip] > 500:
        _banned[ip] = now + 1800
        return jsonify({"error": "rate limit"}), 429
    if len(_rate[ip]) > 120:
        return jsonify({"error": "rate limit"}), 429

@app.after_request
def sec(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "SAMEORIGIN"
    r.headers["X-XSS-Protection"] = "1; mode=block"
    return r

# ══════════════════════════════════════════════════════════
# PLAYER SOURCE — مصدر 4K واحد يدعم تعدد الأصوات واللغات
# ══════════════════════════════════════════════════════════
PLAYER_SOURCES = [
    {
        "name": "VidLink 4K Multi-Audio", 
        "q": "4K", 
        "ads": "none",
        "movie": "https://vidlink.pro/movie/{id}?primaryColor=e50914&autoplay=true&multiLang=true&audio=en", 
        "tv": "https://vidlink.pro/tv/{id}/{s}/{e}?primaryColor=e50914&autoplay=true&multiLang=true&audio=en"
    }
]
SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)

# ══════════════════════════════════════════════════════════
# TMDB HELPER
# ══════════════════════════════════════════════════════════
def tmdb(ep, params=None):
    if not TMDB_API_KEY:
        return {"error": "no key", "results": []}
    p = params or {}
    p["api_key"] = TMDB_API_KEY
    
    lang = request.args.get("lang", "ar")
    p["language"] = "en-US" if lang == "en" else "ar"
    
    url = f"{TMDB_BASE}{ep}?{urllib.parse.urlencode(p)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/3.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}

# ══════════════════════════════════════════════════════════
# FRONTEND HTML
# ══════════════════════════════════════════════════════════
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>ONYX MOVIE – أفضل تجربة سينمائية</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800;900&family=Bebas+Neue&display=swap" rel="stylesheet" />
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #060911; --bg2: #0b0f19; --bg3: #111726;
  --surface: rgba(22, 29, 48, 0.7); --surface-hover: rgba(30, 39, 64, 0.9);
  --accent: #e50914; --accent-glow: rgba(229, 9, 20, 0.4); --accent2: #ff3b45; 
  --gold: #f5c518; --blue: #0077ff;
  --text: #ffffff; --text2: #a0aabf; --text3: #5a6480;
  --border: rgba(255, 255, 255, 0.08);
  --border-glow: rgba(229, 9, 20, 0.3);
  --radius: 14px; --radius-lg: 24px;
  --transition: 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
  --font: 'Cairo', sans-serif;
}

html { scroll-behavior: smooth; font-size: 16px; }
body { 
  background: var(--bg); 
  color: var(--text); 
  font-family: var(--font); 
  direction: rtl; 
  overflow-x: hidden; 
  cursor: default; 
}
a { text-decoration: none; color: inherit; }
ul { list-style: none; }
img { max-width: 100%; display: block; }
button { cursor: pointer; font-family: var(--font); border: none; outline: none; }
input, select, textarea { font-family: var(--font); outline: none; }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: #1e2740; border-radius: 4px; border: 2px solid var(--bg); }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
::selection { background: var(--accent); color: #fff; }

/* CURSOR */
#cursor {
  position: fixed; width: 12px; height: 12px;
  background: var(--accent); border-radius: 50%;
  pointer-events: none; z-index: 9999;
  transform: translate(-50%,-50%);
  transition: transform 0.1s, width 0.2s, height 0.2s, background 0.2s;
  box-shadow: 0 0 15px var(--accent-glow);
}
#cursor-blur {
  position: fixed; width: 36px; height: 36px;
  border: 1.5px solid rgba(229,9,20,0.4);
  border-radius: 50%; pointer-events: none; z-index: 9998;
  transform: translate(-50%,-50%);
  transition: all 0.15s ease-out;
}

/* LOADER */
#loader {
  position: fixed; inset: 0; background: var(--bg);
  z-index: 10000; display: flex; align-items: center; justify-content: center;
  transition: opacity 0.6s ease, visibility 0.6s;
}
#loader.hidden { opacity: 0; visibility: hidden; pointer-events: none; }
.loader-inner { text-align: center; }
.loader-logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 4.5rem; letter-spacing: 0.1em;
  color: var(--text); margin-bottom: 1.5rem;
  text-shadow: 0 0 30px var(--accent-glow);
}
.loader-logo span { color: var(--accent); }
.loader-bar {
  width: 280px; height: 4px; background: rgba(255,255,255,0.05);
  border-radius: 4px; overflow: hidden; margin: 0 auto; position: relative;
}
.loader-fill {
  height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2));
  border-radius: 4px; animation: loaderAnim 1.5s cubic-bezier(0.65, 0, 0.35, 1) forwards;
  box-shadow: 0 0 15px var(--accent);
}
@keyframes loaderAnim { from { width: 0 } to { width: 100% } }

/* NAVBAR */
#navbar {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 1000; padding: 0 3rem; height: 80px;
  display: flex; align-items: center;
  background: linear-gradient(180deg, rgba(6,9,17,0.9) 0%, transparent 100%);
  transition: all var(--transition);
}
#navbar.scrolled {
  height: 70px;
  background: rgba(6, 9, 17, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.nav-container { width: 100%; display: flex; align-items: center; gap: 2.5rem; }
.nav-logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.2rem; letter-spacing: 0.08em; flex-shrink: 0;
  text-shadow: 0 0 20px var(--accent-glow);
}
.nav-logo span { color: var(--accent); }
.nav-links { display: flex; gap: 0.5rem; flex: 1; justify-content: center; }
.nav-links a {
  padding: 0.6rem 1.2rem; border-radius: var(--radius);
  font-size: 0.92rem; font-weight: 600; color: var(--text2);
  transition: all var(--transition);
  position: relative; cursor: pointer;
}
.nav-links a:hover, .nav-links a.active { color: var(--text); background: rgba(255,255,255,0.05); }
.nav-links a.active::after {
  content: ''; position: absolute; bottom: 4px; left: 50%; transform: translateX(-50%);
  width: 16px; height: 3px; background: var(--accent); border-radius: 2px;
  box-shadow: 0 0 8px var(--accent);
}
.nav-right { display: flex; align-items: center; gap: 1rem; flex-shrink: 0; }
.nav-search {
  display: flex; align-items: center;
  background: rgba(255,255,255,0.05); border: 1px solid var(--border);
  border-radius: var(--radius); overflow: hidden;
  transition: all var(--transition);
  backdrop-filter: blur(10px);
}
.nav-search:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 20px var(--accent-glow);
  background: rgba(0,0,0,0.4);
}
.nav-search input {
  background: transparent; border: none;
  color: var(--text); padding: 0.6rem 1.2rem;
  width: 220px; font-size: 0.88rem;
}
.nav-search input::placeholder { color: var(--text3); }
.search-btn {
  background: none; padding: 0.6rem 1rem; color: var(--text2);
  display: flex; align-items: center; justify-content: center;
  transition: color var(--transition);
}
.search-btn:hover { color: var(--accent); }

/* HERO */
.hero {
  position: relative; height: 92vh; min-height: 680px;
  overflow: hidden; display: flex; align-items: center;
}
.hero-bg { position: absolute; inset: 0; }
.hero-bg-slide {
  position: absolute; inset: 0;
  background-size: cover; background-position: center 20%;
  opacity: 0; transition: opacity 1.2s ease, transform 12s ease;
  transform: scale(1.08);
}
.hero-bg-slide.active { opacity: 1; transform: scale(1); }
.hero-overlay {
  position: absolute; inset: 0;
  background: 
    radial-gradient(circle at 80% 20%, transparent 20%, var(--bg) 90%),
    linear-gradient(90deg, var(--bg) 0%, rgba(6,9,17,0.7) 50%, transparent 100%),
    linear-gradient(0deg, var(--bg) 0%, transparent 50%);
}
.hero-content {
  position: relative; z-index: 2; max-width: 700px; padding: 0 4rem;
  animation: heroIn 1s ease 0.3s both;
}
@keyframes heroIn { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }

.hero-badge {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: rgba(229,9,20,0.15); border: 1px solid rgba(229,9,20,0.3);
  color: var(--accent2); font-size: 0.82rem; font-weight: 800;
  padding: 0.4rem 1rem; border-radius: 50px; margin-bottom: 1.25rem;
  backdrop-filter: blur(10px);
  box-shadow: 0 0 15px var(--accent-glow);
}
.hero-title {
  font-family: 'Cairo', sans-serif;
  font-weight: 900;
  font-size: clamp(2.8rem, 5vw, 4.5rem); line-height: 1.15;
  color: #fff; text-shadow: 0 10px 30px rgba(0,0,0,0.8); margin-bottom: 1rem;
}
.hero-meta {
  display: flex; align-items: center; gap: 0.8rem;
  color: var(--text2); font-size: 0.95rem; font-weight: 600;
  margin-bottom: 1.25rem; flex-wrap: wrap;
}
.rating { color: var(--gold); font-weight: 800; }
.hero-desc {
  color: var(--text2); font-size: 1.05rem; line-height: 1.8;
  max-width: 580px; margin-bottom: 2.25rem; text-shadow: 0 2px 10px rgba(0,0,0,0.5);
}
.hero-btns { display: flex; gap: 1.2rem; }

.btn-watch {
  display: inline-flex; align-items: center; gap: 0.75rem;
  background: var(--accent); color: #fff;
  padding: 0.95rem 2.25rem; border-radius: var(--radius);
  font-size: 1.05rem; font-weight: 800;
  transition: all var(--transition);
  box-shadow: 0 10px 30px var(--accent-glow);
}
.btn-watch:hover { background: var(--accent2); transform: translateY(-3px); box-shadow: 0 15px 40px rgba(229,9,20,0.6); }

.btn-info {
  display: inline-flex; align-items: center; gap: 0.75rem;
  background: rgba(255,255,255,0.08); border: 1px solid var(--border);
  color: #fff; padding: 0.95rem 2.25rem;
  border-radius: var(--radius); font-size: 1.05rem; font-weight: 700;
  backdrop-filter: blur(10px); transition: all var(--transition);
}
.btn-info:hover { background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.3); transform: translateY(-3px); }

/* STATS */
.stats-bar {
  background: linear-gradient(180deg, var(--bg) 0%, var(--bg2) 100%);
  border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
  display: grid; grid-template-columns: repeat(4, 1fr);
  padding: 2rem 4rem; position: relative; z-index: 5;
}
.stat-item { text-align: center; border-left: 1px solid var(--border); padding: 0.5rem 1rem; }
.stat-item:last-child { border-left: none; }
.stat-num {
  display: block; font-family: 'Bebas Neue', sans-serif;
  font-size: 3rem; color: var(--accent);
  letter-spacing: 0.05em; line-height: 1;
  text-shadow: 0 0 20px var(--accent-glow);
}
.stat-label { display: block; font-size: 0.85rem; color: var(--text2); margin-top: 0.35rem; font-weight: 600; }

/* SECTIONS */
.section { padding: 4rem; }
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 2rem;
}
.section-title { 
  font-size: 1.6rem; font-weight: 800; color: var(--text); 
  display: flex; align-items: center; gap: 0.75rem;
}
.section-title::before {
  content: ''; width: 5px; height: 24px; background: var(--accent);
  border-radius: 4px; box-shadow: 0 0 10px var(--accent);
}

/* MOVIES GRID */
.movies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 1.5rem;
}
.movie-card {
  position: relative; border-radius: var(--radius);
  overflow: hidden; background: var(--surface);
  border: 1px solid var(--border);
  transition: all var(--transition); cursor: pointer;
}
.movie-card:hover {
  transform: translateY(-10px) scale(1.02);
  border-color: var(--border-glow);
  box-shadow: 0 20px 40px rgba(0,0,0,0.8), 0 0 20px var(--accent-glow);
  z-index: 10;
}
.movie-poster {
  width: 100%; aspect-ratio: 2/3; object-fit: cover;
  display: block; transition: transform 0.5s ease;
}
.movie-card:hover .movie-poster { transform: scale(1.08); }

.card-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(0deg, rgba(6,9,17,0.95) 0%, rgba(6,9,17,0.4) 60%, transparent 100%);
  opacity: 0; transition: opacity var(--transition);
  display: flex; flex-direction: column; justify-content: flex-end;
  padding: 1.2rem;
}
.movie-card:hover .card-overlay { opacity: 1; }
.card-info { transform: translateY(15px); transition: transform var(--transition); }
.movie-card:hover .card-info { transform: translateY(0); }

.card-title { font-size: 0.95rem; font-weight: 800; color: #fff; margin-bottom: 0.35rem; line-height: 1.3; }
.card-meta { font-size: 0.78rem; color: var(--text2); display: flex; gap: 0.6rem; margin-bottom: 0.85rem; }
.card-rating { color: var(--gold); font-weight: 800; }
.card-btns { display: flex; gap: 0.5rem; }
.card-btn-play {
  flex: 1; background: var(--accent); border: none; color: #fff;
  padding: 0.5rem; border-radius: 8px; font-size: 0.82rem; font-weight: 700;
  transition: background var(--transition);
  display: flex; align-items: center; justify-content: center; gap: 0.3rem;
}
.card-btn-play:hover { background: var(--accent2); }

/* MOVIES ROW */
.movies-row {
  display: flex; gap: 1.5rem; overflow-x: auto;
  padding-bottom: 1.5rem; scrollbar-width: none;
}
.movies-row::-webkit-scrollbar { display: none; }
.movies-row .movie-card { flex: 0 0 200px; }

/* CATEGORIES GRID */
.categories-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1.25rem; margin-top: 1.5rem;
}
.cat-card {
  padding: 1.75rem 1.25rem; border-radius: var(--radius);
  background: var(--surface); border: 1px solid var(--border);
  font-size: 1.1rem; font-weight: 800; color: var(--text2);
  transition: all var(--transition); text-align: center;
  backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: center; gap: 0.75rem;
  cursor: pointer;
}
.cat-card:hover {
  border-color: var(--accent); color: var(--text);
  background: var(--surface-hover); transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.5), 0 0 15px var(--accent-glow);
}

/* FOOTER */
.footer {
  background: var(--bg2); border-top: 1px solid var(--border);
  padding: 4rem 4rem 2rem; margin-top: 4rem;
}
.footer-content {
  display: grid; grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 3rem; margin-bottom: 3rem;
}
.footer-logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.2rem; letter-spacing: 0.08em; margin-bottom: 1rem;
}
.footer-logo span { color: var(--accent); }
.footer-brand p { color: var(--text2); font-size: 0.9rem; line-height: 1.8; max-width: 350px; }
.footer-col h4 { font-size: 1rem; font-weight: 800; color: var(--text); margin-bottom: 1.2rem; }
.footer-col a {
  display: block; color: var(--text2); font-size: 0.88rem;
  padding: 0.4rem 0; transition: color var(--transition);
}
.footer-col a:hover { color: var(--accent); }
.footer-bottom {
  border-top: 1px solid var(--border); padding-top: 1.5rem;
  text-align: center; color: var(--text3); font-size: 0.85rem;
}

/* MODALS */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.85); backdrop-filter: blur(12px);
  z-index: 5000; display: flex; align-items: center; justify-content: center;
  opacity: 0; visibility: hidden; transition: all var(--transition); padding: 1.5rem;
}
.modal-overlay.active { opacity: 1; visibility: visible; }
.modal {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 2.5rem;
  width: 100%; max-width: 460px; position: relative;
  box-shadow: 0 25px 50px rgba(0,0,0,0.9), 0 0 30px rgba(229,9,20,0.15);
  transform: scale(0.95); transition: transform var(--transition);
  max-height: 90vh; overflow-y: auto;
}
.modal-overlay.active .modal { transform: scale(1); }
.modal.modal-wide { max-width: 950px; }

.modal-close {
  position: absolute; top: 1.25rem; left: 1.25rem;
  background: rgba(255,255,255,0.05); border: 1px solid var(--border);
  color: var(--text2); width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition); z-index: 10;
}
.modal-close:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

/* STREAM PLAYER CONTAINER */
.player-container {
  position: relative; width: 100%; padding-top: 56.25%;
  background: #000; border-radius: var(--radius); overflow: hidden;
  box-shadow: 0 10px 40px rgba(0,0,0,0.8);
}
.player-container iframe {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;
}

.seasons-selector { display: flex; gap: 0.6rem; flex-wrap: wrap; margin: 1.5rem 0; }
.season-btn {
  background: var(--surface); border: 1px solid var(--border);
  color: var(--text2); padding: 0.6rem 1.2rem; border-radius: var(--radius);
  font-weight: 700; transition: all 0.2s; cursor: pointer;
}
.season-btn.active, .season-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

.episodes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; }
.episode-card {
  background: var(--surface); border-radius: var(--radius); overflow: hidden;
  border: 1px solid var(--border); cursor: pointer; transition: transform 0.2s;
}
.episode-card:hover { transform: translateY(-4px); border-color: var(--accent); }
.episode-thumb { width: 100%; aspect-ratio: 16/9; object-fit: cover; }
.episode-details { padding: 0.75rem; }
.episode-title { font-size: 0.85rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* RESPONSIVE */
@media (max-width: 1024px) {
  #navbar { padding: 0 1.5rem; }
  .hero-content { padding: 0 2rem; }
  .section { padding: 3rem 2rem; }
  .stats-bar { grid-template-columns: repeat(2, 1fr); padding: 1.5rem 2rem; gap: 1rem; }
  .footer-content { grid-template-columns: 1fr 1fr; gap: 2rem; }
}
@media (max-width: 768px) {
  .nav-links { display: none; }
  .hero-title { font-size: 2.5rem; }
  .hero-btns { flex-direction: column; }
  .footer-content { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<!-- LOADER -->
<div id="loader">
  <div class="loader-inner">
    <div class="loader-logo">ONYX <span>MOVIE</span></div>
    <div class="loader-bar"><div class="loader-fill"></div></div>
  </div>
</div>

<!-- CURSOR -->
<div id="cursor"></div>
<div id="cursor-blur"></div>

<!-- NAVBAR -->
<nav id="navbar">
  <div class="nav-container">
    <div class="nav-logo">ONYX <span>MOVIE</span></div>

    <ul class="nav-links">
      <li><a onclick="window.scrollTo({top:0, behavior:'smooth'})" class="active">الرئيسية</a></li>
      <li><a onclick="document.getElementById('movies').scrollIntoView({behavior:'smooth'})">الأفلام</a></li>
      <li><a onclick="document.getElementById('series').scrollIntoView({behavior:'smooth'})">المسلسلات</a></li>
      <li><a onclick="document.getElementById('categories').scrollIntoView({behavior:'smooth'})">التصنيفات</a></li>
    </ul>

    <div class="nav-right">
      <div class="nav-search">
        <input type="text" placeholder="ابحث عن فيلم أو مسلسل..." id="searchInput" onkeydown="if(event.key==='Enter')doSearch()" />
        <button class="search-btn" onclick="doSearch()">🔍</button>
      </div>
    </div>
  </div>
</nav>

<!-- HERO -->
<section class="hero" id="hero">
  <div class="hero-bg" id="heroBg"></div>
  <div class="hero-overlay"></div>

  <div class="hero-content">
    <div class="hero-badge">🔥 الأكثر مشاهدة اليوم</div>
    <h1 class="hero-title" id="heroTitle">جاري التحميل...</h1>
    <p class="hero-meta" id="heroMeta"></p>
    <p class="hero-desc" id="heroDesc"></p>
    <div class="hero-btns">
      <button class="btn-watch" onclick="watchHero()">▶ شاهد الآن</button>
    </div>
  </div>
</section>

<!-- STATS -->
<section class="stats-bar">
  <div class="stat-item"><span class="stat-num" data-target="50000">0</span><span class="stat-label">فيلم ومسلسل</span></div>
  <div class="stat-item"><span class="stat-num" data-target="12000000">0</span><span class="stat-label">مشترك نشط</span></div>
  <div class="stat-item"><span class="stat-num" data-target="195">0</span><span class="stat-label">دولة</span></div>
  <div class="stat-item"><span class="stat-num" data-target="4">0</span><span class="stat-label">K جودة العرض</span></div>
</section>

<!-- TRENDING -->
<section class="section" id="movies">
  <div class="section-header">
    <h2 class="section-title" id="trendingTitle">الأكثر رواجاً هذا الأسبوع</h2>
  </div>
  <div class="movies-grid" id="trendingGrid"></div>
</section>

<!-- POPULAR -->
<section class="section">
  <div class="section-header">
    <h2 class="section-title">أفلام شائعة</h2>
  </div>
  <div class="movies-row" id="popularGrid"></div>
</section>

<!-- SERIES -->
<section class="section" id="series">
  <div class="section-header">
    <h2 class="section-title">أحدث المسلسلات</h2>
  </div>
  <div class="movies-row" id="seriesGrid"></div>
</section>

<!-- CATEGORIES -->
<section class="section" id="categories">
  <h2 class="section-title">استكشف الأنواع والتصنيفات</h2>
  <div class="categories-grid">
    <div class="cat-card" onclick="filterGenre(28)">💥 أكشن</div>
    <div class="cat-card" onclick="filterGenre(878)">🚀 خيال علمي</div>
    <div class="cat-card" onclick="filterGenre(27)">👻 رعب</div>
    <div class="cat-card" onclick="filterGenre(10749)">❤️ رومانسي</div>
    <div class="cat-card" onclick="filterGenre(12)">🗺️ مغامرة</div>
    <div class="cat-card" onclick="filterGenre(35)">😂 كوميدي</div>
    <div class="cat-card" onclick="filterGenre(36)">🏛️ تاريخي</div>
    <div class="cat-card" onclick="filterGenre(18)">🎭 دراما</div>
  </div>
</section>

<!-- FOOTER -->
<footer class="footer">
  <div class="footer-content">
    <div class="footer-brand">
      <div class="footer-logo">ONYX <span>MOVIE</span></div>
      <p>منصتك الأولى لمشاهدة أحدث الأفلام والمسلسلات العالمية بجودة عالية وبدون إعلانات مزعجة.</p>
    </div>
    <div class="footer-col">
      <h4>المحتوى</h4>
      <a href="#movies">الأفلام</a>
      <a href="#series">المسلسلات</a>
      <a href="#categories">التصنيفات</a>
    </div>
  </div>
  <div class="footer-bottom">
    <p>© 2026 ONYX STUDIO. جميع الحقوق محفوظة.</p>
  </div>
</footer>

<!-- STREAM PLAYER MODAL -->
<div class="modal-overlay" id="watchModal" onclick="closeOnOverlay(event,'watchModal')">
  <div class="modal modal-wide">
    <button class="modal-close" onclick="closeWatchModal()">✕</button>
    <h2 id="watchTitle" style="margin-bottom: 1.2rem; font-size: 1.3rem;">جاري التشغيل...</h2>
    <div class="player-container" id="playerContainer"></div>
    <div id="seasonsSection"></div>
  </div>
</div>

<script>
const IMG = 'https://image.tmdb.org/t/p';
const SOURCES = __SOURCES__;
const state = { heroMovies: [], currentMedia: null };

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => document.getElementById('loader')?.classList.add('hidden'), 1000);
  initCursor();
  initNavbar();
  initCounters();
  loadAll();
});

function initCursor() {
  const c = document.getElementById('cursor'), b = document.getElementById('cursor-blur');
  document.addEventListener('mousemove', e => {
    c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px';
    b.style.left = e.clientX + 'px'; b.style.top = e.clientY + 'px';
  });
}

function initNavbar() {
  window.addEventListener('scroll', () => {
    document.getElementById('navbar')?.classList.toggle('scrolled', window.scrollY > 50);
  });
}

function initCounters() {
  document.querySelectorAll('.stat-num').forEach(el => {
    let target = +el.dataset.target, count = 0, inc = target / 100;
    let timer = setInterval(() => {
      count += inc;
      if(count >= target) { count = target; clearInterval(timer); }
      el.textContent = Math.floor(count).toLocaleString();
    }, 20);
  });
}

async function loadAll() {
  loadHero();
  loadTrending();
  loadPopular();
  loadSeries();
}

async function loadHero() {
  try {
    const res = await fetch('/api/trending');
    const data = await res.json();
    state.heroMovies = (data.results || []).slice(0, 5);
    renderHero(0);
  } catch(e){}
}

function renderHero(i) {
  const m = state.heroMovies[i];
  if (!m) return;
  document.getElementById('heroBg').style.backgroundImage = `url('${IMG}/original${m.backdrop_path}')`;
  document.getElementById('heroTitle').textContent = m.title || m.name;
  document.getElementById('heroMeta').innerHTML = `<span>⭐ ${m.vote_average.toFixed(1)}</span> • <span>${(m.release_date||m.first_air_date||'').slice(0,4)}</span>`;
  document.getElementById('heroDesc').textContent = m.overview || 'لا يوجد وصف متاح.';
}

function watchHero() {
  const m = state.heroMovies[0];
  if (m) openMedia(m.id, m.media_type || 'movie', m.title || m.name);
}

function movieCard(m) {
  const title = m.title || m.name;
  const poster = m.poster_path ? `${IMG}/w500${m.poster_path}` : 'https://via.placeholder.com/500x750';
  const type = m.media_type || (m.first_air_date ? 'tv' : 'movie');
  return `
    <div class="movie-card" onclick="openMedia(${m.id}, '${type}', '${title.replace(/'/g, "\\'")}')">
      <img class="movie-poster" src="${poster}" alt="${title}" loading="lazy">
      <div class="card-overlay">
        <div class="card-info">
          <div class="card-title">${title}</div>
          <div class="card-meta"><span class="card-rating">⭐ ${m.vote_average ? m.vote_average.toFixed(1) : '?'}</span></div>
          <div class="card-btns"><button class="card-btn-play">▶ مشاهدة</button></div>
        </div>
      </div>
    </div>`;
}

async function loadTrending() {
  const res = await fetch('/api/trending');
  const data = await res.json();
  document.getElementById('trendingGrid').innerHTML = (data.results || []).slice(0, 12).map(movieCard).join('');
}

async function loadPopular() {
  const res = await fetch('/api/popular/movie');
  const data = await res.json();
  document.getElementById('popularGrid').innerHTML = (data.results || []).slice(0, 10).map(movieCard).join('');
}

async function loadSeries() {
  const res = await fetch('/api/popular/tv');
  const data = await res.json();
  document.getElementById('seriesGrid').innerHTML = (data.results || []).slice(0, 10).map(movieCard).join('');
}

async function openMedia(id, type, title) {
  state.currentMedia = { id, type, title };
  document.getElementById('watchTitle').textContent = `تشغيل: ${title}`;
  document.getElementById('seasonsSection').innerHTML = '';
  
  startStreaming(1, 1);
  
  if (type === 'tv') {
    try {
      const res = await fetch(`/api/tv/${id}`);
      const m = await res.json();
      if (m.seasons && m.seasons.length) {
        let html = '<div class="seasons-selector">';
        const seasons = m.seasons.filter(s => s.season_number > 0);
        seasons.forEach((s, idx) => {
          html += `<button class="season-btn ${idx===0?'active':''}" onclick="loadEpisodes(${id}, ${s.season_number}, this)">الموسم ${s.season_number}</button>`;
        });
        html += '</div><div class="episodes-grid" id="episodesGrid"></div>';
        document.getElementById('seasonsSection').innerHTML = html;
        if (seasons[0]) loadEpisodes(id, seasons[0].season_number);
      }
    } catch(e){}
  }
  
  openModal('watchModal');
}

function startStreaming(season, episode) {
  const src = SOURCES[0];
  let url = src[state.currentMedia.type] || src.movie;
  url = url.replace('{id}', state.currentMedia.id).replace('{s}', season).replace('{e}', episode);
  document.getElementById('playerContainer').innerHTML = `<iframe src="${url}" allowfullscreen allow="autoplay; encrypted-media"></iframe>`;
}

async function loadEpisodes(tvId, seasonNum, btn) {
  if (btn) {
    document.querySelectorAll('.season-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }
  const grid = document.getElementById('episodesGrid');
  if (!grid) return;
  grid.innerHTML = '<p>جاري التحميل...</p>';
  try {
    const res = await fetch(`/api/tv/${tvId}/season/${seasonNum}`);
    const data = await res.json();
    grid.innerHTML = (data.episodes || []).map(ep => {
      const still = ep.still_path ? `${IMG}/w300${ep.still_path}` : 'https://via.placeholder.com/300x169';
      return `
        <div class="episode-card" onclick="startStreaming(${seasonNum}, ${ep.episode_number})">
          <img class="episode-thumb" src="${still}">
          <div class="episode-details">
            <div class="episode-title">الحلقة ${ep.episode_number}: ${ep.name || ''}</div>
          </div>
        </div>`;
    }).join('');
  } catch(e) { grid.innerHTML = '<p>خطأ في جلب الحلقات</p>'; }
}

async function doSearch() {
  const q = document.getElementById('searchInput').value.trim();
  if (!q) return;
  const grid = document.getElementById('trendingGrid');
  document.getElementById('trendingTitle').textContent = `نتائج البحث عن: ${q}`;
  grid.innerHTML = '<p>جاري البحث...</p>';
  document.getElementById('movies').scrollIntoView({behavior:'smooth'});
  try {
    const res = await fetch('/api/search?q=' + encodeURIComponent(q));
    const data = await res.json();
    grid.innerHTML = (data.results || []).filter(m => m.poster_path).map(movieCard).join('') || '<p>لا توجد نتائج</p>';
  } catch(e){ grid.innerHTML = '<p>خطأ في البحث</p>'; }
}

async function filterGenre(genreId) {
  const grid = document.getElementById('trendingGrid');
  grid.innerHTML = '<p>جاري التحميل...</p>';
  document.getElementById('movies').scrollIntoView({behavior:'smooth'});
  try {
    const res = await fetch(`${TMDB_BASE}/discover/movie?api_key=${TMDB_API_KEY}&with_genres=${genreId}&language=ar`);
    const data = await res.json();
    grid.innerHTML = (data.results || []).filter(m => m.poster_path).map(movieCard).join('');
  } catch(e){}
}

function closeWatchModal() {
  document.getElementById('playerContainer').innerHTML = '';
  closeModal('watchModal');
}

function openModal(id) { document.getElementById(id)?.classList.add('active'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('active'); }
function closeOnOverlay(e, id) { if(e.target.id === id) closeWatchModal(); }
</script>
</body>
</html>
"""

INDEX_HTML = INDEX_HTML.replace('__SOURCES__', SOURCES_JSON)

# ══════════════════════════════════════════════════════════
# ROUTES API
# ══════════════════════════════════════════════════════════
@app.route("/")
def index():
    return INDEX_HTML

@app.route("/api/trending")
def api_trending():
    return jsonify(tmdb("/trending/all/week"))

@app.route("/api/popular/<mt>")
def api_popular(mt):
    if mt not in ("movie", "tv"):
        return jsonify({"error": "invalid"}), 400
    return jsonify(tmdb(f"/{mt}/popular"))

@app.route("/api/movie/<int:mid>")
def api_movie(mid):
    return jsonify(tmdb(f"/movie/{mid}"))

@app.route("/api/tv/<int:tid>")
def api_tv(tid):
    return jsonify(tmdb(f"/tv/{tid}"))

@app.route("/api/tv/<int:tid>/season/<int:s>")
def api_tv_season(tid, s):
    return jsonify(tmdb(f"/tv/{tid}/season/{s}"))

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    return jsonify(tmdb("/search/multi", {"query": q}))

@app.route("/health")
def health():
    return jsonify({"status": "ok", "tmdb": "ok" if TMDB_API_KEY else "missing"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
