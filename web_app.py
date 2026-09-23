# -*- -*- coding: utf-8 -*-
"""ONYX MOVIE — Flask + TMDB + Bilingual UI (AR/EN)"""

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
# المصدر الرئيسي المباشر (VidLink 4K)
# ══════════════════════════════════════════════════════════

PLAYER_SOURCES = [
    {"name": "", "quality": "4K", "ads": "none",
     "movie": "https://vidlink.pro/movie/{id}?primaryColor=e50914&autoplay=true",
     "tv":    "https://vidlink.pro/tv/{id}/{season}/{episode}?primaryColor=e50914&autoplay=true"}
]

SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)


# ══════════════════════════════════════════════════════════
# HTML — الصفحة الرئيسية
# ══════════════════════════════════════════════════════════

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl" id="htmlTag">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>ONYX MOVIE</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&family=Bebas+Neue&family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet" />
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #141414; --bg2: #181818; --bg3: #1f1f1f;
  --surface: #242424; --surface2: #2f2f2f;
  --accent: #e50914; --accent2: #ff1e27;
  --gold: #f5c518; --green: #22c55e;
  --text: #f0f0f0; --text2: #aaaaaa; --text3: #666666;
  --border: rgba(255,255,255,0.1);
  --radius: 6px; --radius-lg: 12px;
  --transition: 0.3s cubic-bezier(0.4,0,0.2,1);
  --font: 'Cairo', 'Inter', sans-serif;
}

html { scroll-behavior: smooth; font-size: 16px; }
body { background: var(--bg); color: var(--text); font-family: var(--font); overflow-x: hidden; }
a { text-decoration: none; color: inherit; }
img { max-width: 100%; display: block; }
button { cursor: pointer; font-family: var(--font); border: none; }
input { font-family: var(--font); }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 4px; }

