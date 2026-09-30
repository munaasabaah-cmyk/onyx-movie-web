# -*- coding: utf-8 -*-
"""
ONYX CINEMA v13.5 - Flask + Discord Bot + TMDB + Multi Sources
Complete single-file with embedded full UI
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
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"
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
    ("VidSrcXYZ", "https://vidsrc.xyz/embed/movie?tmdb={id}", "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrcME", "https://vidsrc.me/embed/movie?tmdb={id}", "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrcCC", "https://vidsrc.cc/v2/embed/movie/{id}", "https://vidsrc.cc/v2/embed/tv/{id}/{s}/{e}"),
    ("VidSrcNET", "https://vidsrc.net/embed/movie/{id}", "https://vidsrc.net/embed/tv/{id}/{s}/{e}"),
    ("VidSrcIN", "https://vidsrc.in/embed/movie/{id}", "https://vidsrc.in/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPM", "https://vidsrc.pm/embed/movie/{id}", "https://vidsrc.pm/embed/tv/{id}/{s}/{e}"),
    ("2Embed", "https://www.2embed.to/embed/tmdb/movie?id={id}", "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("EmbedSU", "https://embed.su/embed/movie/{id}", "https://embed.su/embed/tv/{id}/{s}/{e}"),
    ("MultiEmbed", "https://multiembed.mov/?video_id={id}&tmdb=1", "https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("VidPlus", "https://vidplus.to/embed/movie/{id}", "https://vidplus.to/embed/tv/{id}/{s}/{e}"),
    ("VidCloud", "https://vidcloud.stream/movie/{id}", "https://vidcloud.stream/tv/{id}/{s}/{e}"),
    ("VidPlay", "https://vidplay.site/movie/{id}", "https://vidplay.site/tv/{id}/{s}/{e}"),
    ("VidFast", "https://vidfast.pro/movie/{id}", "https://vidfast.pro/tv/{id}/{s}/{e}"),
    ("VidEasy", "https://videasy.net/movie/{id}", "https://videasy.net/tv/{id}/{s}/{e}"),
    ("VidSrcPRO", "https://vidsrc.pro/embed/movie/{id}", "https://vidsrc.pro/embed/tv/{id}/{s}/{e}"),
    ("VidSrcVIP", "https://vidsrc.vip/embed/movie/{id}", "https://vidsrc.vip/embed/tv/{id}/{s}/{e}"),
    ("VidSrcICU", "https://vidsrc.icu/embed/movie/{id}", "https://vidsrc.icu/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWATCH", "https://vidsrc.watch/embed/movie/{id}", "https://vidsrc.watch/embed/tv/{id}/{s}/{e}"),
    ("VidSrcFUN", "https://vidsrc.fun/embed/movie/{id}", "https://vidsrc.fun/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPLUS", "https://vidsrc.plus/embed/movie/{id}", "https://vidsrc.plus/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHD", "https://vidsrchd.me/embed/movie/{id}", "https://vidsrchd.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc4K", "https://vidsrc4k.me/embed/movie/{id}", "https://vidsrc4k.me/embed/tv/{id}/{s}/{e}"),
]

QUALITY_VARIANTS = ["4K", "HD", "SD"]


def build_sources():
    sources = []
    for name, movie_url, tv_url in REAL_SOURCES:
        for q in QUALITY_VARIANTS:
            sources.append({
                "name": name + " " + q,
                "q": q,
                "movie": movie_url,
                "tv": tv_url,
            })
    return sources


PLAYER_SOURCES = build_sources()
SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)

SPORTS_SOURCES = [
    {"name": "YallaShoot 4K", "q": "4K", "movie": "https://yallashoot.com/embed/{id}", "tv": "https://yallashoot.com/embed/{id}"},
    {"name": "KoraLive HD", "q": "HD", "movie": "https://koralive.com/embed/{id}", "tv": "https://koralive.com/embed/{id}"},
    {"name": "BeinSport HD", "q": "HD", "movie": "https://beinsport.com/embed/{id}", "tv": "https://beinsport.com/embed/{id}"},
    {"name": "HesGoal HD", "q": "HD", "movie": "https://hesgoal.com/embed/{id}", "tv": "https://hesgoal.com/embed/{id}"},
    {"name": "FootyBite HD", "q": "HD", "movie": "https://footybite.com/embed/{id}", "tv": "https://footybite.com/embed/{id}"},
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
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/13.5"})
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
# HTML - INDEX
# =========================================================
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>ONYX CINEMA</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--surface:#16161f;--surface2:#1f1f2e;--accent:#e8b84b;--accent2:#c0392b;--green:#22c55e;--text:#e8e8f0;--text2:#a0a0b8;--border:rgba(255,255,255,0.08);--shadow:0 8px 32px rgba(0,0,0,0.6)}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'Cairo',sans-serif;overflow-x:hidden;min-height:100vh}
a{text-decoration:none;color:inherit}img{max-width:100%;display:block}
button{cursor:pointer;font-family:'Cairo',sans-serif;border:none;background:none;color:inherit}
input{font-family:'Cairo',sans-serif;color:inherit}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--accent);border-radius:3px}
#navbar{position:fixed;top:0;left:0;right:0;z-index:1000;height:68px;display:flex;align-items:center;justify-content:space-between;padding:0 3%;background:linear-gradient(180deg,rgba(10,10,15,0.98) 0%,transparent 100%);transition:.3s}
#navbar.scrolled{background:rgba(10,10,15,0.98);border-bottom:1px solid var(--border);backdrop-filter:blur(20px)}
.nav-logo{font-family:'Bebas Neue',sans-serif;font-size:1.9rem;letter-spacing:3px;color:var(--accent)}
.nav-links{display:flex;gap:32px}
.nav-links a{font-size:.88rem;font-weight:600;color:var(--text2);transition:.2s;cursor:pointer;padding:.3rem 0}
.nav-links a:hover,.nav-links a.active{color:var(--accent)}
.nav-actions{display:flex;align-items:center;gap:12px}
.btn-icon{width:40px;height:40px;border-radius:10px;background:var(--surface2);color:var(--text2);display:flex;align-items:center;justify-content:center;font-size:.85rem;font-weight:700;transition:.2s;border:1px solid var(--border);cursor:pointer}
.btn-icon:hover{background:var(--accent);color:var(--bg);border-color:var(--accent)}
#hero{height:100vh;min-height:580px;position:relative;overflow:hidden;display:flex;align-items:flex-end;padding-bottom:88px}
#hero-bg{position:absolute;inset:0;background-size:cover;background-position:center;transition:opacity .6s}
#hero-bg::after{content:'';position:absolute;inset:0;background:linear-gradient(to top,var(--bg) 0%,rgba(10,10,15,0.65) 42%,rgba(10,10,15,0.15) 100%)}
.hero-content{position:relative;z-index:2;padding:0 60px;max-width:700px}
.hero-eyebrow{font-size:.76rem;font-weight:700;letter-spacing:2px;color:var(--accent);text-transform:uppercase;margin-bottom:14px;display:flex;align-items:center;gap:10px}
.hero-eyebrow::before{content:'';display:block;width:24px;height:2px;background:var(--accent)}
#hero-title{font-size:clamp(2.2rem,5vw,4rem);font-weight:900;line-height:1.12;margin-bottom:14px}
#hero-meta{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px;font-size:.85rem;color:var(--text2)}
#hero-meta .accent{color:var(--accent);font-weight:700}
#hero-desc{font-size:.94rem;color:#a0a0be;line-height:1.8;max-width:520px;margin-bottom:30px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.hero-actions{display:flex;gap:14px;flex-wrap:wrap}
.btn-primary{display:flex;align-items:center;gap:10px;background:var(--accent);color:var(--bg);font-weight:700;font-size:.94rem;padding:13px 30px;border-radius:8px;transition:.2s}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(232,184,75,.35)}
.play-arrow{width:0;height:0;border-top:6px solid transparent;border-bottom:6px solid transparent;border-left:10px solid var(--bg)}
.btn-ghost{display:flex;align-items:center;gap:9px;background:rgba(255,255,255,.08);color:var(--text);font-weight:600;font-size:.94rem;padding:13px 28px;border-radius:8px;border:1px solid rgba(255,255,255,.15);transition:.2s}
.btn-ghost:hover{background:rgba(255,255,255,.16)}
section{padding:50px 40px;max-width:1900px;margin:0 auto}
.sec-title{font-size:1.35rem;font-weight:900;margin-bottom:24px;display:flex;align-items:center;gap:12px}
.sec-title::before{content:'';display:block;width:4px;height:24px;background:var(--accent);border-radius:2px}
.cards-row{display:flex;gap:18px;overflow-x:auto;padding-bottom:12px;scrollbar-width:none;scroll-snap-type:x mandatory}
.cards-row::-webkit-scrollbar{display:none}
.movie-card{flex:0 0 180px;scroll-snap-align:start;cursor:pointer;transition:transform .25s;position:relative}
.movie-card:hover{transform:translateY(-8px)}
.card-poster{width:100%;aspect-ratio:2/3;border-radius:12px;object-fit:cover;background:var(--surface2);margin-bottom:10px;position:relative;overflow:hidden;border:1px solid var(--border)}
.card-poster img{width:100%;height:100%;object-fit:cover;transition:transform .4s;display:block}
.movie-card:hover .card-poster img{transform:scale(1.06)}
.card-rating{position:absolute;top:8px;left:8px;background:rgba(0,0,0,.82);color:var(--accent);font-size:.72rem;font-weight:700;padding:4px 9px;border-radius:5px}
.card-title{font-size:.87rem;font-weight:700;line-height:1.3;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.4em}
.card-year{font-size:.74rem;color:var(--text2)}
#browse-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:22px}
#browse-grid .movie-card{flex:none;width:100%}
.genre-strip{display:flex;gap:10px;overflow-x:auto;padding-bottom:12px;margin-bottom:28px;flex-wrap:wrap}
.genre-chip{padding:8px 20px;border-radius:6px;border:1px solid var(--border);font-size:.82rem;font-weight:600;color:var(--text2);background:var(--surface2);cursor:pointer;transition:.2s;font-family:inherit}
.genre-chip:hover{border-color:var(--accent);color:var(--accent)}
.genre-chip.active{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.modal-overlay{position:fixed;inset:0;z-index:3000;background:rgba(0,0,0,.92);backdrop-filter:blur(12px);display:flex;align-items:flex-start;justify-content:center;padding:20px;opacity:0;pointer-events:none;transition:opacity .3s;overflow-y:auto}
.modal-overlay.open{opacity:1;pointer-events:all}
#modal{width:min(1100px,96vw);background:var(--surface);border:1px solid var(--border);border-radius:20px;box-shadow:var(--shadow);transform:translateY(24px) scale(.97);transition:transform .35s;margin:auto;overflow:hidden}
.modal-overlay.open #modal{transform:translateY(0) scale(1)}
.modal-backdrop{width:100%;height:280px;background-size:cover;background-position:center;position:relative;background-color:var(--surface2)}
.modal-backdrop::after{content:'';position:absolute;inset:0;background:linear-gradient(to top,var(--surface) 0%,transparent 70%)}
.modal-close{position:absolute;top:16px;left:16px;z-index:3;width:38px;height:38px;border-radius:10px;background:rgba(0,0,0,.75);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;cursor:pointer}
.modal-close:hover{background:var(--accent2)}
.modal-body{padding:26px 34px 36px}
.modal-title{font-size:2rem;font-weight:900;line-height:1.2;margin-bottom:12px}
.modal-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:.85rem;color:var(--text2);margin-bottom:18px}
.modal-meta .accent{color:var(--accent);font-weight:700}
.modal-desc{font-size:.92rem;color:#a8a8c4;line-height:1.85;margin-bottom:24px}
.player-container{width:100%;aspect-ratio:16/9;background:#000;border-radius:12px;overflow:hidden;margin-bottom:18px;position:relative;box-shadow:0 15px 50px rgba(0,0,0,.9)}
.player-container iframe{width:100%;height:100%;border:none;display:block}
.player-placeholder{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1a1a2e,#0a0a15);color:var(--text2);flex-direction:column;gap:14px}
.player-placeholder-icon{width:70px;height:70px;border-radius:50%;background:rgba(232,184,75,.15);border:2px solid var(--accent);display:flex;align-items:center;justify-content:center;font-size:1.4rem;color:var(--accent);animation:pulse 2s infinite;font-weight:900}
@keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.1);opacity:.7}}
.quality-info{display:flex;align-items:center;gap:.8rem;padding:12px 16px;background:var(--surface2);border-radius:10px;border:1px solid var(--border);margin-bottom:18px;flex-wrap:wrap}
.quality-badge{padding:5px 14px;border-radius:6px;font-size:.78rem;font-weight:800;text-transform:uppercase}
.quality-badge.q4k{background:linear-gradient(135deg,#f5c518,#ff9800);color:#000}
.quality-badge.qhd{background:var(--green);color:#000}
.quality-badge.qsd{background:var(--surface);color:var(--text2)}
.quality-info-text{color:var(--text2);font-size:.85rem;font-weight:600}
.modal-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}
.cast-section{margin-top:24px}
.cast-section h4{font-size:.82rem;color:var(--text2);margin-bottom:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.cast-list{display:flex;gap:12px;overflow-x:auto;padding-bottom:8px}
.cast-item{flex:0 0 auto;width:110px;background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px 10px;text-align:center}
.cast-avatar{width:60px;height:60px;margin:0 auto 9px;background:linear-gradient(135deg,var(--accent),#d35400);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.4rem;color:var(--bg);overflow:hidden}
.cast-avatar img{width:100%;height:100%;object-fit:cover}
.cast-name{font-size:.76rem;font-weight:700;margin-bottom:3px}
.cast-role{font-size:.66rem;color:var(--text2)}
.seasons-section{margin-top:24px}
.seasons-section h4{font-size:.82rem;color:var(--text2);margin-bottom:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.season-tabs{display:flex;gap:8px;overflow-x:auto;padding-bottom:12px;margin-bottom:16px}
.season-tab{padding:8px 18px;background:var(--surface2);border:1px solid var(--border);color:var(--text2);border-radius:6px;font-size:.82rem;font-weight:600;cursor:pointer;white-space:nowrap;font-family:inherit}
.season-tab.active{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.episodes-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:10px}
.episode-btn{padding:14px 8px;background:var(--surface2);border:1px solid var(--border);color:var(--text);border-radius:8px;font-size:.85rem;font-weight:600;cursor:pointer;text-align:center;font-family:inherit}
.episode-btn:hover{border-color:var(--accent);color:var(--accent)}
.episode-btn.active{background:var(--accent);color:var(--bg)}
.loading{text-align:center;padding:50px 20px;color:var(--text2);grid-column:1/-1}
.spinner{display:inline-block;width:40px;height:40px;border:3px solid var(--surface2);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin-bottom:12px}
@keyframes spin{to{transform:rotate(360deg)}}
footer{background:var(--surface);border-top:1px solid var(--border);padding:40px;text-align:center;color:var(--text2);font-size:.82rem}
.footer-logo{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;color:var(--accent);margin-bottom:10px;letter-spacing:3px}
.match-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px;transition:.2s}
.match-card:hover{border-color:var(--accent);transform:translateY(-3px)}
.match-league{font-size:.72rem;font-weight:700;color:var(--accent);text-transform:uppercase;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}
.match-live-badge{background:#c0392b;color:white;font-size:.6rem;padding:3px 8px;border-radius:4px;letter-spacing:1px}
.match-teams{display:flex;flex-direction:column;gap:10px;margin-bottom:14px}
.match-team{display:flex;justify-content:space-between;align-items:center}
.match-team-name{font-weight:600;font-size:.92rem}
.match-score{font-family:'Bebas Neue',sans-serif;font-size:1.5rem;color:var(--accent);letter-spacing:1px}
.match-footer{display:flex;justify-content:space-between;font-size:.74rem;color:var(--text2);margin-bottom:12px}
.match-quality{background:linear-gradient(135deg,#f5c518,#ff9800);color:#000;font-weight:800;font-size:.65rem;padding:2px 8px;border-radius:4px;text-transform:uppercase}
.league-strip{display:flex;gap:10px;overflow-x:auto;padding-bottom:14px;margin-bottom:24px;flex-wrap:wrap}
@media(max-width:900px){
  #navbar{padding:0 16px;height:60px}.nav-links{display:none}.nav-logo{font-size:1.5rem}
  section{padding:35px 16px}.hero-content{padding:0 20px}#hero-title{font-size:2rem}
  #modal{width:100%;border-radius:16px}.modal-body{padding:20px}.modal-title{font-size:1.5rem}
  #browse-grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}
  .movie-card{flex:0 0 145px}.cast-item{width:96px}
}
@media(max-width:500px){.movie-card{flex:0 0 130px}.btn-primary,.btn-ghost{padding:11px 20px;font-size:.85rem}}
</style>
</head>
<body>

<nav id="navbar">
  <div class="nav-logo">ONYX CINEMA</div>
  <div class="nav-links">
    <a class="active" onclick="switchPage('movies', event)">الأفلام</a>
    <a onclick="switchPage('matches', event)">كرة القدم</a>
    <a onclick="switchPage('series', event)">المسلسلات</a>
    <a onclick="switchPage('browse', event)">تصفح</a>
  </div>
  <div class="nav-actions">
    <button class="btn-icon" onclick="openSearch()">بحث</button>
  </div>
</nav>

<div id="search-overlay" style="position:fixed;inset:0;z-index:2000;background:rgba(0,0,0,.88);backdrop-filter:blur(14px);display:none;align-items:flex-start;justify-content:center;padding-top:120px;padding-left:20px;padding-right:20px">
  <div style="width:min(680px,96vw);background:var(--surface);border:1px solid var(--border);border-radius:20px;overflow:hidden">
    <div style="display:flex;align-items:center;gap:14px;padding:18px 22px;border-bottom:1px solid var(--border)">
      <input id="search-input" type="text" placeholder="ابحث عن فيلم أو مسلسل..." style="flex:1;background:none;border:none;outline:none;font-size:1.05rem;color:var(--text)" />
      <button onclick="closeSearch()" style="background:var(--surface2);border:1px solid var(--border);color:var(--text2);width:50px;height:32px;border-radius:8px;font-weight:700;cursor:pointer;font-family:inherit">ESC</button>
    </div>
    <div id="search-results" style="max-height:420px;overflow-y:auto"></div>
  </div>
</div>

<div class="modal-overlay" id="modal-overlay" onclick="if(event.target.id==='modal-overlay')closeModal()">
  <div id="modal">
    <div class="modal-backdrop" id="modal-backdrop">
      <button class="modal-close" onclick="closeModal()">ESC</button>
    </div>
    <div class="modal-body">
      <h2 class="modal-title" id="modal-title"></h2>
      <div class="modal-meta" id="modal-meta"></div>
      <p class="modal-desc" id="modal-desc"></p>
      <div class="player-container">
        <div class="player-placeholder" id="player-placeholder">
          <div class="player-placeholder-icon">▶</div>
          <div>جار تحميل الفيديو...</div>
        </div>
        <iframe id="pframe" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerpolicy="origin" style="display:none"></iframe>
      </div>
      <div class="quality-info">
        <span class="quality-badge q4k" id="quality-badge">4K</span>
        <span class="quality-info-text">يتم التشغيل تلقائياً بأفضل جودة متاحة</span>
      </div>
      <div class="modal-actions">
        <button class="btn-primary" onclick="playNow()"><div class="play-arrow"></div>مشاهدة الآن</button>
        <button class="btn-ghost" onclick="openFullscreen()">شاشة كاملة</button>
      </div>
      <div class="seasons-section" id="seasons-section" style="display:none">
        <h4>المواسم والحلقات</h4>
        <div class="season-tabs" id="season-tabs"></div>
        <div class="episodes-grid" id="episodes-grid"></div>
      </div>
      <div class="cast-section" id="cast-section"></div>
    </div>
  </div>
</div>

<main>
  <div id="movies-page">
    <section id="hero" style="padding:0;max-width:none">
      <div id="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-eyebrow">الفيلم المميز</div>
        <h1 id="hero-title"></h1>
        <div id="hero-meta"></div>
        <p id="hero-desc"></p>
        <div class="hero-actions">
          <button class="btn-primary" onclick="playHero()"><div class="play-arrow"></div>مشاهدة الآن</button>
          <button class="btn-ghost" onclick="addHeroToFav()">❤ أضف للمفضلة</button>
        </div>
      </div>
    </section>
    <section>
      <h2 class="sec-title">رائج الآن</h2>
      <div class="cards-row" id="trending-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>
    <section>
      <h2 class="sec-title">أفلام شائعة</h2>
      <div class="cards-row" id="popular-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>
    <section>
      <h2 class="sec-title">الأعلى تقييماً</h2>
      <div class="cards-row" id="toprated-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>
  </div>

  <div id="matches-page" style="display:none">
    <section>
      <h2 class="sec-title">مباريات كرة القدم</h2>
      <div class="league-strip" id="league-strip"></div>
      <div id="matches-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px"></div>
    </section>
  </div>

  <div id="series-page" style="display:none">
    <section>
      <h2 class="sec-title">مسلسلات شائعة</h2>
      <div class="cards-row" id="series-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>
    <section>
      <h2 class="sec-title">الأعلى تقييماً في المسلسلات</h2>
      <div class="cards-row" id="series-top-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>
  </div>

  <div id="browse-page" style="display:none">
    <section>
      <h2 class="sec-title">تصفّح الأفلام</h2>
      <div class="genre-strip" id="genre-strip"></div>
      <div id="browse-grid"><div class="loading"><div class="spinner"></div></div></div>
    </section>
  </div>
</main>

<footer>
  <div class="footer-logo">ONYX CINEMA PRO</div>
  <p>منصة أفلام ومسلسلات ومباريات كرة القدم - جميع الحقوق محفوظة 2026</p>
</footer>

<script>
const IMG_W = 'https://image.tmdb.org/t/p/w500';
const IMG_O = 'https://image.tmdb.org/t/p/original';
const IMG_P = 'https://image.tmdb.org/t/p/w185';

const S = {
  movies: [],
  current: null,
  seasons: [],
  tvId: null,
  currentSeason: 1,
  currentEpisode: 1,
  matches: [],
  currentLeague: '',
};

window.addEventListener('scroll', () => {
  document.getElementById('navbar').classList.toggle('scrolled', window.scrollY > 40);
});

function showToast(msg) {
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = 'position:fixed;bottom:30px;left:50%;transform:translateX(-50%);padding:12px 24px;background:var(--surface2);color:var(--text);border:1px solid var(--accent);border-radius:10px;font-weight:600;z-index:9999;transition:0.3s;opacity:0';
  document.body.appendChild(t);
  setTimeout(() => t.style.opacity = '1', 50);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 2500);
}

async function fetchJSON(path) {
  try {
    const r = await fetch(path);
    return await r.json();
  } catch (e) {
    console.error(e);
    return { results: [] };
  }
}

function buildCard(m) {
  const div = document.createElement('div');
  div.className = 'movie-card';
  const type = m.media_type || (m.name ? 'tv' : 'movie');
  const title = m.title || m.name || '?';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
  const poster = m.poster_path ? IMG_W + m.poster_path : '';
  div.innerHTML =
    '<div class="card-poster">' +
      (poster ? '<img src="' + poster + '" loading="lazy" alt="" />' :
        '<div style="width:100%;height:100%;background:var(--surface2);display:flex;align-items:center;justify-content:center;font-size:.8rem;color:var(--text2)">لا صورة</div>') +
      '<div class="card-rating">★ ' + rating + '</div>' +
    '</div>' +
    '<div class="card-title">' + title + '</div>' +
    '<div class="card-year">' + year + '</div>';
  div.onclick = () => openModal(m.id, type);
  return div;
}

async function init() {
  const trending = await fetchJSON('/api/trending');
  const popular = await fetchJSON('/api/popular/movie');
  const top = await fetchJSON('/api/top_rated/movie');
  const series = await fetchJSON('/api/popular/tv');
  const seriesTop = await fetchJSON('/api/top_rated/tv');
  S.movies = [...(trending.results || []), ...(popular.results || []), ...(series.results || [])];
  renderHero((trending.results || [])[0]);
  renderRow('trending-row', trending.results || []);
  renderRow('popular-row', popular.results || []);
  renderRow('toprated-row', top.results || []);
  renderRow('series-row', series.results || []);
  renderRow('series-top-row', seriesTop.results || []);
  renderGenres();
  renderGrid(popular.results || []);
  await loadMatches();
}

function renderHero(m) {
  if (!m) return;
  S.current = m;
  if (m.backdrop_path) {
    document.getElementById('hero-bg').style.backgroundImage = "url('" + IMG_O + m.backdrop_path + "')";
  }
  document.getElementById('hero-title').textContent = m.title || m.name || '?';
  document.getElementById('hero-meta').innerHTML =
    '<span class="accent">★ ' + (m.vote_average?.toFixed(1) || 'N/A') + '</span>' +
    '<span>' + (m.release_date || m.first_air_date || '').substring(0, 4) + '</span>' +
    '<span>' + (m.media_type === 'tv' ? 'مسلسل' : 'فيلم') + '</span>';
  document.getElementById('hero-desc').textContent = m.overview || '';
}

function renderRow(id, movies) {
  const row = document.getElementById(id);
  if (!row) return;
  row.innerHTML = '';
  movies.slice(0, 15).forEach(m => row.appendChild(buildCard(m)));
}

function renderGrid(movies) {
  const grid = document.getElementById('browse-grid');
  grid.innerHTML = '';
  movies.slice(0, 24).forEach(m => grid.appendChild(buildCard(m)));
}

function renderGenres() {
  const strip = document.getElementById('genre-strip');
  const genres = [
    {name:'الكل', id:null}, {name:'أكشن', id:28}, {name:'دراما', id:18},
    {name:'كوميديا', id:35}, {name:'خيال علمي', id:878}, {name:'رعب', id:27},
    {name:'رومانسي', id:10749}, {name:'مغامرة', id:12},
  ];
  strip.innerHTML = genres.map((g, i) =>
    '<button class="genre-chip' + (i === 0 ? ' active' : '') + '" onclick="filterGenre(' + (g.id || 'null') + ', this)">' + g.name + '</button>'
  ).join('');
}

async function filterGenre(gid, btn) {
  document.querySelectorAll('#genre-strip .genre-chip').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const grid = document.getElementById('browse-grid');
  grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  const url = gid ? '/api/discover?genre=' + gid : '/api/popular/movie';
  const data = await fetchJSON(url);
  renderGrid(data.results || []);
}

function openSearch() {
  document.getElementById('search-overlay').style.display = 'flex';
  setTimeout(() => document.getElementById('search-input').focus(), 100);
}

function closeSearch() {
  document.getElementById('search-overlay').style.display = 'none';
}

document.getElementById('search-input')?.addEventListener('input', async (e) => {
  const q = e.target.value.trim();
  const list = document.getElementById('search-results');
  if (!q) { list.innerHTML = ''; return; }
  list.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  const data = await fetchJSON('/api/search?q=' + encodeURIComponent(q));
  const results = (data.results || []).slice(0, 10);
  if (!results.length) {
    list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text2)">لا توجد نتائج</div>';
    return;
  }
  list.innerHTML = results.map(m => {
    const type = m.media_type || 'movie';
    const title = m.title || m.name || '?';
    const poster = m.poster_path ? IMG_W + m.poster_path : '';
    return '<div onclick="closeSearch();openModal(' + m.id + ',\'' + type + '\')" style="display:flex;align-items:center;gap:14px;padding:12px 22px;cursor:pointer;border-bottom:1px solid rgba(255,255,255,.025)">' +
      (poster ? '<img src="' + poster + '" style="width:44px;height:64px;object-fit:cover;border-radius:6px" />' : '') +
      '<div><strong>' + title + '</strong><br><small style="color:var(--text2)">' + (m.release_date || m.first_air_date || '').substring(0, 4) + ' • ★ ' + (m.vote_average?.toFixed(1) || 'N/A') + '</small></div>' +
    '</div>';
  }).join('');
});

async function openModal(id, type) {
  S.current = { id, type };
  document.getElementById('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
  const pframe = document.getElementById('pframe');
  const ph = document.getElementById('player-placeholder');
  pframe.style.display = 'none';
  pframe.src = 'about:blank';
  ph.style.display = 'flex';
  document.getElementById('seasons-section').style.display = 'none';
  document.getElementById('cast-section').innerHTML = '';
  const data = await fetchJSON('/api/' + type + '/' + id);
  document.getElementById('modal-title').textContent = data.title || data.name || '?';
  document.getElementById('modal-meta').innerHTML =
    '<span class="accent">★ ' + (data.vote_average?.toFixed(1) || 'N/A') + '</span>' +
    '<span>' + (data.release_date || data.first_air_date || '').substring(0, 4) + '</span>' +
    (data.runtime ? '<span>' + data.runtime + ' دقيقة</span>' : '');
  document.getElementById('modal-desc').textContent = data.overview || 'لا يوجد وصف';
  if (data.backdrop_path) {
    document.getElementById('modal-backdrop').style.backgroundImage = "url('" + IMG_O + data.backdrop_path + "')";
  }
  const cast = data.credits?.cast?.slice(0, 12) || [];
  if (cast.length) {
    document.getElementById('cast-section').innerHTML =
      '<h4>طاقم التمثيل</h4><div class="cast-list">' +
      cast.map(c => {
        const avatar = c.profile_path ? '<img src="' + IMG_P + c.profile_path + '" />' : (c.name || '?')[0];
        return '<div class="cast-item"><div class="cast-avatar">' + avatar + '</div>' +
          '<div class="cast-name">' + (c.name || '?') + '</div>' +
          '<div class="cast-role">' + (c.character || '') + '</div></div>';
      }).join('') + '</div>';
  }
  if (type === 'tv' && data.seasons) {
    S.seasons = data.seasons.filter(s => s.season_number > 0);
    S.tvId = id;
    S.currentSeason = 1;
    S.currentEpisode = 1;
    document.getElementById('seasons-section').style.display = 'block';
    renderSeasons(S.seasons, 1);
  }
  setTimeout(() => startStream(id, type, 1, 1), 300);
}

function renderSeasons(seasons, activeNum) {
  const tabs = document.getElementById('season-tabs');
  tabs.innerHTML = seasons.map(s =>
    '<button class="season-tab' + (s.season_number === activeNum ? ' active' : '') + '" onclick="selectSeason(' + s.season_number + ')">' +
    (s.name || 'الموسم ' + s.season_number) + ' (' + (s.episode_count || 0) + ')</button>'
  ).join('');
  loadEpisodes(activeNum);
}

async function selectSeason(num) {
  document.querySelectorAll('.season-tab').forEach((b, i) => {
    const sn = S.seasons[i]?.season_number;
    b.classList.toggle('active', sn === num);
  });
  await loadEpisodes(num);
}

async function loadEpisodes(seasonNum) {
  const grid = document.getElementById('episodes-grid');
  grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  S.currentSeason = seasonNum;
  const data = await fetchJSON('/api/tv/' + S.tvId + '/season/' + seasonNum);
  const eps = data.episodes || [];
  if (!eps.length) {
    grid.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2);grid-column:1/-1">لا توجد حلقات</div>';
    return;
  }
  grid.innerHTML = eps.map(e =>
    '<button class="episode-btn" onclick="playEpisode(' + seasonNum + ',' + e.episode_number + ', this)">' +
    '<div style="font-size:.7rem;color:var(--text2);margin-bottom:4px">حلقة</div>' +
    '<div style="font-size:1rem;font-weight:700">' + e.episode_number + '</div>' +
    '</button>'
  ).join('');
}

function playEpisode(seasonNum, epNum, btn) {
  document.querySelectorAll('.episode-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  S.currentSeason = seasonNum;
  S.currentEpisode = epNum;
  startStream(S.tvId, 'tv', seasonNum, epNum);
  showToast('حلقة ' + epNum + ' - الموسم ' + seasonNum);
}

function startStream(id, type, season, episode) {
  const pframe = document.getElementById('pframe');
  const ph = document.getElementById('player-placeholder');
  ph.style.display = 'flex';
  pframe.style.display = 'none';
  const url = '/player?type=' + type + '&id=' + id + '&season=' + (season || 1) + '&episode=' + (episode || 1);
  pframe.src = url;
  pframe.onload = () => {
    setTimeout(() => {
      ph.style.display = 'none';
      pframe.style.display = 'block';
    }, 500);
  };
}

function playNow() {
  if (!S.current) return;
  startStream(S.current.id, S.current.type, S.currentSeason, S.currentEpisode);
  showToast('جاري التشغيل...');
}

function openFullscreen() {
  if (!S.current) return;
  const url = '/player?type=' + S.current.type + '&id=' + S.current.id + '&season=' + S.currentSeason + '&episode=' + S.currentEpisode;
  window.open(url, '_blank');
}

function playHero() {
  if (!S.current) return;
  const type = S.current.media_type || (S.current.name ? 'tv' : 'movie');
  openModal(S.current.id, type);
}

function addHeroToFav() {
  if (!S.current) return;
  showToast('❤ أضيف للمفضلة');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
  const pframe = document.getElementById('pframe');
  if (pframe) pframe.src = 'about:blank';
}

function switchPage(page, event) {
  if (event) event.preventDefault();
  document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
  if (event && event.target) event.target.classList.add('active');
  document.getElementById('movies-page').style.display = page === 'movies' ? 'block' : 'none';
  document.getElementById('matches-page').style.display = page === 'matches' ? 'block' : 'none';
  document.getElementById('series-page').style.display = page === 'series' ? 'block' : 'none';
  document.getElementById('browse-page').style.display = page === 'browse' ? 'block' : 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadMatches(league) {
  const grid = document.getElementById('matches-grid');
  grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  const url = league ? '/api/matches?league=' + league : '/api/matches';
  const data = await fetchJSON(url);
  S.matches = data.matches || [];
  renderMatches();
  renderLeagueStrip();
}

function renderLeagueStrip() {
  const strip = document.getElementById('league-strip');
  const leagues = [
    {id:'', name:'كل الدوريات'}, {id:'saudi', name:'السعودي'}, {id:'egypt', name:'المصري'},
    {id:'spain', name:'الإسباني'}, {id:'england', name:'الإنجليزي'}, {id:'italy', name:'الإيطالي'},
    {id:'ucl', name:'أبطال أوروبا'}
  ];
  strip.innerHTML = leagues.map(l =>
    '<button class="genre-chip' + (S.currentLeague === l.id ? ' active' : '') + '" onclick="selectLeague(\'' + l.id + '\')">' + l.name + '</button>'
  ).join('');
}

function selectLeague(id) {
  S.currentLeague = id;
  loadMatches(id || null);
}

function renderMatches() {
  const grid = document.getElementById('matches-grid');
  if (!S.matches.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text2)">لا توجد مباريات</div>';
    return;
  }
  grid.innerHTML = S.matches.map((m, i) => {
    const statusText = m.status === 'live' ? 'مباشر الآن' : m.status === 'upcoming' ? 'قادمة - ' + m.time : 'انتهت';
    const liveBadge = m.status === 'live' ? '<span class="match-live-badge">LIVE</span>' : '';
    return '<div class="match-card">' +
      '<div class="match-league"><span>' + m.league + '</span>' + liveBadge + '</div>' +
      '<div class="match-teams">' +
        '<div class="match-team"><span class="match-team-name">' + m.team1 + '</span><span class="match-score">' + m.s1 + '</span></div>' +
        '<div class="match-team"><span class="match-team-name">' + m.team2 + '</span><span class="match-score">' + m.s2 + '</span></div>' +
      '</div>' +
      '<div class="match-footer"><span>' + statusText + '</span><span>' + m.ch + '</span></div>' +
      '<div style="display:flex;justify-content:space-between;align-items:center">' +
        '<span class="match-quality">' + m.quality + '</span>' +
        '<button class="btn-primary" style="padding:8px 16px;font-size:.78rem" onclick="watchMatch(' + i + ')">مشاهدة</button>' +
      '</div>' +
    '</div>';
  }).join('');
}

function watchMatch(idx) {
  const m = S.matches[idx];
  if (!m) return;
  showToast('جاري فتح البث...');
  const url = '/match?id=' + encodeURIComponent(m.stream_id) + '&team1=' + encodeURIComponent(m.team1) + '&team2=' + encodeURIComponent(m.team2);
  window.open(url, '_blank');
}

document.addEventListener('DOMContentLoaded', init);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { closeModal(); closeSearch(); }
});
</script>
</body>
</html>
"""


