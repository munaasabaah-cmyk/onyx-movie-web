# -*- coding: utf-8 -*-
"""🎬 ONYX MOVIE — Flask + TMDB + 25 Player Sources (HD/4K)"""

from flask import Flask, jsonify, request
import os
import urllib.request
import urllib.parse
import json

app = Flask(__name__)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p"

# ══════════════════════════════════════════════════════════
# 🎬 25 مصدر — مرتبين من الأفضل (4K + بدون إعلانات)
# ══════════════════════════════════════════════════════════

PLAYER_SOURCES = [
    # ═══ المستوى 1: 4K/HD + بدون إعلانات ═══
    {"name": "VidLink 4K",     "quality": "4K", "ads": "none",
     "movie": "https://vidlink.pro/movie/{id}?primaryColor=e50914&autoplay=true",
     "tv":    "https://vidlink.pro/tv/{id}/{season}/{episode}?primaryColor=e50914&autoplay=true"},

    {"name": "Videasy 4K",     "quality": "4K", "ads": "none",
     "movie": "https://player.videasy.net/movie/{id}",
     "tv":    "https://player.videasy.net/tv/{id}/{season}/{episode}"},

    {"name": "AutoEmbed HD",   "quality": "HD", "ads": "none",
     "movie": "https://player.autoembed.cc/embed/movie/{id}",
     "tv":    "https://player.autoembed.cc/embed/tv/{id}/{season}/{episode}"},

    {"name": "SmashyStream",   "quality": "HD", "ads": "none",
     "movie": "https://player.smashy.stream/movie/{id}",
     "tv":    "https://player.smashy.stream/tv/{id}?s={season}&e={episode}"},

    {"name": "VidPlus HD",     "quality": "HD", "ads": "low",
     "movie": "https://vidplus.to/embed/movie/{id}",
     "tv":    "https://vidplus.to/embed/tv/{id}/{season}/{episode}"},

    # ═══ المستوى 2: HD + إعلانات قليلة ═══
    {"name": "VidSrc.xyz",     "quality": "HD", "ads": "low",
     "movie": "https://vidsrc.xyz/embed/movie?tmdb={id}",
     "tv":    "https://vidsrc.xyz/embed/tv?tmdb={id}&season={season}&episode={episode}"},

    {"name": "2Embed.to",      "quality": "HD", "ads": "low",
     "movie": "https://www.2embed.to/embed/tmdb/movie?id={id}",
     "tv":    "https://www.2embed.to/embed/tmdb/tv?id={id}&s={season}&e={episode}"},

    {"name": "Embed.su",       "quality": "HD", "ads": "low",
     "movie": "https://embed.su/embed/movie/{id}",
     "tv":    "https://embed.su/embed/tv/{id}/{season}/{episode}"},

    {"name": "MoviesAPI",      "quality": "HD", "ads": "low",
     "movie": "https://moviesapi.club/movie/{id}",
     "tv":    "https://moviesapi.club/tv/{id}-{season}-{episode}"},

    {"name": "VidSrc.io",      "quality": "HD", "ads": "low",
     "movie": "https://vidsrc.io/embed/movie/{id}",
     "tv":    "https://vidsrc.io/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc.cc",      "quality": "SD", "ads": "medium",
     "movie": "https://vidsrc.cc/v2/embed/movie/{id}",
     "tv":    "https://vidsrc.cc/v2/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc.wtf",     "quality": "SD", "ads": "medium",
     "movie": "https://vidsrc.wtf/api/1/movie/?id={id}",
     "tv":    "https://vidsrc.wtf/api/1/tv/?id={id}&s={season}&e={episode}"},

    {"name": "VidSrc.dev",     "quality": "SD", "ads": "medium",
     "movie": "https://vidsrc.dev/embed/movie/{id}",
     "tv":    "https://vidsrc.dev/embed/tv/{id}/{season}/{episode}"},

    # ═══ المستوى 3: احتياطي ═══
    {"name": "VidSrc.to",      "quality": "SD", "ads": "medium",
     "movie": "https://vidsrc.to/embed/movie/{id}",
     "tv":    "https://vidsrc.to/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc.me",      "quality": "SD", "ads": "medium",
     "movie": "https://vidsrc.me/embed/movie?tmdb={id}",
     "tv":    "https://vidsrc.me/embed/tv?tmdb={id}&season={season}&episode={episode}"},

    {"name": "SuperEmbed",     "quality": "SD", "ads": "high",
     "movie": "https://multiembed.mov/?video_id={id}&tmdb=1",
     "tv":    "https://multiembed.mov/?video_id={id}&tmdb=1&s={season}&e={episode}"},

    {"name": "MultiEmbed",     "quality": "SD", "ads": "high",
     "movie": "https://multiembed.mov/directstream.php?video_id={id}&tmdb=1",
     "tv":    "https://multiembed.mov/directstream.php?video_id={id}&tmdb=1&s={season}&e={episode}"},

    {"name": "2Embed.cc",      "quality": "SD", "ads": "high",
     "movie": "https://www.2embed.cc/embed/{id}",
     "tv":    "https://www.2embed.cc/embedtv/{id}&s={season}&e={episode}"},

    {"name": "VidSrc.lol",     "quality": "SD", "ads": "high",
     "movie": "https://vidsrc.lol/embed/movie/{id}",
     "tv":    "https://vidsrc.lol/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc.pw",      "quality": "SD", "ads": "high",
     "movie": "https://vidsrc.pw/embed/movie/{id}",
     "tv":    "https://vidsrc.pw/embed/tv/{id}/{season}/{episode}"},

    {"name": "Player4u",       "quality": "SD", "ads": "high",
     "movie": "https://player4u.xyz/embed/movie/{id}",
     "tv":    "https://player4u.xyz/embed/tv/{id}/{season}/{episode}"},
]