#navbar {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 1000; padding: 0 4%; height: 68px;
  display: flex; align-items: center;
  background: linear-gradient(180deg, rgba(0,0,0,0.9) 0%, transparent 100%);
  transition: background var(--transition);
}
#navbar.scrolled { background: #141414; box-shadow: 0 2px 20px rgba(0,0,0,0.8); }
.nav-container { width: 100%; display: flex; align-items: center; gap: 2rem; max-width: 1600px; margin: 0 auto; }
.nav-logo { font-family: 'Bebas Neue', sans-serif; font-size: 2.2rem; letter-spacing: 0.08em; flex-shrink: 0; color: var(--accent); }
.nav-links { display: flex; gap: 1rem; flex: 1; list-style: none; }
.nav-links a { padding: 0.5rem 0.8rem; font-size: 0.9rem; font-weight: 600; color: var(--text2); transition: color var(--transition); cursor: pointer; }
.nav-links a:hover, .nav-links a.active { color: var(--text); }
.lang-btn { background: var(--surface2); color: var(--text); padding: 0.4rem 0.8rem; border-radius: var(--radius); font-weight: 700; font-size: 0.8rem; border: 1px solid var(--border); }
.nav-search { display: flex; align-items: center; flex-shrink: 0; background: rgba(0,0,0,0.75); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.nav-search:focus-within { border-color: var(--accent); }
.nav-search input { background: transparent; border: none; outline: none; color: var(--text); padding: 0.5rem 1rem; width: 200px; font-size: 0.85rem; }
.nav-search input::placeholder { color: var(--text3); }
.nav-search button { background: var(--accent); color: #fff; padding: 0.5rem 1rem; font-size: 0.85rem; font-weight: 700; }

.hero { position: relative; height: 80vh; min-height: 520px; overflow: hidden; display: flex; align-items: center; }
.hero-bg { position: absolute; inset: 0; }
.hero-bg-slide { position: absolute; inset: 0; background-size: cover; background-position: center; opacity: 0; transition: opacity 1.2s ease; }
.hero-bg-slide.active { opacity: 1; }
.hero-overlay { position: absolute; inset: 0; background: linear-gradient(90deg, #141414 0%, rgba(20,20,20,0.6) 50%, transparent 100%), linear-gradient(0deg, #141414 0%, transparent 40%); }
html[dir="ltr"] .hero-overlay { background: linear-gradient(270deg, #141414 0%, rgba(20,20,20,0.6) 50%, transparent 100%), linear-gradient(0deg, #141414 0%, transparent 40%); }
.hero-content { position: relative; z-index: 2; max-width: 650px; padding: 0 4%; }
.hero-badge { display: inline-block; background: var(--accent); color: #fff; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.75rem; border-radius: var(--radius); margin-bottom: 1rem; }
.hero-title { font-size: clamp(2.5rem, 5vw, 4rem); font-weight: 900; line-height: 1.1; color: #fff; margin-bottom: 1rem; }
.hero-meta { display: flex; align-items: center; gap: 1rem; color: var(--text2); font-size: 0.95rem; font-weight: 600; margin-bottom: 1rem; flex-wrap: wrap; }
.hero-meta .rating { color: var(--gold); }
.hero-desc { color: var(--text2); font-size: 0.95rem; line-height: 1.6; max-width: 550px; margin-bottom: 1.5rem; }
.btn-play { display: inline-flex; align-items: center; gap: 0.5rem; background: #fff; color: #000; padding: 0.75rem 2rem; border-radius: var(--radius); font-size: 1rem; font-weight: 700; transition: all var(--transition); }
.btn-play:hover { background: rgba(255,255,255,0.8); transform: scale(1.03); }

.section { padding: 2rem 4%; max-width: 1600px; margin: 0 auto; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
.section-title { font-size: 1.4rem; font-weight: 700; }
.section-sub { font-size: 0.85rem; color: var(--text2); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 1rem; }
.card { position: relative; border-radius: var(--radius); overflow: hidden; background: var(--surface); transition: transform 0.3s ease; cursor: pointer; }
.card:hover { transform: scale(1.05); z-index: 5; box-shadow: 0 10px 30px rgba(0,0,0,0.8); }
.card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; background: var(--surface2); }
.card-info { padding: 0.75rem; }
.card-title { font-size: 0.85rem; font-weight: 700; color: #fff; margin-bottom: 0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-meta { font-size: 0.75rem; color: var(--text2); display: flex; gap: 0.5rem; flex-wrap: wrap; }
.card-meta .rating { color: var(--gold); font-weight: 700; }

.top-list { display: flex; flex-direction: column; gap: 0.75rem; }
.top-item { display: flex; align-items: center; gap: 1.25rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 0.75rem 1.25rem; transition: all var(--transition); cursor: pointer; }
.top-item:hover { background: var(--surface2); }
.top-rank { font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem; color: var(--accent); width: 2.5rem; text-align: center; flex-shrink: 0; }
.top-thumb { width: 55px; height: 80px; border-radius: 4px; object-fit: cover; flex-shrink: 0; }
.top-details { flex: 1; }
.top-title { font-size: 0.95rem; font-weight: 700; margin-bottom: 0.2rem; }
.top-meta { font-size: 0.8rem; color: var(--text2); display: flex; gap: 0.75rem; }
.top-meta .rating { color: var(--gold); }

.footer { background: var(--bg2); border-top: 1px solid var(--border); padding: 2rem; text-align: center; color: var(--text3); font-size: 0.85rem; margin-top: 3rem; }
.loading { text-align: center; padding: 3rem; color: var(--text2); grid-column: 1/-1; }
.spinner { display: inline-block; width: 36px; height: 36px; border: 3px solid var(--surface2); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }

/* FULLSCREEN MODAL DESIGN */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.95); backdrop-filter: blur(10px); z-index: 5000; display: none; align-items: flex-start; justify-content: center; padding: 1.5rem; overflow-y: auto; }
.modal-overlay.active { display: flex; }
.modal { background: #181818; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 2.5rem; width: 95%; max-width: 1400px; position: relative; margin: auto; }
.modal-close { position: absolute; top: 1.2rem; left: 1.2rem; background: var(--surface2); color: var(--text2); border: none; width: 40px; height: 40px; border-radius: 50%; font-size: 1.2rem; z-index: 10; transition: background 0.2s; }
html[dir="ltr"] .modal-close { left: auto; right: 1.2rem; }
.modal-close:hover { background: var(--accent); color: #fff; }

.player-wrapper { width: 100%; display: none; margin-bottom: 2rem; }
.player-wrapper.active { display: block; }
.player-container { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: var(--radius); overflow: hidden; }
.player-container iframe { width: 100%; height: 100%; border: none; }

.movie-header { display: flex; gap: 2.5rem; align-items: flex-start; margin-bottom: 2rem; flex-wrap: wrap; }
.movie-poster { width: 240px; flex-shrink: 0; border-radius: var(--radius); overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.8); }
.movie-info { flex: 1; min-width: 300px; }
.movie-info h2 { font-size: 2.4rem; margin-bottom: 0.8rem; font-weight: 800; line-height: 1.2; }
.movie-meta { display: flex; gap: 1rem; flex-wrap: wrap; color: var(--text2); font-size: 0.95rem; margin-bottom: 1.2rem; align-items: center; }
.movie-meta .rating { color: var(--gold); font-weight: 700; background: rgba(245, 197, 24, 0.1); padding: 0.2rem 0.6rem; border-radius: 4px; }
.movie-genres { color: var(--text2); font-size: 0.9rem; margin-bottom: 1.2rem; }
.movie-desc { color: var(--text2); line-height: 1.7; font-size: 0.95rem; margin-bottom: 1.5rem; max-width: 850px; }

.btn-watch-now { background: var(--accent); color: #fff; border: none; padding: 0.85rem 2.5rem; border-radius: var(--radius); font-size: 1.1rem; font-weight: 800; display: inline-flex; align-items: center; gap: 0.5rem; transition: background 0.2s, transform 0.2s; margin-top: 0.5rem; }
.btn-watch-now:hover { background: var(--accent2); transform: scale(1.03); }

/* CAST SECTION */
.cast-section { margin-top: 2rem; border-top: 1px solid var(--border); padding-top: 2rem; }
.cast-section h3 { font-size: 1.3rem; margin-bottom: 1.2rem; font-weight: 700; }
.cast-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 1rem; }
.cast-card { background: var(--surface); border-radius: var(--radius); overflow: hidden; text-align: center; padding-bottom: 0.6rem; }
.cast-card img { width: 100%; aspect-ratio: 1/1; object-fit: cover; background: var(--surface2); }
.cast-name { font-size: 0.8rem; font-weight: 700; margin-top: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 0.3rem; }
.cast-role { font-size: 0.7rem; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 0.3rem; }

.seasons-section { margin-top: 2rem; border-top: 1px solid var(--border); padding-top: 2rem; }
.seasons-section h3 { font-size: 1.2rem; margin-bottom: 1rem; }
.season-selector { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
.season-btn { background: var(--surface); border: 1px solid var(--border); color: var(--text2); padding: 0.5rem 1.1rem; border-radius: 4px; font-size: 0.9rem; }
.season-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.episodes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.75rem; }
.episode-btn { background: var(--surface); border: 1px solid var(--border); color: var(--text2); padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.85rem; }
</style>
</head>
<body>

<nav id="navbar">
  <div class="nav-container">
    <div class="nav-logo">ONYX</div>
    <ul class="nav-links">
      <li><a href="#trending-section" class="active" id="navHome">الرئيسية</a></li>
      <li><a href="#popular-section" id="navMovies">الأفلام</a></li>
      <li><a href="#series-section" id="navSeries">المسلسلات</a></li>
      <li><a href="#top-section" id="navTop">الأعلى تقييماً</a></li>
    </ul>
    <button class="lang-btn" onclick="toggleLanguage()" id="langBtn">EN</button>
    <div class="nav-search">
      <input type="text" id="searchInput" placeholder="ابحث عن فيلم أو مسلسل..." />
      <button onclick="doSearch()" id="searchBtn">بحث</button>
    </div>
  </div>
</nav>

<section class="hero">
  <div class="hero-bg" id="heroBg"></div>
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-badge" id="heroBadge">الأكثر رواجاً — جودة 4K</div>
    <h1 class="hero-title" id="heroTitle">جاري التحميل...</h1>
    <div class="hero-meta" id="heroMeta"></div>
    <p class="hero-desc" id="heroDesc"></p>
    <button class="btn-play" onclick="playHero()" id="heroPlayBtn">مشاهدة الآن</button>
  </div>
</section>

<section class="section" id="trending-section">
  <div class="section-header"><h2 class="section-title" id="titleTrending">الأكثر رواجاً</h2><span class="section-sub" id="trendingCount"></span></div>
  <div class="grid" id="trendingGrid"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section" id="popular-section">
  <div class="section-header"><h2 class="section-title" id="titlePopular">الأفلام الشائعة</h2><span class="section-sub" id="popularCount"></span></div>
  <div class="grid" id="popularGrid"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section" id="top-section">
  <div class="section-header"><h2 class="section-title" id="titleTop">الأعلى تقييماً</h2></div>
  <div class="top-list" id="topList"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section" id="series-section">
  <div class="section-header"><h2 class="section-title" id="titleSeries">المسلسلات الشائعة</h2><span class="section-sub" id="seriesCount"></span></div>
  <div class="grid" id="seriesGrid"><div class="loading"><div class="spinner"></div></div></div>
</section>

<footer class="footer">ONYX STUDIO — جميع الحقوق محفوظة</footer>

<div class="modal-overlay" id="movieModal" onclick="if(event.target.id==='movieModal') closeModal()">
  <div class="modal">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div id="modalContent"></div>
  </div>
</div>

<script>
const IMG = 'https://image.tmdb.org/t/p';
const SOURCES = __SOURCES__;
let currentLang = 'ar';
let heroMovies = [];
let heroIndex = 0;
let currentMovie = { id: null, type: null };

const I18N = {
  ar: {
    home: "الرئيسية", movies: "الأفلام", series: "المسلسلات", top: "الأعلى تقييماً",
    searchPh: "ابحث عن فيلم أو مسلسل...", searchBtn: "بحث",
    badge: "الأكثر رواجاً — جودة 4K", watchNow: "مشاهدة الآن",
    trending: "الأكثر رواجاً", popular: "الأفلام الشائعة", topTitle: "الأعلى تقييماً", seriesTitle: "المسلسلات الشائعة",
    rating: "تقييم", castTitle: "طاقم التمثيل", seasonsTitle: "المواسم والحلقات", season: "الموسم", episode: "حلقة"
  },
  en: {
    home: "Home", movies: "Movies", series: "TV Series", top: "Top Rated",
    searchPh: "Search movies or shows...", searchBtn: "Search",
    badge: "Trending — 4K Quality", watchNow: "Watch Now",
    trending: "Trending Now", popular: "Popular Movies", topTitle: "Top Rated", seriesTitle: "Popular TV Series",
    rating: "Rating", castTitle: "Cast & Characters", seasonsTitle: "Seasons & Episodes", season: "Season", episode: "Episode"
  }
};

function toggleLanguage() {
  currentLang = currentLang === 'ar' ? 'en' : 'ar';
  const html = document.getElementById('htmlTag');
  html.lang = currentLang;
  html.dir = currentLang === 'ar' ? 'rtl' : 'ltr';
  document.getElementById('langBtn').textContent = currentLang === 'ar' ? 'EN' : 'AR';

  const t = I18N[currentLang];
  document.getElementById('navHome').textContent = t.home;
  document.getElementById('navMovies').textContent = t.movies;
  document.getElementById('navSeries').textContent = t.series;
  document.getElementById('navTop').textContent = t.top;
  document.getElementById('searchInput').placeholder = t.searchPh;
  document.getElementById('searchBtn').textContent = t.searchBtn;
  document.getElementById('heroBadge').textContent = t.badge;
  document.getElementById('heroPlayBtn').textContent = t.watchNow;
  document.getElementById('titleTrending').textContent = t.trending;
  document.getElementById('titlePopular').textContent = t.popular;
  document.getElementById('titleTop').textContent = t.topTitle;
  document.getElementById('titleSeries').textContent = t.seriesTitle;

  reloadAll();
}

function movieCard(m) {
  const title = m.title || m.name || '?';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
  const poster = m.poster_path ? IMG + '/w500' + m.poster_path : 'https://via.placeholder.com/300x450/242424/aaaaaa?text=ONYX';
  const type = m.media_type || (m.name ? 'tv' : 'movie');
  const t = I18N[currentLang];
  return '<div class="card" onclick="openMovie(' + m.id + ', \'' + type + '\')">' +
    '<img src="' + poster + '" alt="' + title + '" loading="lazy">' +
    '<div class="card-info"><div class="card-title">' + title + '</div>' +
    '<div class="card-meta"><span>' + year + '</span><span class="rating">' + t.rating + ' ' + rating + '</span></div></div></div>';
}

async function loadHero() {
  try {
    const res = await fetch('/api/trending?lang=' + currentLang);
    const data = await res.json();
    heroMovies = (data.results || []).filter(m => m.backdrop_path).slice(0, 5);
    if (!heroMovies.length) return;
    const bg = document.getElementById('heroBg');
    bg.innerHTML = heroMovies.map((m, i) =>
      '<div class="hero-bg-slide ' + (i === 0 ? 'active' : '') + '" style="background-image:url(\'' + IMG + '/original' + m.backdrop_path + '\')"></div>'
    ).join('');
    renderHero(0);
  } catch (e) {}
}

function renderHero(i) {
  const m = heroMovies[i];
  if (!m) return;
  const t = I18N[currentLang];
  document.getElementById('heroTitle').textContent = m.title || m.name || '?';
  document.getElementById('heroMeta').innerHTML = '<span>' + ((m.release_date || m.first_air_date || '').substring(0, 4)) + '</span><span class="rating">' + t.rating + ' ' + (m.vote_average ? m.vote_average.toFixed(1) : '?') + '</span>';
  document.getElementById('heroDesc').textContent = (m.overview || '').substring(0, 200) + '...';
}

function playHero() {
  const m = heroMovies[heroIndex];
  if (m) openMovie(m.id, m.media_type || 'movie');
}

async function loadSection(url, gridId, countId) {
  const el = document.getElementById(gridId);
  try {
    const res = await fetch(url + '?lang=' + currentLang);
    const data = await res.json();
    const results = (data.results || []).filter(m => m.poster_path);
    el.innerHTML = results.map(movieCard).join('');
    if (countId) document.getElementById(countId).textContent = results.length;
  } catch (e) { el.innerHTML = ''; }
}

async function openMovie(id, type) {
  const modal = document.getElementById('movieModal');
  const content = document.getElementById('modalContent');
  content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
  currentMovie = { id: id, type: type };

  try {
    const res = await fetch('/api/' + type + '/' + id + '?lang=' + currentLang);
    const m = await res.json();
    const creditsRes = await fetch('/api/' + type + '/' + id + '/credits?lang=' + currentLang);
    const credits = await creditsRes.json();

    const title = m.title || m.name || '?';
    const year = (m.release_date || m.first_air_date || '').substring(0, 4);
    const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
    const runtime = m.runtime || (m.episode_run_time && m.episode_run_time[0]) || '?';
    const poster = m.poster_path ? IMG + '/w500' + m.poster_path : '';
    const genres = (m.genres || []).map(g => g.name).join(' • ');
    const desc = m.overview || '';
    const t = I18N[currentLang];

    let html = '<div class="player-wrapper" id="playerWrapper"><div class="player-container"><iframe id="playerFrame" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen"></iframe></div></div>';

    html += '<div class="movie-header">';
    html += '<div class="movie-poster"><img src="' + poster + '" alt="' + title + '"></div>';
    html += '<div class="movie-info">';
    html += '<h2>' + title + '</h2>';
    html += '<div class="movie-meta"><span class="rating">' + t.rating + ' ' + rating + '/10</span><span>' + year + '</span><span>' + runtime + ' min</span></div>';
    if (genres) html += '<p class="movie-genres">' + genres + '</p>';
    html += '<p class="movie-desc">' + desc + '</p>';
    html += '<button class="btn-watch-now" onclick="startStreaming(0, 1, 1)">' + t.watchNow + '</button>';
    html += '</div></div>';

    if (credits.cast && credits.cast.length) {
      html += '<div class="cast-section"><h3>' + t.castTitle + '</h3><div class="cast-grid">';
      credits.cast.slice(0, 8).forEach(c => {
        const photo = c.profile_path ? IMG + '/w185' + c.profile_path : 'https://via.placeholder.com/150/2f2f2f/ffffff?text=Actor';
        html += '<div class="cast-card"><img src="' + photo + '"><div class="cast-name">' + c.name + '</div><div class="cast-role">' + (c.character || '') + '</div></div>';
      });
      html += '</div></div>';
    }

    if (type === 'tv' && m.seasons) {
      html += '<div class="seasons-section"><h3>' + t.seasonsTitle + '</h3><div class="season-selector">';
      m.seasons.filter(s => s.season_number > 0).forEach(s => {
        html += '<button class="season-btn" onclick="changeSeason(this, ' + id + ', ' + s.season_number + ')">' + t.season + ' ' + s.season_number + '</button>';
      });
      html += '</div><div class="episodes-grid" id="episodesGrid"></div></div>';
    }

    content.innerHTML = html;
  } catch (e) {}
}

function startStreaming(idx, season, episode) {
  const wrapper = document.getElementById('playerWrapper');
  const frame = document.getElementById('playerFrame');
  frame.src = '/player?type=' + currentMovie.type + '&id=' + currentMovie.id + '&source=0&season=' + (season||1) + '&episode=' + (episode||1);
  wrapper.classList.add('active');
  wrapper.scrollIntoView({ behavior: 'smooth' });
}

function closeModal() {
  document.getElementById('movieModal').classList.remove('active');
  document.body.style.overflow = '';
  document.getElementById('playerFrame').src = '';
}

function reloadAll() {
  loadHero();
  loadSection('/api/trending', 'trendingGrid', 'trendingCount');
  loadSection('/api/popular/movie', 'popularGrid', 'popularCount');
  loadSection('/api/popular/tv', 'seriesGrid', 'seriesCount');
}

document.addEventListener('DOMContentLoaded', reloadAll);
</script>
</body>
</html>
"""

INDEX_HTML = INDEX_HTML.replace('__SOURCES__', SOURCES_JSON)


# ══════════════════════════════════════════════════════════
# PLAYER PAGE
# ══════════════════════════════════════════════════════════

PLAYER_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* { margin: 0; padding: 0; }
html, body, iframe { width: 100%; height: 100%; background: #000; border: none; overflow: hidden; }
</style>
</head>
<body>
<iframe id="player" src="" allowfullscreen allow="autoplay; encrypted-media"></iframe>
<script>
const SOURCES = __SOURCES__;
const params = new URLSearchParams(window.location.search);
const type = params.get('type') || 'movie';
const id = params.get('id');
const season = params.get('season') || '1';
const episode = params.get('episode') || '1';

const src = SOURCES[0];
if (src) {
  let url = src[type] || src.movie;
  url = url.replace('{id}', id).replace('{season}', season).replace('{episode}', episode);
  document.getElementById('player').src = url;
}
</script>
</body>
</html>
"""

PLAYER_HTML = PLAYER_HTML.replace('__SOURCES__', SOURCES_JSON)


# ══════════════════════════════════════════════════════════
# ROUTES (Backend Handling Both AR and EN)
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
    
    # تحديد اللغة بناءً على خيار المستخدم
    lang = request.args.get("lang", "ar")
    params["language"] = "en-US" if lang == "en" else "ar"
    
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

@app.route("/api/movie/<int:movie_id>")
def api_movie(movie_id):
    return jsonify(tmdb_get(f"/movie/{movie_id}"))

@app.route("/api/tv/<int:tv_id>")
def api_tv(tv_id):
    return jsonify(tmdb_get(f"/tv/{tv_id}"))

@app.route("/api/<media_type>/<int:item_id>/credits")
def api_credits(media_type, item_id):
    return jsonify(tmdb_get(f"/{media_type}/{item_id}/credits"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