# =========================================================
# HTML - PLAYER (Activity)
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
#search-btn{padding:10px 20px;background:var(--accent);color:#000;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-family:inherit}
#tabs{display:flex;gap:8px;padding:12px 18px;background:var(--surface);border-bottom:1px solid var(--border);overflow-x:auto}
#tabs::-webkit-scrollbar{display:none}
.tab{padding:8px 18px;background:var(--surface2);color:var(--text2);border:1px solid var(--border);border-radius:8px;font-size:0.85rem;font-weight:600;cursor:pointer;white-space:nowrap;font-family:inherit}
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
@media(max-width:600px){.grid{grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:12px}.detail-poster{width:140px}}
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

<script>
const IMG_BASE = 'https://image.tmdb.org/t/p/w500';
let currentContent = null;
let currentList = [];

async function api(path) {
  try { const r = await fetch(path); return await r.json(); }
  catch (e) { return { results: [] }; }
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
      (poster ? '<img class="card-poster" src="' + poster + '" loading="lazy" />' :
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
  const url = type === 'tv' ? 'https://vidlink.pro/tv/' + id + '/1/1' : 'https://vidlink.pro/movie/' + id;
  const wrap = document.getElementById('player-wrap');
  const frame = document.getElementById('player-frame');
  frame.src = url;
  wrap.classList.add('active');
  wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function playEpisode(tvId, seasonNum, epNum) {
  const url = 'https://vidlink.pro/tv/' + tvId + '/' + seasonNum + '/' + epNum;
  const wrap = document.getElementById('player-wrap');
  const frame = document.getElementById('player-frame');
  frame.src = url;
  wrap.classList.add('active');
  wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showGrid() {
  document.getElementById('detail').classList.remove('active');
  document.getElementById('content').style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

window.addEventListener('DOMContentLoaded', () => {
  loadCategory('trending', document.querySelector('.tab.active'));
});
</script>
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
#wrap{position:relative;width:100vw;height:100vh}
iframe{position:absolute;top:52px;left:0;width:100%;height:calc(100% - 52px);border:none}
#topbar{position:absolute;top:0;left:0;right:0;height:52px;background:rgba(10,10,15,.98);color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 18px;z-index:20;border-bottom:1px solid rgba(255,255,255,.08)}
#topbar .info{font-size:14px;font-weight:700;color:#e8b84b}
#topbar .btns{display:flex;gap:6px;flex-wrap:wrap}
#topbar button{background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.12);padding:7px 13px;border-radius:6px;cursor:pointer;font-size:11px;font-weight:700;font-family:inherit}
#topbar button.active{background:#e8b84b;color:#000}
</style>
</head>
<body>
<div id="wrap">
  <div id="topbar">
    <div class="info" id="match-info">ONYX SPORTS</div>
    <div class="btns" id="servers"></div>
  </div>
  <iframe id="player" allowfullscreen allow="autoplay; encrypted-media" referrerpolicy="origin"></iframe>
</div>
<script>
const SOURCES = __SOURCES__;
const p = new URLSearchParams(location.search);
const id = p.get('id') || 'match_1';
const team1 = p.get('team1') || '';
const team2 = p.get('team2') || '';
if (team1 && team2) document.getElementById('match-info').textContent = team1 + ' ضد ' + team2;

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
  const src = SOURCES[idx];
  const url = (src.movie || src.tv).replace(/{id}/g, id);
  document.getElementById('player').src = url;
  document.querySelectorAll('#servers button').forEach((b, i) => b.classList.toggle('active', i === idx));
}

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


@app.route("/api/discover")
def api_discover():
    genre = request.args.get("genre")
    year = request.args.get("year")
    params = {"sort_by": "popularity.desc"}
    if genre: params["with_genres"] = genre
    if year: params["primary_release_year"] = year
    return jsonify(tmdb("/discover/movie", params))


@app.route("/api/matches")
def api_matches():
    league = request.args.get("league")
    date = request.args.get("date")
    matches = get_matches(league, date)
    return jsonify({"matches": matches, "count": len(matches)})


@app.route("/api/leagues")
def api_leagues():
    return jsonify({"leagues": FOOTBALL_LEAGUES})


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ONYX CINEMA v13.5",
        "tmdb": "ok" if TMDB_API_KEY else "missing",
        "sources": len(PLAYER_SOURCES),
    })


# =========================================================
# DISCORD BOT
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
