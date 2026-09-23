# -*- coding: utf-8 -*-
"""🎬 ONYX MOVIE — Flask Web App + TMDB API"""

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
# 🎬 HTML + CSS + JS (كل شي في ملف واحد)
# ══════════════════════════════════════════════════════════

INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>ONYX MOVIE — أفضل تجربة سينمائية</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet" />
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #080b14; --bg2: #0d1117; --bg3: #12172a;
  --surface: #161d30; --surface2: #1e2740;
  --accent: #e50914; --accent2: #ff4c54;
  --gold: #f5c518;
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

/* NAVBAR */
#navbar {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 1000; padding: 0 2rem; height: 70px;
  display: flex; align-items: center;
  background: rgba(8,11,20,0.95);
  backdrop-filter: blur(20px);
  box-shadow: 0 2px 40px rgba(0,0,0,0.5);
}
.nav-container { width: 100%; display: flex; align-items: center; gap: 2rem; max-width: 1600px; margin: 0 auto; }
.nav-logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.8rem; letter-spacing: 0.08em; flex-shrink: 0;
}
.nav-logo span { color: var(--accent); }
.nav-links { display: flex; gap: 0.25rem; flex: 1; justify-content: center; }
.nav-links a {
  padding: 0.5rem 1rem; border-radius: 8px;
  font-size: 0.9rem; font-weight: 600; color: var(--text2);
  transition: color var(--transition); cursor: pointer;
}
.nav-links a:hover, .nav-links a.active { color: var(--text); }
.nav-search {
  display: flex; align-items: center; flex-shrink: 0;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; overflow: hidden;
  transition: border-color var(--transition);
}
.nav-search:focus-within { border-color: var(--accent); }
.nav-search input {
  background: transparent; border: none; outline: none;
  color: var(--text); padding: 0.55rem 1rem;
  width: 240px; font-size: 0.85rem; font-family: var(--font);
}
.nav-search input::placeholder { color: var(--text3); }
.nav-search button {
  background: var(--accent); color: #fff;
  padding: 0.55rem 1rem; font-size: 0.85rem;
  font-weight: 700; transition: background var(--transition);
}
.nav-search button:hover { background: var(--accent2); }

/* HERO */
.hero {
  position: relative; height: 80vh; min-height: 500px;
  overflow: hidden; display: flex; align-items: center;
  margin-top: 70px;
}
.hero-bg { position: absolute; inset: 0; }
.hero-bg-slide {
  position: absolute; inset: 0;
  background-size: cover; background-position: center;
  opacity: 0; transition: opacity 1.2s ease;
}
.hero-bg-slide.active { opacity: 1; }
.hero-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(90deg, rgba(8,11,20,0.95) 0%, rgba(8,11,20,0.6) 50%, rgba(8,11,20,0.2) 100%), linear-gradient(0deg, rgba(8,11,20,1) 0%, transparent 40%);
}
.hero-content {
  position: relative; z-index: 2;
  max-width: 650px; padding: 0 4rem;
}
.hero-badge {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: rgba(229,9,20,0.15); border: 1px solid rgba(229,9,20,0.4);
  color: var(--accent2); font-size: 0.8rem; font-weight: 700;
  padding: 0.35rem 0.85rem; border-radius: 50px; margin-bottom: 1rem;
}
.hero-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: clamp(2.5rem, 6vw, 5rem); line-height: 1;
  letter-spacing: 0.04em; color: #fff;
  text-shadow: 0 4px 30px rgba(0,0,0,0.5); margin-bottom: 1rem;
}
.hero-meta {
  display: flex; align-items: center; gap: 1rem;
  color: var(--text2); font-size: 0.95rem; font-weight: 600;
  margin-bottom: 1rem; flex-wrap: wrap;
}
.hero-meta .rating { color: var(--gold); }
.hero-desc {
  color: var(--text2); font-size: 1rem; line-height: 1.7;
  max-width: 550px; margin-bottom: 2rem;
}
.btn-watch {
  display: inline-flex; align-items: center; gap: 0.6rem;
  background: var(--accent); color: #fff;
  padding: 0.85rem 2rem; border-radius: var(--radius);
  font-size: 1rem; font-weight: 700;
  transition: all var(--transition);
}
.btn-watch:hover {
  background: var(--accent2); box-shadow: var(--glow);
  transform: translateY(-2px);
}