# ══════════════════════════════════════════════════════════
# HTML الرئيسية
# ══════════════════════════════════════════════════════════

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>ONYX MOVIE — مشاهدة الأفلام بجودة 4K</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet" />
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #080b14; --bg2: #0d1117; --bg3: #12172a;
  --surface: #161d30; --surface2: #1e2740;
  --accent: #e50914; --accent2: #ff4c54;
  --gold: #f5c518;
  --green: #22c55e;
  --text: #f0f0f0; --text2: #a0aabf; --text3: #5a6480;
  --border: rgba(255,255,255,0.07);
  --radius: 12px; --radius-lg: 20px;
  --transition: 0.3s cubic-bezier(0.4,0,0.2,1);
  --glow: 0 0 40px rgba(229,9,20,0.3);
  --font: 'Cairo', sans-serif;
}

html { scroll-behavior: smooth; font-size: 16px; }
body { background: var(--bg); color: var(--text); font-family: var(--font); direction: rtl; overflow-x: hidden; }
a { text-decoration: none; color: inherit; }
img { max-width: 100%; display: block; }
button { cursor: pointer; font-family: var(--font); border: none; }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 4px; }
::selection { background: var(--accent); color: #fff; }

#navbar {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 1000; padding: 0 2rem; height: 70px;
  display: flex; align-items: center;
  background: rgba(8,11,20,0.95);
  backdrop-filter: blur(20px);
  box-shadow: 0 2px 40px rgba(0,0,0,0.5);
}
.nav-container { width: 100%; display: flex; align-items: center; gap: 2rem; max-width: 1600px; margin: 0 auto; }
.nav-logo { font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem; letter-spacing: 0.08em; flex-shrink: 0; }
.nav-logo span { color: var(--accent); }
.nav-links { display: flex; gap: 0.25rem; flex: 1; justify-content: center; }
.nav-links a { padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem; font-weight: 600; color: var(--text2); transition: color var(--transition); cursor: pointer; }
.nav-links a:hover, .nav-links a.active { color: var(--text); }
.nav-search { display: flex; align-items: center; flex-shrink: 0; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.nav-search:focus-within { border-color: var(--accent); }
.nav-search input { background: transparent; border: none; outline: none; color: var(--text); padding: 0.55rem 1rem; width: 240px; font-size: 0.85rem; font-family: var(--font); }
.nav-search input::placeholder { color: var(--text3); }
.nav-search button { background: var(--accent); color: #fff; padding: 0.55rem 1rem; font-size: 0.85rem; font-weight: 700; transition: background var(--transition); }
.nav-search button:hover { background: var(--accent2); }

.hero { position: relative; height: 75vh; min-height: 500px; overflow: hidden; display: flex; align-items: center; margin-top: 70px; }
.hero-bg { position: absolute; inset: 0; }
.hero-bg-slide { position: absolute; inset: 0; background-size: cover; background-position: center; opacity: 0; transition: opacity 1.2s ease; }
.hero-bg-slide.active { opacity: 1; }
.hero-overlay { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(8,11,20,0.95) 0%, rgba(8,11,20,0.6) 50%, rgba(8,11,20,0.2) 100%), linear-gradient(0deg, rgba(8,11,20,1) 0%, transparent 40%); }
.hero-content { position: relative; z-index: 2; max-width: 650px; padding: 0 4rem; }
.hero-badge { display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(229,9,20,0.15); border: 1px solid rgba(229,9,20,0.4); color: var(--accent2); font-size: 0.8rem; font-weight: 700; padding: 0.35rem 0.85rem; border-radius: 50px; margin-bottom: 1rem; }
.hero-title { font-family: 'Bebas Neue', sans-serif; font-size: clamp(2.5rem, 6vw, 5rem); line-height: 1; color: #fff; text-shadow: 0 4px 30px rgba(0,0,0,0.5); margin-bottom: 1rem; }
.hero-meta { display: flex; align-items: center; gap: 1rem; color: var(--text2); font-size: 0.95rem; font-weight: 600; margin-bottom: 1rem; flex-wrap: wrap; }
.hero-meta .rating { color: var(--gold); }
.hero-desc { color: var(--text2); font-size: 1rem; line-height: 1.7; max-width: 550px; margin-bottom: 2rem; }
.btn-play { display: inline-flex; align-items: center; gap: 0.6rem; background: var(--accent); color: #fff; padding: 0.85rem 2rem; border-radius: var(--radius); font-size: 1rem; font-weight: 700; transition: all var(--transition); }
.btn-play:hover { background: var(--accent2); box-shadow: var(--glow); transform: translateY(-2px); }

.section { padding: 3rem 4rem; max-width: 1600px; margin: 0 auto; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.75rem; }
.section-title { font-size: 1.6rem; font-weight: 700; }
.section-sub { font-size: 0.85rem; color: var(--text2); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1.25rem; }
.card { position: relative; border-radius: var(--radius); overflow: hidden; background: var(--surface); transition: all var(--transition); cursor: pointer; }
.card:hover { transform: translateY(-8px); box-shadow: 0 20px 60px rgba(0,0,0,0.6); z-index: 2; }
.card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; background: var(--surface2); transition: transform var(--transition); }
.card:hover img { transform: scale(1.05); }
.card-info { padding: 0.85rem; }
.card-title { font-size: 0.9rem; font-weight: 700; color: #fff; margin-bottom: 0.3rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-meta { font-size: 0.75rem; color: var(--text2); display: flex; gap: 0.5rem; flex-wrap: wrap; }
.card-meta .rating { color: var(--gold); font-weight: 700; }
.card-badge-hd { position: absolute; top: 8px; right: 8px; background: var(--accent); color: #fff; font-size: 0.65rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; z-index: 2; }
.card-badge-hd.green { background: var(--green); }

.top-list { display: flex; flex-direction: column; gap: 0.75rem; }
.top-item { display: flex; align-items: center; gap: 1.25rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 0.85rem 1.25rem; transition: all var(--transition); cursor: pointer; }
.top-item:hover { background: var(--surface2); }
.top-rank { font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem; color: var(--accent); width: 2.5rem; text-align: center; flex-shrink: 0; }
.top-thumb { width: 60px; height: 85px; border-radius: 8px; object-fit: cover; flex-shrink: 0; }
.top-details { flex: 1; }
.top-title { font-size: 1rem; font-weight: 700; margin-bottom: 0.3rem; }
.top-meta { font-size: 0.8rem; color: var(--text2); display: flex; gap: 0.75rem; }
.top-meta .rating { color: var(--gold); }

.footer { background: var(--bg2); border-top: 1px solid var(--border); padding: 2rem; text-align: center; color: var(--text3); font-size: 0.85rem; }
.loading { text-align: center; padding: 3rem; color: var(--text2); grid-column: 1/-1; }
.spinner { display: inline-block; width: 40px; height: 40px; border: 3px solid var(--surface2); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.95); backdrop-filter: blur(8px); z-index: 5000; display: none; align-items: flex-start; justify-content: center; padding: 2rem 1rem; overflow-y: auto; }
.modal-overlay.active { display: flex; }
.modal { background: var(--bg3); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 2rem; max-width: 1200px; width: 100%; position: relative; }
.modal-close { position: absolute; top: 1rem; left: 1rem; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); color: var(--text2); width: 40px; height: 40px; border-radius: 50%; font-size: 1.2rem; transition: all var(--transition); z-index: 10; }
.modal-close:hover { background: var(--accent); color: #fff; }

.player-container { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: var(--radius); overflow: hidden; margin-bottom: 1rem; position: relative; }
.player-container iframe { width: 100%; height: 100%; border: none; }
.player-status { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; padding: 0.75rem 1rem; background: var(--surface); border-radius: 8px; border: 1px solid var(--border); }
.player-status-info { display: flex; align-items: center; gap: 0.75rem; }
.quality-badge { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.25rem 0.7rem; border-radius: 6px; font-size: 0.72rem; font-weight: 700; }
.quality-badge.uhd { background: linear-gradient(135deg, #f5c518, #ff9800); color: #000; }
.quality-badge.hd { background: var(--green); color: #000; }
.quality-badge.sd { background: var(--surface2); color: var(--text2); }
.ads-badge { display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.72rem; padding: 0.25rem 0.7rem; border-radius: 6px; }
.ads-badge.none { background: rgba(34,197,94,0.15); color: var(--green); }
.ads-badge.low { background: rgba(245,197,24,0.15); color: var(--gold); }
.ads-badge.medium, .ads-badge.high { background: rgba(229,9,20,0.15); color: var(--accent2); }

.player-tabs { display: flex; gap: 0.4rem; margin-bottom: 1rem; flex-wrap: wrap; max-height: 140px; overflow-y: auto; padding: 0.5rem; background: var(--surface); border-radius: 8px; border: 1px solid var(--border); }
.player-tab { background: var(--bg3); border: 1px solid var(--border); color: var(--text2); padding: 0.4rem 0.8rem; border-radius: 6px; font-size: 0.72rem; font-weight: 600; transition: all var(--transition); white-space: nowrap; display: inline-flex; align-items: center; gap: 0.3rem; }
.player-tab.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.player-tab:hover:not(.active) { border-color: var(--accent); color: var(--accent); }
.player-tab .dot { width: 6px; height: 6px; border-radius: 50%; }
.player-tab .dot.green { background: var(--green); }
.player-tab .dot.gold { background: var(--gold); }
.player-tab .dot.red { background: var(--accent2); }

.movie-header { display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.movie-poster { width: 200px; flex-shrink: 0; border-radius: var(--radius); overflow: hidden; }
.movie-info { flex: 1; min-width: 250px; }
.movie-info h2 { font-size: 1.8rem; margin-bottom: 0.75rem; }
.movie-meta { display: flex; gap: 0.75rem; flex-wrap: wrap; color: var(--text2); font-size: 0.9rem; margin-bottom: 1rem; }
.movie-meta .rating { color: var(--gold); font-weight: 700; }
.movie-genres { color: var(--text2); font-size: 0.85rem; margin-bottom: 1rem; }
.movie-desc { color: var(--text2); line-height: 1.7; margin-bottom: 1rem; }

.seasons-section { margin-top: 1.5rem; }
.seasons-section h3 { font-size: 1.1rem; margin-bottom: 1rem; color: var(--text); }
.season-selector { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
.season-btn { background: var(--surface); border: 1px solid var(--border); color: var(--text2); padding: 0.4rem 0.9rem; border-radius: 6px; font-size: 0.85rem; transition: all var(--transition); cursor: pointer; }
.season-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.episodes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.75rem; }
.episode-btn { background: var(--surface); border: 1px solid var(--border); color: var(--text2); padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.85rem; text-align: right; transition: all var(--transition); cursor: pointer; }
.episode-btn:hover { background: var(--accent); border-color: var(--accent); color: #fff; }

@media (max-width: 900px) {
  .nav-links { display: none; }
  .nav-search input { width: 140px; }
  .section { padding: 2rem 1.5rem; }
  .hero-content { padding: 0 1.5rem; }
  .grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
  .modal { padding: 1rem; }
  .movie-poster { width: 100%; max-width: 200px; margin: 0 auto; }
}
</style>
</head>
<body>

<nav id="navbar">
  <div class="nav-container">
    <div class="nav-logo">ONYX <span>MOVIE</span></div>
    <ul class="nav-links">
      <li><a href="#trending-section" class="active">الرئيسية</a></li>
      <li><a href="#popular-section">الأفلام</a></li>
      <li><a href="#series-section">المسلسلات</a></li>
      <li><a href="#top-section">الأعلى تقييماً</a></li>
    </ul>
    <div class="nav-search">
      <input type="text" id="searchInput" placeholder="ابحث..." />
      <button onclick="doSearch()">🔍</button>
    </div>
  </div>
</nav>

<section class="hero">
  <div class="hero-bg" id="heroBg"></div>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-badge">🔥 الأكثر رواجاً الآن — جودة 4K</div>
    <h1 class="hero-title" id="heroTitle">جاري التحميل...</h1>
    <div class="hero-meta" id="heroMeta"></div>
    <p class="hero-desc" id="heroDesc"></p>
    <button class="btn-play" onclick="playHero()">▶ شاهد الآن</button>
  </div>
</section>

<section class="section" id="trending-section">
  <div class="section-header"><h2 class="section-title">🔥 الأكثر رواجاً</h2><span class="section-sub" id="trendingCount"></span></div>
  <div class="grid" id="trendingGrid"><div class="loading"><div class="spinner"></div><p>جاري التحميل...</p></div></div>
</section>

<section class="section" id="popular-section">
  <div class="section-header"><h2 class="section-title">🎬 أفلام شائعة</h2><span class="section-sub" id="popularCount"></span></div>
  <div class="grid" id="popularGrid"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section" id="top-section">
  <div class="section-header"><h2 class="section-title">⭐ الأعلى تقييماً</h2></div>
  <div class="top-list" id="topList"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section" id="series-section">
  <div class="section-header"><h2 class="section-title">📺 مسلسلات شائعة</h2><span class="section-sub" id="seriesCount"></span></div>
  <div class="grid" id="seriesGrid"><div class="loading"><div class="spinner"></div></div></div>
</section>

<footer class="footer">🚀 ONYX STUDIO — جميع الحقوق محفوظة</footer>

<div class="modal-overlay" id="movieModal" onclick="if(event.target.id==='movieModal') closeModal()">
  <div class="modal">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div id="modalContent"></div>
  </div>
</div>

<script>
// سيتم وضع JavaScript هنا في الرد 3
</script>

</body>
</html>
"""


# ══════════════════════════════════════════════════════════
# PLAYER PAGE
# ══════════════════════════════════════════════════════════

PLAYER_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 100%; height: 100%; background: #000; overflow: hidden; }
iframe { width: 100%; height: 100%; border: none; display: block; }
</style>
</head>
<body>
<iframe id="player" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture"></iframe>
<script>
const SOURCES = __SOURCES__;
const params = new URLSearchParams(window.location.search);
const type = params.get('type') || 'movie';
const id = params.get('id');
const sourceIdx = parseInt(params.get('source') || '0');
const season = params.get('season') || '1';
const episode = params.get('episode') || '1';

const src = SOURCES[sourceIdx];
if (src) {
  let url = src[type] || src.movie;
  url = url.replace('{id}', id).replace('{season}', season).replace('{episode}', episode);
  document.getElementById('player').src = url;
}
</script>
</body>
</html>
"""


# استبدال __SOURCES__ بـ JSON
INDEX_HTML = INDEX_HTML.replace('__SOURCES__', json.dumps(PLAYER_SOURCES, ensure_ascii=False))
PLAYER_HTML = PLAYER_HTML.replace('__SOURCES__', json.dumps(PLAYER_SOURCES, ensure_ascii=False))


# ══════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════

@app.route("/")
def index():
    return INDEX_HTML


@app.route("/player")
def player():
    return PLAYER_HTML


def tmdb_get(endpoint, params=None):
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY missing", "results": []}
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    params["language"] = "ar"
    url = f"{TMDB_BASE}{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


@app.route("/api/trending")
def api_trending():
    return jsonify(tmdb_get("/trending/all/week"))


@app.route("/api/popular/<media_type>")
def api_popular(media_type):
    return jsonify(tmdb_get(f"/{media_type}/popular"))


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    return jsonify(tmdb_get("/search/multi", {"query": q}))


@app.route("/api/movie/<int:movie_id>")
def api_movie(movie_id):
    return jsonify(tmdb_get(f"/movie/{movie_id}"))


@app.route("/api/tv/<int:tv_id>")
def api_tv(tv_id):
    return jsonify(tmdb_get(f"/tv/{tv_id}"))


@app.route("/api/tv/<int:tv_id>/season/<int:season_num>")
def api_tv_season(tv_id, season_num):
    return jsonify(tmdb_get(f"/tv/{tv_id}/season/{season_num}"))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "ONYX MOVIE", "sources": len(PLAYER_SOURCES)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)<script>
const IMG = 'https://image.tmdb.org/t/p';
const SOURCES = __SOURCES__;
let heroMovies = [];
let heroIndex = 0;
let currentMovie = { id: null, type: null };

/* ─── MOVIE CARD ─── */
function movieCard(m) {
  const title = m.title || m.name || '?';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
  const poster = m.poster_path
    ? IMG + '/w500' + m.poster_path
    : 'https://via.placeholder.com/300x450/161d30/5a6480?text=🎬';
  const type = m.media_type || (m.name ? 'tv' : 'movie');
  const isHD = m.vote_average >= 7.5;
  return '<div class="card" onclick="openMovie(' + m.id + ', \'' + type + '\')">' +
    '<img src="' + poster + '" alt="' + title + '" loading="lazy" onerror="this.src=\'https://via.placeholder.com/300x450/161d30/5a6480?text=🎬\'">' +
    (isHD ? '<div class="card-badge-hd green">HD</div>' : '') +
    '<div class="card-info">' +
      '<div class="card-title">' + title + '</div>' +
      '<div class="card-meta">' +
        '<span>' + year + '</span>' +
        '<span class="rating">⭐ ' + rating + '</span>' +
      '</div>' +
    '</div>' +
  '</div>';
}

/* ─── HERO ─── */
async function loadHero() {
  try {
    const res = await fetch('/api/trending');
    const data = await res.json();
    const results = (data.results || []).filter(m => m.backdrop_path).slice(0, 5);
    if (!results.length) return;
    heroMovies = results;
    const bg = document.getElementById('heroBg');
    bg.innerHTML = results.map((m, i) =>
      '<div class="hero-bg-slide ' + (i === 0 ? 'active' : '') + '" style="background-image:url(\'' + IMG + '/original' + m.backdrop_path + '\')"></div>'
    ).join('');
    renderHero(0);
    setInterval(() => {
      heroIndex = (heroIndex + 1) % heroMovies.length;
      document.querySelectorAll('.hero-bg-slide').forEach((s, i) => s.classList.toggle('active', i === heroIndex));
      renderHero(heroIndex);
    }, 7000);
  } catch (e) { console.error(e); }
}

function renderHero(i) {
  const m = heroMovies[i];
  if (!m) return;
  const title = m.title || m.name || '?';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
  const desc = m.overview || 'لا يوجد وصف';
  document.getElementById('heroTitle').textContent = title;
  document.getElementById('heroMeta').innerHTML =
    '<span>' + year + '</span>' +
    '<span class="rating">⭐ ' + rating + '</span>' +
    '<span>' + (m.media_type === 'tv' ? '📺 مسلسل' : '🎬 فيلم') + '</span>' +
    '<span style="color:#22c55e">✓ 4K متوفر</span>';
  document.getElementById('heroDesc').textContent = desc.substring(0, 220) + (desc.length > 220 ? '...' : '');
}

function playHero() {
  const m = heroMovies[heroIndex];
  if (m) openMovie(m.id, m.media_type || 'movie');
}

/* ─── LOAD SECTIONS ─── */
async function loadTrending() {
  const el = document.getElementById('trendingGrid');
  try {
    const res = await fetch('/api/trending');
    const data = await res.json();
    const results = (data.results || []).filter(m => m.poster_path);
    el.innerHTML = results.map(movieCard).join('') || '<div class="loading">لا توجد نتائج</div>';
    document.getElementById('trendingCount').textContent = results.length + ' عنصر';
  } catch (e) { el.innerHTML = '<div class="loading">❌ خطأ</div>'; }
}

async function loadPopular() {
  const el = document.getElementById('popularGrid');
  try {
    const res = await fetch('/api/popular/movie');
    const data = await res.json();
    const results = (data.results || []).filter(m => m.poster_path);
    el.innerHTML = results.map(movieCard).join('');
    document.getElementById('popularCount').textContent = results.length + ' فيلم';
  } catch (e) { el.innerHTML = '<div class="loading">❌</div>'; }
}

async function loadTopRated() {
  const el = document.getElementById('topList');
  try {
    const res = await fetch('/api/popular/movie');
    const data = await res.json();
    const results = (data.results || [])
      .filter(m => m.poster_path)
      .sort((a, b) => b.vote_average - a.vote_average)
      .slice(0, 10);
    el.innerHTML = results.map((m, i) => {
      const title = m.title || m.name || '?';
      const year = (m.release_date || '').substring(0, 4);
      const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
      const poster = IMG + '/w200' + m.poster_path;
      return '<div class="top-item" onclick="openMovie(' + m.id + ', \'movie\')">' +
        '<div class="top-rank">' + String(i + 1).padStart(2, '0') + '</div>' +
        '<img class="top-thumb" src="' + poster + '" alt="' + title + '">' +
        '<div class="top-details">' +
          '<div class="top-title">' + title + '</div>' +
          '<div class="top-meta"><span>' + year + '</span><span class="rating">⭐ ' + rating + '</span></div>' +
        '</div>' +
      '</div>';
    }).join('');
  } catch (e) { el.innerHTML = '<div class="loading">❌</div>'; }
}

async function loadSeries() {
  const el = document.getElementById('seriesGrid');
  try {
    const res = await fetch('/api/popular/tv');
    const data = await res.json();
    const results = (data.results || []).filter(m => m.poster_path);
    el.innerHTML = results.map(movieCard).join('');
    document.getElementById('seriesCount').textContent = results.length + ' مسلسل';
  } catch (e) { el.innerHTML = '<div class="loading">❌</div>'; }
}

/* ─── SEARCH ─── */
async function doSearch() {
  const q = document.getElementById('searchInput').value.trim();
  if (!q) return;
  const el = document.getElementById('trendingGrid');
  const title = document.querySelector('#trending-section .section-title');
  el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  title.textContent = '🔍 نتائج البحث: ' + q;
  document.getElementById('trending-section').scrollIntoView({ behavior: 'smooth' });
  try {
    const res = await fetch('/api/search?q=' + encodeURIComponent(q));
    const data = await res.json();
    const results = (data.results || []).filter(m => m.poster_path);
    el.innerHTML = results.map(movieCard).join('') || '<div class="loading">لا توجد نتائج لـ: ' + q + '</div>';
    document.getElementById('trendingCount').textContent = results.length + ' نتيجة';
  } catch (e) { el.innerHTML = '<div class="loading">❌ خطأ</div>'; }
}

/* ─── OPEN MOVIE ─── */
async function openMovie(id, type) {
  const modal = document.getElementById('movieModal');
  const content = document.getElementById('modalContent');
  content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
  currentMovie = { id: id, type: type };

  try {
    const res = await fetch('/api/' + type + '/' + id);
    const m = await res.json();
    const title = m.title || m.name || '?';
    const year = (m.release_date || m.first_air_date || '').substring(0, 4);
    const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
    const runtime = m.runtime || (m.episode_run_time && m.episode_run_time[0]) || '?';
    const poster = m.poster_path ? IMG + '/w500' + m.poster_path : '';
    const genres = (m.genres || []).map(g => g.name).join(' • ');
    const desc = m.overview || 'لا يوجد وصف متاح';

    let html = '';

    /* PLAYER */
    html += '<div class="player-container"><iframe id="playerFrame" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture"></iframe></div>';

    /* STATUS BAR */
    html += '<div class="player-status">' +
      '<div class="player-status-info">' +
        '<span id="statusQuality" class="quality-badge uhd">🎬 4K/HD</span>' +
        '<span id="statusAds" class="ads-badge none">✓ بدون إعلانات</span>' +
        '<span style="color:var(--text2);font-size:0.8rem" id="statusName">VidLink 4K</span>' +
      '</div>' +
      '<span style="color:var(--text2);font-size:0.75rem">' + SOURCES.length + ' مصدر متوفر</span>' +
    '</div>';

    /* PLAYER TABS (25 مصدر) */
    html += '<div class="player-tabs" id="playerTabs">';
    SOURCES.forEach((s, i) => {
      const dotClass = s.ads === 'none' ? 'green' : (s.ads === 'low' ? 'gold' : 'red');
      html += '<button class="player-tab' + (i === 0 ? ' active' : '') + '" onclick="switchSource(' + i + ')">' +
        '<span class="dot ' + dotClass + '"></span>' +
        s.name + ' <small style="opacity:0.7">(' + s.quality + ')</small>' +
      '</button>';
    });
    html += '</div>';

    /* MOVIE INFO */
    html += '<div class="movie-header">';
    html += '<div class="movie-poster"><img src="' + poster + '" alt="' + title + '"></div>';
    html += '<div class="movie-info">';
    html += '<h2>' + title + '</h2>';
    html += '<div class="movie-meta">';
    html += '<span class="rating">⭐ ' + rating + '/10</span>';
    html += '<span>📅 ' + year + '</span>';
    html += '<span>⏱️ ' + runtime + ' دقيقة</span>';
    html += '<span>' + (type === 'tv' ? '📺 مسلسل' : '🎬 فيلم') + '</span>';
    html += '</div>';
    if (genres) html += '<p class="movie-genres">🎭 ' + genres + '</p>';
    html += '<p class="movie-desc">' + desc + '</p>';
    html += '</div>';
    html += '</div>';

    /* SEASONS */
    if (type === 'tv' && m.seasons && m.seasons.length) {
      html += '<div class="seasons-section">';
      html += '<h3>📺 المواسم والحلقات</h3>';
      html += '<div class="season-selector" id="seasonSelector">';
      m.seasons.filter(s => s.season_number > 0).forEach(s => {
        html += '<button class="season-btn" data-season="' + s.season_number + '" onclick="changeSeason(this, ' + id + ', ' + s.season_number + ')">الموسم ' + s.season_number + '</button>';
      });
      html += '</div>';
      html += '<div class="episodes-grid" id="episodesGrid"></div>';
      html += '</div>';
    }

    content.innerHTML = html;

    /* Load first source (VidLink - 4K no ads) */
    loadPlayer(0);

    /* Load episodes for TV */
    if (type === 'tv') {
      const firstSeason = m.seasons.filter(s => s.season_number > 0)[0];
      if (firstSeason) {
        document.querySelector('.season-btn')?.classList.add('active');
        loadEpisodes(id, firstSeason.season_number);
      }
    }

  } catch (e) {
    content.innerHTML = '<div class="loading">❌ خطأ: ' + e.message + '</div>';
  }
}

/* ─── PLAYER ─── */
function loadPlayer(idx, season, episode) {
  const frame = document.getElementById('playerFrame');
  if (!frame) return;
  season = season || 1;
  episode = episode || 1;
  frame.src = '/player?type=' + currentMovie.type + '&id=' + currentMovie.id + '&source=' + idx + '&season=' + season + '&episode=' + episode;

  /* Update status */
  const s = SOURCES[idx];
  if (s) {
    const q = document.getElementById('statusQuality');
    const a = document.getElementById('statusAds');
    const n = document.getElementById('statusName');
    if (q) {
      q.textContent = '🎬 ' + s.quality;
      q.className = 'quality-badge ' + (s.quality === '4K' ? 'uhd' : s.quality === 'HD' ? 'hd' : 'sd');
    }
    if (a) {
      a.textContent = s.ads === 'none' ? '✓ بدون إعلانات' : s.ads === 'low' ? '⚠ إعلانات قليلة' : '⚠ إعلانات';
      a.className = 'ads-badge ' + s.ads;
    }
    if (n) n.textContent = s.name;
  }
}

function switchSource(idx) {
  document.querySelectorAll('.player-tab').forEach((t, i) => t.classList.toggle('active', i === idx));
  /* Get current season/episode if TV */
  const activeSeason = document.querySelector('.season-btn.active');
  const season = activeSeason ? activeSeason.dataset.season : 1;
  loadPlayer(idx, season, 1);
}

/* ─── EPISODES ─── */
async function loadEpisodes(tvId, seasonNum) {
  const el = document.getElementById('episodesGrid');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  try {
    const res = await fetch('/api/tv/' + tvId + '/season/' + seasonNum);
    const data = await res.json();
    const episodes = data.episodes || [];
    if (!episodes.length) {
      el.innerHTML = '<div class="loading">لا توجد حلقات</div>';
      return;
    }
    el.innerHTML = episodes.map(ep =>
      '<button class="episode-btn" onclick="playEpisode(' + tvId + ', ' + seasonNum + ', ' + ep.episode_number + ')">' +
        '<strong>حلقة ' + ep.episode_number + '</strong><br>' +
        '<span style="font-size:0.75rem;color:var(--text3)">' + (ep.name || '').substring(0, 40) + '</span>' +
      '</button>'
    ).join('');
  } catch (e) {
    el.innerHTML = '<div class="loading">❌ خطأ</div>';
  }
}

function changeSeason(btn, tvId, seasonNum) {
  document.querySelectorAll('.season-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadEpisodes(tvId, seasonNum);
  /* Reload player with new season */
  const activeTab = document.querySelector('.player-tab.active');
  const idx = Array.from(document.querySelectorAll('.player-tab')).indexOf(activeTab);
  loadPlayer(idx >= 0 ? idx : 0, seasonNum, 1);
}

function playEpisode(tvId, season, episode) {
  const activeTab = document.querySelector('.player-tab.active');
  const idx = Array.from(document.querySelectorAll('.player-tab')).indexOf(activeTab);
  loadPlayer(idx >= 0 ? idx : 0, season, episode);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ─── CLOSE MODAL ─── */
function closeModal() {
  document.getElementById('movieModal').classList.remove('active');
  document.body.style.overflow = '';
  const frame = document.getElementById('playerFrame');
  if (frame) frame.src = '';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
  if (e.key === 'Enter' && document.activeElement.id === 'searchInput') doSearch();
});

/* ─── INIT ─── */
document.addEventListener('DOMContentLoaded', () => {
  loadHero();
  loadTrending();
  loadPopular();
  loadTopRated();
  loadSeries();
});
</script>