/* SECTIONS */
.section { padding: 3rem 4rem; max-width: 1600px; margin: 0 auto; }
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1.75rem;
}
.section-title { font-size: 1.6rem; font-weight: 700; color: var(--text); }
.section-sub { font-size: 0.85rem; color: var(--text2); }

/* GRID */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1.25rem;
}
.card {
  position: relative; border-radius: var(--radius);
  overflow: hidden; background: var(--surface);
  transition: all var(--transition); cursor: pointer;
}
.card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 60px rgba(0,0,0,0.6);
  z-index: 2;
}
.card img {
  width: 100%; aspect-ratio: 2/3;
  object-fit: cover; display: block;
  background: var(--surface2);
  transition: transform var(--transition);
}
.card:hover img { transform: scale(1.05); }
.card-info { padding: 0.85rem; }
.card-title {
  font-size: 0.9rem; font-weight: 700;
  color: #fff; margin-bottom: 0.3rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.card-meta {
  font-size: 0.75rem; color: var(--text2);
  display: flex; gap: 0.5rem; flex-wrap: wrap;
}
.card-meta .rating { color: var(--gold); font-weight: 700; }

/* TOP LIST */
.top-list { display: flex; flex-direction: column; gap: 0.75rem; }
.top-item {
  display: flex; align-items: center; gap: 1.25rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 0.85rem 1.25rem;
  transition: all var(--transition); cursor: pointer;
}
.top-item:hover { background: var(--surface2); transform: translateX(-4px); }
.top-rank {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.8rem; color: var(--accent);
  width: 2.5rem; text-align: center; flex-shrink: 0;
}
.top-thumb {
  width: 60px; height: 85px;
  border-radius: 8px; object-fit: cover; flex-shrink: 0;
  background: var(--surface2);
}
.top-details { flex: 1; min-width: 0; }
.top-title { font-size: 1rem; font-weight: 700; margin-bottom: 0.3rem; }
.top-meta { font-size: 0.8rem; color: var(--text2); display: flex; gap: 0.75rem; }
.top-meta .rating { color: var(--gold); }

/* FOOTER */
.footer {
  background: var(--bg2); border-top: 1px solid var(--border);
  padding: 2rem; text-align: center;
  color: var(--text3); font-size: 0.85rem;
}

/* LOADING */
.loading {
  text-align: center; padding: 3rem;
  color: var(--text2); grid-column: 1/-1;
}
.spinner {
  display: inline-block; width: 40px; height: 40px;
  border: 3px solid var(--surface2);
  border-top-color: var(--accent);
  border-radius: 50%; animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* MODAL */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.85);
  backdrop-filter: blur(8px);
  z-index: 5000; display: none;
  align-items: center; justify-content: center;
  padding: 1rem;
}
.modal-overlay.active { display: flex; }
.modal {
  background: var(--bg3); border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 2rem; max-width: 800px;
  width: 100%; max-height: 90vh; overflow-y: auto;
  position: relative;
}
.modal-close {
  position: absolute; top: 1rem; left: 1rem;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  color: var(--text2); width: 36px; height: 36px;
  border-radius: 50%; font-size: 1rem;
  transition: all var(--transition);
}
.modal-close:hover { background: var(--accent); color: #fff; }
.modal-content { display: flex; gap: 2rem; flex-wrap: wrap; }
.modal-poster { width: 220px; flex-shrink: 0; }
.modal-poster img { width: 100%; border-radius: var(--radius); }
.modal-info { flex: 1; min-width: 250px; }
.modal-info h2 { font-size: 1.8rem; margin-bottom: 0.75rem; }
.modal-meta {
  display: flex; gap: 0.75rem; flex-wrap: wrap;
  color: var(--text2); font-size: 0.9rem; margin-bottom: 1rem;
}
.modal-meta .rating { color: var(--gold); }
.modal-desc { color: var(--text2); line-height: 1.7; margin-bottom: 1.5rem; }

/* RESPONSIVE */
@media (max-width: 900px) {
  .nav-links { display: none; }
  .nav-search input { width: 150px; }
  .section { padding: 2rem 1.5rem; }
  .hero-content { padding: 0 1.5rem; }
  .grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
  .modal-content { flex-direction: column; }
  .modal-poster { width: 100%; max-width: 250px; margin: 0 auto; }
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
      <input type="text" id="searchInput" placeholder="ابحث عن فيلم أو مسلسل..." />
      <button onclick="doSearch()">🔍 بحث</button>
    </div>
  </div>
</nav>

<section class="hero">
  <div class="hero-bg" id="heroBg"></div>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-badge">🔥 الأكثر رواجاً الآن</div>
    <h1 class="hero-title" id="heroTitle">جاري التحميل...</h1>
    <div class="hero-meta" id="heroMeta"></div>
    <p class="hero-desc" id="heroDesc"></p>
    <button class="btn-watch" onclick="watchHero()">▶ شاهد الآن</button>
  </div>
</section>

<section class="section" id="trending-section">
  <div class="section-header">
    <h2 class="section-title">🔥 الأكثر رواجاً</h2>
    <span class="section-sub" id="trendingCount"></span>
  </div>
  <div class="grid" id="trendingGrid">
    <div class="loading"><div class="spinner"></div><p>جاري التحميل...</p></div>
  </div>
</section>

<section class="section" id="popular-section">
  <div class="section-header">
    <h2 class="section-title">🎬 أفلام شائعة</h2>
    <span class="section-sub" id="popularCount"></span>
  </div>
  <div class="grid" id="popularGrid">
    <div class="loading"><div class="spinner"></div></div>
  </div>
</section>

<section class="section" id="top-section">
  <div class="section-header">
    <h2 class="section-title">⭐ الأعلى تقييماً</h2>
  </div>
  <div class="top-list" id="topList">
    <div class="loading"><div class="spinner"></div></div>
  </div>
</section>

<section class="section" id="series-section">
  <div class="section-header">
    <h2 class="section-title">📺 مسلسلات شائعة</h2>
    <span class="section-sub" id="seriesCount"></span>
  </div>
  <div class="grid" id="seriesGrid">
    <div class="loading"><div class="spinner"></div></div>
  </div>
</section>

<footer class="footer">
  🚀 ONYX STUDIO — جميع الحقوق محفوظة
</footer>

<div class="modal-overlay" id="movieModal" onclick="if(event.target.id==='movieModal') closeModal()">
  <div class="modal">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div id="modalContent"></div>
  </div>
</div>

<script>
const IMG = 'https://image.tmdb.org/t/p';
let heroMovies = [];
let heroIndex = 0;

/* ─── MOVIE CARD ─── */
function movieCard(m) {
  const title = m.title || m.name || '?';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
  const poster = m.poster_path
    ? IMG + '/w500' + m.poster_path
    : 'https://via.placeholder.com/300x450/161d30/5a6480?text=🎬';
  const type = m.media_type || (m.name ? 'tv' : 'movie');
  return '<div class="card" onclick="openMovie(' + m.id + ', \'' + type + '\')">' +
    '<img src="' + poster + '" alt="' + title + '" loading="lazy" onerror="this.src=\'https://via.placeholder.com/300x450/161d30/5a6480?text=🎬\'">' +
    '<div class="card-info">' +
      '<div class="card-title">' + title + '</div>' +
      '<div class="card-meta">' +
        '<span>' + year + '</span>' +
        '<span class="rating">⭐ ' + rating + '</span>' +
      '</div>' +
    '</div>' +
  '</div>';
}

/* ─── LOAD HERO ─── */
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
    '<span>' + (m.media_type === 'tv' ? '📺 مسلسل' : '🎬 فيلم') + '</span>';
  document.getElementById('heroDesc').textContent = desc.substring(0, 220) + (desc.length > 220 ? '...' : '');
}

function watchHero() {
  const m = heroMovies[heroIndex];
  if (m) openMovie(m.id, m.media_type || 'movie');
}

/* ─── LOAD TRENDING ─── */
async function loadTrending() {
  const el = document.getElementById('trendingGrid');
  try {
    const res = await fetch('/api/trending');
    const data = await res.json();
    const results = (data.results || []).filter(m => m.poster_path);
    el.innerHTML = results.map(movieCard).join('') || '<div class="loading">لا توجد نتائج</div>';
    document.getElementById('trendingCount').textContent = results.length + ' عنصر';
  } catch (e) {
    el.innerHTML = '<div class="loading">❌ خطأ في التحميل</div>';
  }
}

/* ─── LOAD POPULAR ─── */
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

/* ─── LOAD TOP RATED ─── */
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

/* ─── LOAD SERIES ─── */
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
  if (!q) {
    alert('اكتب كلمة البحث');
    return;
  }
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
  } catch (e) { el.innerHTML = '<div class="loading">❌ خطأ في البحث</div>'; }
}

/* ─── OPEN MOVIE DETAIL ─── */
async function openMovie(id, type) {
  const modal = document.getElementById('movieModal');
  const content = document.getElementById('modalContent');
  content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  modal.classList.add('active');
  try {
    const res = await fetch('/api/' + type + '/' + id);
    const m = await res.json();
    const title = m.title || m.name || '?';
    const year = (m.release_date || m.first_air_date || '').substring(0, 4);
    const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
    const runtime = m.runtime || (m.episode_run_time && m.episode_run_time[0]) || '?';
    const poster = m.poster_path ? IMG + '/w500' + m.poster_path : '';
    const genres = (m.genres || []).map(g => g.name).join(' • ');
    content.innerHTML = '<div class="modal-content">' +
      '<div class="modal-poster"><img src="' + poster + '" alt="' + title + '"></div>' +
      '<div class="modal-info">' +
        '<h2>' + title + '</h2>' +
        '<div class="modal-meta">' +
          '<span class="rating">⭐ ' + rating + '/10</span>' +
          '<span>📅 ' + year + '</span>' +
          '<span>⏱️ ' + runtime + ' دقيقة</span>' +
          '<span>' + (type === 'tv' ? '📺 مسلسل' : '🎬 فيلم') + '</span>' +
        '</div>' +
        '<p style="color:var(--text2);margin-bottom:1rem;font-size:0.85rem">' + genres + '</p>' +
        '<p class="modal-desc">' + (m.overview || 'لا يوجد وصف متاح') + '</p>' +
        '<button class="btn-watch" onclick="alert(\'🎬 جاري تشغيل: ' + title.replace(/'/g, '') + '\')">▶ شاهد الآن</button>' +
      '</div>' +
    '</div>';
  } catch (e) {
    content.innerHTML = '<div class="loading">❌ خطأ في التحميل</div>';
  }
}

function closeModal() {
  document.getElementById('movieModal').classList.remove('active');
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

</body>
</html>
"""


# ══════════════════════════════════════════════════════════
# 🎯 ROUTES
# ══════════════════════════════════════════════════════════

@app.route("/")
def index():
    return INDEX_HTML


def tmdb_get(endpoint, params=None):
    """جلب من TMDB"""
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
    """كل الأفلام الرائجة"""
    return jsonify(tmdb_get("/trending/all/week"))


@app.route("/api/popular/<media_type>")
def api_popular(media_type):
    """كل الأفلام/المسلسلات الشائعة"""
    return jsonify(tmdb_get(f"/{media_type}/popular"))


@app.route("/api/search")
def api_search():
    """بحث"""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    return jsonify(tmdb_get("/search/multi", {"query": q}))


@app.route("/api/movie/<int:movie_id>")
def api_movie(movie_id):
    """تفاصيل فيلم"""
    return jsonify(tmdb_get(f"/movie/{movie_id}"))


@app.route("/api/tv/<int:tv_id>")
def api_tv(tv_id):
    """تفاصيل مسلسل"""
    return jsonify(tmdb_get(f"/tv/{tv_id}"))


@app.route("/api/genre")
def api_genre():
    """حسب التصنيف"""
    media_type = request.args.get("type", "movie")
    genre_id = request.args.get("id", "28")
    return jsonify(tmdb_get(f"/discover/{media_type}", {
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
    }))


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ONYX MOVIE",
        "tmdb": "✅" if TMDB_API_KEY else "❌",
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
