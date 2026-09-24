# -*- coding: utf-8 -*-
"""
ONYX CINEMA v8.0 — Single File
Flask + TMDB + 8 Sources + Full UI + Video Player
"""

from flask import Flask, jsonify, request, render_template_string
import os
import time
import json
import urllib.request
import urllib.parse
from collections import defaultdict

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "a6288fc42fb7de2837e2756a101397e5")
SECRET_SALT = os.getenv("SECRET_SALT", "onyx_cinema_2025_secret")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1212admin")
TMDB_BASE = "https://api.themoviedb.org/3"

# ══════════════════════════════════════════════════════════
# SECURITY
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
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return r


# ══════════════════════════════════════════════════════════
# PLAYER SOURCES — 8 مصادر
# ══════════════════════════════════════════════════════════
PLAYER_SOURCES = [
    {"name": "VidLink 4K", "q": "4K",
     "movie": "https://vidlink.pro/movie/{id}",
     "tv": "https://vidlink.pro/tv/{id}/{s}/{e}"},
    {"name": "Videasy 4K", "q": "4K",
     "movie": "https://player.videasy.net/movie/{id}",
     "tv": "https://player.videasy.net/tv/{id}/{s}/{e}"},
    {"name": "AutoEmbed HD", "q": "HD",
     "movie": "https://player.autoembed.cc/embed/movie/{id}",
     "tv": "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}"},
    {"name": "SmashyStream HD", "q": "HD",
     "movie": "https://player.smashy.stream/movie/{id}",
     "tv": "https://player.smashy.stream/tv/{id}?s={s}&e={e}"},
    {"name": "VidSrc XYZ", "q": "HD",
     "movie": "https://vidsrc.xyz/embed/movie?tmdb={id}",
     "tv": "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}"},
    {"name": "2Embed.to", "q": "HD",
     "movie": "https://www.2embed.to/embed/tmdb/movie?id={id}",
     "tv": "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"},
    {"name": "Embed.su", "q": "HD",
     "movie": "https://embed.su/embed/movie/{id}",
     "tv": "https://embed.su/embed/tv/{id}/{s}/{e}"},
    {"name": "VidSrc.to", "q": "SD",
     "movie": "https://vidsrc.to/embed/movie/{id}",
     "tv": "https://vidsrc.to/embed/tv/{id}/{s}/{e}"},
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
    p["language"] = "ar"
    url = f"{TMDB_BASE}{ep}?{urllib.parse.urlencode(p)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/8.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


# ══════════════════════════════════════════════════════════
# HTML — SINGLE FILE (Full UI + Player)
# ══════════════════════════════════════════════════════════
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<meta name="theme-color" content="#0a0a0f">
<title>ONYX CINEMA</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{
  --bg:#0a0a0f;--bg2:#12121a;--surface:#16161f;--surface2:#1f1f2e;
  --accent:#e8b84b;--accent2:#c0392b;--gold:#f5c518;--green:#22c55e;
  --text:#e8e8f0;--text2:#a0a0b8;--text3:#5a5a72;
  --border:rgba(255,255,255,0.08);
  --radius:12px;--radius-lg:20px;
  --shadow:0 8px 32px rgba(0,0,0,0.6);
}
html{scroll-behavior:smooth;font-size:16px}
body{background:var(--bg);color:var(--text);font-family:'Cairo',sans-serif;overflow-x:hidden;min-height:100vh}
a{text-decoration:none;color:inherit}
img{max-width:100%;display:block}
button{cursor:pointer;font-family:'Cairo',sans-serif;border:none;background:none;color:inherit}
input,textarea,select{font-family:'Cairo',sans-serif;color:inherit}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--accent);border-radius:3px}

/* NAVBAR */
#navbar{position:fixed;top:0;left:0;right:0;z-index:1000;height:68px;display:flex;align-items:center;justify-content:space-between;padding:0 3%;background:linear-gradient(180deg,rgba(10,10,15,0.98) 0%,transparent 100%);transition:.3s}
#navbar.scrolled{background:rgba(10,10,15,0.98);border-bottom:1px solid var(--border);backdrop-filter:blur(20px)}
.nav-logo{font-family:'Bebas Neue',sans-serif;font-size:1.9rem;letter-spacing:3px;color:var(--accent);flex-shrink:0}
.nav-links{display:flex;gap:32px}
.nav-links a{font-size:.88rem;font-weight:600;color:var(--text2);transition:.2s;cursor:pointer;padding:.3rem 0}
.nav-links a:hover,.nav-links a.active{color:var(--accent)}
.nav-actions{display:flex;align-items:center;gap:12px}
.btn-icon{width:40px;height:40px;border-radius:10px;background:var(--surface2);color:var(--text2);display:flex;align-items:center;justify-content:center;font-size:1rem;transition:.2s;border:1px solid var(--border);cursor:pointer}
.btn-icon:hover{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.user-profile{display:flex;align-items:center;gap:9px;padding:5px 14px;border-radius:20px;background:rgba(232,184,75,.08);cursor:pointer;transition:.2s;border:1px solid rgba(232,184,75,.2)}
.user-profile:hover{background:rgba(232,184,75,.16)}
.user-avatar{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--accent),#d35400);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--bg);font-size:.85rem}
.user-name{font-size:.83rem;color:var(--accent);font-weight:600}

/* HERO */
#hero{height:100vh;min-height:580px;position:relative;overflow:hidden;display:flex;align-items:flex-end;padding-bottom:88px}
#hero-bg{position:absolute;inset:0;background-size:cover;background-position:center;background-repeat:no-repeat;transition:opacity .6s}
#hero-bg::after{content:'';position:absolute;inset:0;background:linear-gradient(to top,var(--bg) 0%,rgba(10,10,15,0.65) 42%,rgba(10,10,15,0.15) 100%)}
.hero-content{position:relative;z-index:2;padding:0 60px;max-width:700px}
.hero-eyebrow{font-size:.76rem;font-weight:700;letter-spacing:2px;color:var(--accent);text-transform:uppercase;margin-bottom:14px;display:flex;align-items:center;gap:10px}
.hero-eyebrow::before{content:'';display:block;width:24px;height:2px;background:var(--accent)}
#hero-title{font-size:clamp(2.2rem,5vw,4rem);font-weight:900;line-height:1.12;margin-bottom:14px}
#hero-meta{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px;font-size:.85rem;color:var(--text2)}
#hero-meta .accent{color:var(--accent);font-weight:700}
#hero-meta .sep{color:var(--border)}
#hero-desc{font-size:.94rem;color:#a0a0be;line-height:1.8;max-width:520px;margin-bottom:30px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.hero-actions{display:flex;gap:14px;flex-wrap:wrap}
.btn-primary{display:flex;align-items:center;gap:10px;background:var(--accent);color:var(--bg);font-weight:700;font-size:.94rem;padding:13px 30px;border-radius:8px;transition:.2s;cursor:pointer;border:none}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(232,184,75,.35)}
.play-arrow{width:0;height:0;border-top:6px solid transparent;border-bottom:6px solid transparent;border-left:10px solid var(--bg)}
.btn-ghost{display:flex;align-items:center;gap:9px;background:rgba(255,255,255,.08);color:var(--text);font-weight:600;font-size:.94rem;padding:13px 28px;border-radius:8px;border:1px solid rgba(255,255,255,.15);transition:.2s;cursor:pointer}
.btn-ghost:hover{background:rgba(255,255,255,.16)}

/* SECTIONS */
section{padding:50px 40px;max-width:1900px;margin:0 auto}
.sec-title{font-size:1.35rem;font-weight:900;margin-bottom:24px;display:flex;align-items:center;gap:12px}
.sec-title::before{content:'';display:block;width:4px;height:24px;background:var(--accent);border-radius:2px}

/* CARDS ROW */
.cards-row{display:flex;gap:18px;overflow-x:auto;padding-bottom:12px;scrollbar-width:none;scroll-snap-type:x mandatory}
.cards-row::-webkit-scrollbar{display:none}

/* MOVIE CARD */
.movie-card{flex:0 0 180px;scroll-snap-align:start;cursor:pointer;transition:transform .25s;position:relative}
.movie-card:hover{transform:translateY(-8px)}
.card-poster{width:100%;aspect-ratio:2/3;border-radius:12px;object-fit:cover;background:var(--surface2);margin-bottom:10px;position:relative;overflow:hidden;border:1px solid var(--border)}
.card-poster img{width:100%;height:100%;object-fit:cover;transition:transform .4s;display:block}
.movie-card:hover .card-poster img{transform:scale(1.06)}
.card-rating{position:absolute;top:8px;left:8px;background:rgba(0,0,0,.82);color:var(--accent);font-size:.72rem;font-weight:700;padding:4px 9px;border-radius:5px;letter-spacing:.3px;backdrop-filter:blur(8px)}
.card-fav{position:absolute;top:8px;right:8px;width:32px;height:32px;border-radius:50%;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;font-size:.9rem;color:var(--text2);z-index:2;transition:.2s;cursor:pointer;border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(8px)}
.card-fav.active{background:var(--accent2);border-color:var(--accent2);color:white}
.card-fav:hover{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.card-info{padding:0 4px}
.card-title{font-size:.87rem;font-weight:700;line-height:1.3;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.4em}
.card-year{font-size:.74rem;color:var(--text2)}

/* GRID */
#browse-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:22px}
#browse-grid .movie-card{flex:none;width:100%}

/* GENRE STRIP */
.genre-strip{display:flex;gap:10px;overflow-x:auto;padding-bottom:12px;scrollbar-width:none;margin-bottom:28px;flex-wrap:wrap}
.genre-strip::-webkit-scrollbar{display:none}
.genre-chip{flex:0 0 auto;padding:8px 20px;border-radius:6px;border:1px solid var(--border);font-size:.82rem;font-weight:600;color:var(--text2);background:var(--surface2);cursor:pointer;transition:.2s}
.genre-chip:hover{border-color:var(--accent);color:var(--accent)}
.genre-chip.active{background:var(--accent);color:var(--bg);border-color:var(--accent)}

/* MODAL */
.modal-overlay{position:fixed;inset:0;z-index:3000;background:rgba(0,0,0,.92);backdrop-filter:blur(12px);display:flex;align-items:flex-start;justify-content:center;padding:20px;opacity:0;pointer-events:none;transition:opacity .3s;overflow-y:auto}
.modal-overlay.open{opacity:1;pointer-events:all}
#modal{width:min(1100px,96vw);background:var(--surface);border:1px solid var(--border);border-radius:20px;box-shadow:var(--shadow);transform:translateY(24px) scale(.97);transition:transform .35s;margin:auto;overflow:hidden}
.modal-overlay.open #modal{transform:translateY(0) scale(1)}
.modal-backdrop{width:100%;height:280px;background-size:cover;background-position:center;position:relative;background-repeat:no-repeat;background-color:var(--surface2)}
.modal-backdrop::after{content:'';position:absolute;inset:0;background:linear-gradient(to top,var(--surface) 0%,transparent 70%)}
.modal-close{position:absolute;top:16px;left:16px;z-index:3;width:38px;height:38px;border-radius:10px;background:rgba(0,0,0,.75);color:white;display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:700;transition:.2s;cursor:pointer;border:1px solid rgba(255,255,255,.15);backdrop-filter:blur(8px)}
.modal-close:hover{background:var(--accent2);border-color:var(--accent2)}
.modal-body{padding:26px 34px 36px}
.modal-title{font-size:2rem;font-weight:900;line-height:1.2;margin-bottom:12px}
.modal-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:.85rem;color:var(--text2);margin-bottom:18px}
.modal-meta .accent{color:var(--accent);font-weight:700}
.modal-meta .sep{color:var(--surface2)}
.modal-desc{font-size:.92rem;color:#a8a8c4;line-height:1.85;margin-bottom:24px}

/* PLAYER */
.player-container{width:100%;aspect-ratio:16/9;background:#000;border-radius:12px;overflow:hidden;margin-bottom:18px;position:relative;box-shadow:0 15px 50px rgba(0,0,0,.9)}
.player-container iframe{width:100%;height:100%;border:none;display:block}
.player-placeholder{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1a1a2e,#0a0a15);color:var(--text2);flex-direction:column;gap:14px}
.player-placeholder-icon{width:70px;height:70px;border-radius:50%;background:rgba(232,184,75,.15);border:2px solid var(--accent);display:flex;align-items:center;justify-content:center;font-size:1.8rem;color:var(--accent);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.1);opacity:.7}}

/* QUALITY INFO */
.quality-info{display:flex;align-items:center;gap:.8rem;padding:12px 16px;background:var(--surface2);border-radius:10px;border:1px solid var(--border);margin-bottom:18px;flex-wrap:wrap}
.quality-badge{padding:5px 14px;border-radius:6px;font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.5px}
.quality-badge.q4k{background:linear-gradient(135deg,#f5c518,#ff9800);color:#000}
.quality-badge.qhd{background:var(--green);color:#000}
.quality-badge.qsd{background:var(--surface);color:var(--text2)}
.quality-info-text{color:var(--text2);font-size:.85rem;font-weight:600}

/* ACTIONS */
.modal-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}

/* CAST */
.cast-section{margin-top:24px}
.cast-section h4{font-size:.82rem;color:var(--text2);margin-bottom:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.cast-list{display:flex;gap:12px;overflow-x:auto;padding-bottom:8px;scrollbar-width:none}
.cast-list::-webkit-scrollbar{display:none}
.cast-item{flex:0 0 auto;width:100px;background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px 10px;text-align:center;cursor:pointer;transition:.2s}
.cast-item:hover{border-color:var(--accent);transform:translateY(-3px)}
.cast-avatar{width:56px;height:56px;margin:0 auto 9px;background:linear-gradient(135deg,var(--accent),#d35400);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.4rem;color:var(--bg);overflow:hidden}
.cast-avatar img{width:100%;height:100%;object-fit:cover}
.cast-name{font-size:.76rem;font-weight:700;margin-bottom:3px;line-height:1.2}
.cast-role{font-size:.66rem;color:var(--text2)}

/* STARS */
.stars-row{display:flex;gap:8px;margin:16px 0}
.star-btn{font-size:1.4rem;cursor:pointer;transition:.18s;color:var(--text2);background:none;border:none}
.star-btn:hover,.star-btn.lit{color:var(--accent);transform:scale(1.18)}

/* AUTH MODAL */
#auth-modal{position:fixed;inset:0;z-index:9000;background:rgba(0,0,0,.97);display:none;align-items:center;justify-content:center;padding:20px}
#auth-modal.open{display:flex}
.auth-box{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:40px;max-width:440px;width:100%;box-shadow:var(--shadow)}
.auth-logo{font-family:'Bebas Neue',sans-serif;font-size:2.4rem;color:var(--accent);margin-bottom:8px;letter-spacing:2px;text-align:center}
.auth-subtitle{color:var(--text2);font-size:.88rem;margin-bottom:30px;text-align:center}
.auth-input{width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:12px 14px;border-radius:10px;font-size:.93rem;margin-bottom:12px;transition:.2s;outline:none}
.auth-input:focus{border-color:var(--accent)}
.auth-btn{width:100%;background:var(--accent);color:var(--bg);font-weight:700;padding:12px;border-radius:10px;margin-bottom:14px;transition:.2s;cursor:pointer;font-size:.94rem}
.auth-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(232,184,75,.35)}
.auth-close{position:absolute;top:20px;right:20px;width:36px;height:36px;border-radius:50%;background:var(--surface2);border:1px solid var(--border);color:var(--text2);cursor:pointer;font-size:.9rem}

/* PROFILE MODAL */
#profile-modal{position:fixed;inset:0;z-index:8000;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;padding:20px}
#profile-modal.open{display:flex}
.profile-box{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:40px;max-width:520px;width:100%;box-shadow:var(--shadow);max-height:90vh;overflow-y:auto}
.form-group{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.form-group label{font-size:.82rem;font-weight:600;color:var(--text2)}
.form-group input,.form-group textarea{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:10px 12px;border-radius:10px;font-size:.9rem;transition:.2s;outline:none}
.form-group input:focus,.form-group textarea:focus{border-color:var(--accent)}
.form-actions{display:flex;gap:12px;margin-top:12px}
.btn-save{flex:1;background:var(--accent);color:var(--bg);padding:11px;border-radius:10px;font-weight:700;cursor:pointer;transition:.2s}
.btn-save:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(232,184,75,.3)}
.btn-cancel{flex:1;background:var(--surface2);color:var(--text);border:1px solid var(--border);padding:11px;border-radius:10px;font-weight:600;cursor:pointer;transition:.2s}
.btn-cancel:hover{border-color:var(--accent)}

/* SEARCH */
#search-overlay{position:fixed;inset:0;z-index:2000;background:rgba(0,0,0,.88);backdrop-filter:blur(14px);display:none;align-items:flex-start;justify-content:center;padding-top:120px;padding-left:20px;padding-right:20px}
#search-overlay.open{display:flex}
.search-box{width:min(680px,96vw);background:var(--surface);border:1px solid var(--border);border-radius:20px;overflow:hidden;box-shadow:var(--shadow)}
.search-input-row{display:flex;align-items:center;gap:14px;padding:18px 22px;border-bottom:1px solid var(--border)}
#search-input{flex:1;background:none;border:none;outline:none;font-size:1.05rem;color:var(--text)}
#search-input::placeholder{color:var(--text3)}
.search-close-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text2);width:32px;height:32px;border-radius:8px;font-size:.75rem;font-weight:700;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:.2s}
.search-close-btn:hover{background:var(--accent2);color:white;border-color:var(--accent2)}
#search-results-list{max-height:420px;overflow-y:auto}
.search-result-item{display:flex;align-items:center;gap:14px;padding:12px 22px;cursor:pointer;transition:.2s;border-bottom:1px solid rgba(255,255,255,.025)}
.search-result-item:hover{background:var(--surface2)}
.search-result-item img{width:44px;height:64px;object-fit:cover;border-radius:6px;flex-shrink:0;background:var(--surface2)}
.search-result-info strong{display:block;font-size:.93rem;margin-bottom:3px}
.search-result-info span{font-size:.76rem;color:var(--text2)}

/* TOAST */
#toast{position:fixed;bottom:28px;left:50%;z-index:9999;transform:translateX(-50%) translateY(60px);background:var(--surface2);color:var(--text);padding:12px 26px;border-radius:10px;font-size:.86rem;font-weight:600;border:1px solid var(--border);box-shadow:var(--shadow);transition:transform .3s cubic-bezier(.4,0,.2,1),opacity .3s;opacity:0;max-width:90vw;white-space:nowrap}
#toast.show{transform:translateX(-50%) translateY(0);opacity:1}

/* LOADING */
.loading{text-align:center;padding:50px 20px;color:var(--text2);grid-column:1/-1}
.spinner{display:inline-block;width:40px;height:40px;border:3px solid var(--surface2);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin-bottom:12px}
@keyframes spin{to{transform:rotate(360deg)}}

/* FOOTER */
footer{background:var(--surface);border-top:1px solid var(--border);padding:40px;text-align:center;color:var(--text2);font-size:.82rem}
.footer-logo{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;color:var(--accent);margin-bottom:10px;letter-spacing:3px}

/* RESPONSIVE */
@media(max-width:900px){
  #navbar{padding:0 16px;height:60px}
  .nav-links{display:none}
  .nav-logo{font-size:1.5rem}
  section{padding:35px 16px}
  .hero-content{padding:0 20px}
  #hero-title{font-size:2rem}
  #hero-desc{font-size:.85rem}
  #modal{width:100%;border-radius:16px}
  .modal-body{padding:20px}
  .modal-title{font-size:1.5rem}
  #browse-grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}
  .movie-card{flex:0 0 145px}
  .cast-item{width:88px}
}
@media(max-width:500px){
  .movie-card{flex:0 0 130px}
  .user-name{display:none}
  .btn-primary,.btn-ghost{padding:11px 20px;font-size:.85rem}
}
</style>
</head>
<body>

<div id="toast"></div>

<!-- AUTH MODAL -->
<div id="auth-modal">
  <button class="auth-close" onclick="closeAuth()">✕</button>
  <div class="auth-box">
    <div class="auth-logo">CINEARA</div>
    <p class="auth-subtitle">سجّل دخولك للمتابعة</p>
    <input class="auth-input" type="email" id="email-input" placeholder="بريدك الإلكتروني" />
    <input class="auth-input" type="password" id="pass-input" placeholder="كلمة المرور" />
    <button class="auth-btn" onclick="doLogin()">دخول</button>
    <div style="text-align:center;color:var(--text3);font-size:.78rem;margin:14px 0">أو</div>
    <button class="auth-btn" style="background:var(--surface2);color:var(--text)" onclick="googleAuth()">المتابعة بـ Google</button>
    <p style="text-align:center;color:var(--text2);font-size:.82rem;margin-top:14px">ليس لديك حساب؟ <a onclick="guestLogin()" style="color:var(--accent);cursor:pointer;font-weight:700">تابع كزائر</a></p>
  </div>
</div>

<!-- PROFILE MODAL -->
<div id="profile-modal">
  <div class="profile-box">
    <h3 style="font-size:1.2rem;margin-bottom:24px;text-align:center">الملف الشخصي</h3>
    <div class="form-group"><label>الاسم</label><input type="text" id="profile-name" /></div>
    <div class="form-group"><label>البريد</label><input type="email" id="profile-email" /></div>
    <div class="form-group"><label>نبذة</label><textarea id="profile-bio" rows="3"></textarea></div>
    <div class="form-actions">
      <button class="btn-save" onclick="saveProfile()">حفظ</button>
      <button class="btn-cancel" onclick="closeProfileModal()">إلغاء</button>
    </div>
  </div>
</div>

<!-- NAVBAR -->
<nav id="navbar">
  <div class="nav-logo">CINEARA</div>
  <div class="nav-links">
    <a class="active" onclick="switchPage('movies', event)">الأفلام</a>
    <a onclick="switchPage('matches', event)">كرة القدم</a>
  </div>
  <div class="nav-actions">
    <button class="btn-icon" onclick="openSearch()">🔍</button>
    <div class="user-profile" onclick="openProfileModal()">
      <div class="user-avatar" id="user-avatar">U</div>
      <span class="user-name" id="user-name">المستخدم</span>
    </div>
  </div>
</nav>

<!-- SEARCH -->
<div id="search-overlay">
  <div class="search-box">
    <div class="search-input-row">
      <span style="color:var(--text2);font-size:1.1rem">🔍</span>
      <input id="search-input" type="text" placeholder="ابحث عن فيلم أو مسلسل..." />
      <button class="search-close-btn" onclick="closeSearch()">ESC</button>
    </div>
    <div id="search-results-list"></div>
  </div>
</div>

<!-- MOVIE MODAL -->
<div class="modal-overlay" id="modal-overlay" onclick="if(event.target.id==='modal-overlay')closeModal()">
  <div id="modal">
    <div class="modal-backdrop" id="modal-backdrop">
      <button class="modal-close" onclick="closeModal()">ESC</button>
    </div>
    <div class="modal-body">
      <h2 class="modal-title" id="modal-title"></h2>
      <div class="modal-meta" id="modal-meta"></div>
      <p class="modal-desc" id="modal-desc"></p>

      <div class="player-container" id="player-container">
        <div class="player-placeholder" id="player-placeholder">
          <div class="player-placeholder-icon">▶</div>
          <div style="font-size:.9rem;font-weight:600">جارٍ تحميل الفيديو...</div>
        </div>
        <iframe id="pframe" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerpolicy="origin" style="display:none"></iframe>
      </div>

      <div class="quality-info" id="quality-info">
        <span class="quality-badge" id="quality-badge">HD</span>
        <span class="quality-info-text">📺 يتم التشغيل تلقائياً بأفضل جودة</span>
      </div>

      <div class="modal-actions">
        <button class="btn-primary" onclick="playNow()"><div class="play-arrow"></div>مشاهدة الآن</button>
        <button class="btn-ghost" id="fav-btn" onclick="toggleFavCurrent()">🤍 المفضّلة</button>
        <button class="btn-ghost" onclick="shareMovie()">🔗 مشاركة</button>
      </div>

      <div class="cast-section" id="cast-section"></div>

      <div style="margin-top:24px">
        <p style="font-size:.8rem;color:var(--text2);margin-bottom:8px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">تقييمك</p>
        <div class="stars-row" id="stars-row"></div>
      </div>
    </div>
  </div>
</div>

<!-- MAIN -->
<main>
  <div id="movies-page">
    <section id="hero" style="padding:0;max-width:none">
      <div id="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-eyebrow">الأفلام المميزة</div>
        <h1 id="hero-title"></h1>
        <div id="hero-meta"></div>
        <p id="hero-desc"></p>
        <div class="hero-actions">
          <button class="btn-primary" onclick="playHero()"><div class="play-arrow"></div>مشاهدة الآن</button>
          <button class="btn-ghost" onclick="addHeroToFav()">🤍 أضف للمفضّلة</button>
        </div>
      </div>
    </section>

    <section>
      <h2 class="sec-title">🔥 رائج الآن</h2>
      <div class="cards-row" id="trending-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>

    <section>
      <h2 class="sec-title">🎬 أفلام شائعة</h2>
      <div class="cards-row" id="popular-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>

    <section>
      <h2 class="sec-title">📺 مسلسلات</h2>
      <div class="cards-row" id="series-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>

    <section>
      <h2 class="sec-title">🎭 تصفّح الأفلام</h2>
      <div class="genre-strip" id="genre-strip"></div>
      <div id="browse-grid"><div class="loading"><div class="spinner"></div></div></div>
    </section>
  </div>

  <div id="matches-page" style="display:none">
    <section>
      <h2 class="sec-title">⚽ مباريات كرة القدم</h2>
      <div id="matches-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px"></div>
    </section>
  </div>
</main>

<footer>
  <div class="footer-logo">CINEARA PRO</div>
  <p>منصة أفلام وكرة قدم — جميع الحقوق محفوظة 2025</p>
</footer>

<script>
const IMG_W = 'https://image.tmdb.org/t/p/w500';
const IMG_O = 'https://image.tmdb.org/t/p/original';
const SOURCES = __SOURCES__;

const S = {
  user: JSON.parse(localStorage.getItem('ca_user') || 'null'),
  fav: JSON.parse(localStorage.getItem('ca_favs') || '[]'),
  ratings: JSON.parse(localStorage.getItem('ca_ratings') || '{}'),
  tmdbMovies: [],
  currentMovie: null,
  currentSourceIdx: 0,
};

const genreMap = {28:'أكشن',12:'مغامرة',16:'أنيميشن',35:'كوميديا',80:'جريمة',18:'دراما',10751:'عائلي',14:'خيال',36:'تاريخي',27:'رعب',10749:'رومانسي',878:'خيال علمي',53:'إثارة'};

document.addEventListener('DOMContentLoaded', () => {
  if (S.user) {
    document.getElementById('auth-modal').classList.remove('open');
    updateUserUI();
    init();
  } else {
    document.getElementById('auth-modal').classList.add('open');
  }
  window.addEventListener('scroll', () => {
    document.getElementById('navbar').classList.toggle('scrolled', window.scrollY > 40);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeModal(); closeSearch(); closeProfileModal(); }
  });
});

function closeAuth() { document.getElementById('auth-modal').classList.remove('open'); }

function doLogin() {
  const email = document.getElementById('email-input').value.trim();
  const pass = document.getElementById('pass-input').value.trim();
  if (!email || !email.includes('@')) return showToast('أدخل بريداً صحيحاً');
  if (!pass || pass.length < 3) return showToast('كلمة المرور قصيرة');
  const user = { id: Date.now().toString(36), name: email.split('@')[0], email: email, bio: '', avatar: '' };
  S.user = user;
  localStorage.setItem('ca_user', JSON.stringify(user));
  document.getElementById('auth-modal').classList.remove('open');
  updateUserUI();
  showToast('✅ تم تسجيل الدخول');
  init();
}

function guestLogin() {
  const user = { id: 'guest_' + Date.now(), name: 'زائر', email: 'guest@local', bio: '', avatar: '' };
  S.user = user;
  localStorage.setItem('ca_user', JSON.stringify(user));
  document.getElementById('auth-modal').classList.remove('open');
  updateUserUI();
  showToast('✅ دخلت كزائر');
  init();
}

function googleAuth() {
  const name = prompt('اسمك:');
  if (!name) return;
  const user = { id: 'google_' + Date.now(), name: name, email: name.toLowerCase().replace(/\s/g, '') + '@gmail.com', bio: '', avatar: '' };
  S.user = user;
  localStorage.setItem('ca_user', JSON.stringify(user));
  document.getElementById('auth-modal').classList.remove('open');
  updateUserUI();
  showToast('✅ دخلت عبر Google');
  init();
}

function updateUserUI() {
  if (!S.user) return;
  const initial = (S.user.name || 'U')[0].toUpperCase();
  document.getElementById('user-avatar').textContent = initial;
  document.getElementById('user-name').textContent = S.user.name;
}

function openProfileModal() {
  if (!S.user) return;
  document.getElementById('profile-name').value = S.user.name || '';
  document.getElementById('profile-email').value = S.user.email || '';
  document.getElementById('profile-bio').value = S.user.bio || '';
  document.getElementById('profile-modal').classList.add('open');
}

function closeProfileModal() { document.getElementById('profile-modal').classList.remove('open'); }

function saveProfile() {
  if (!S.user) return;
  S.user.name = document.getElementById('profile-name').value || S.user.name;
  S.user.bio = document.getElementById('profile-bio').value || '';
  localStorage.setItem('ca_user', JSON.stringify(S.user));
  updateUserUI();
  closeProfileModal();
  showToast('✅ تم حفظ البيانات');
}

async function fetchMovies(type = 'popular', genreId = null) {
  try {
    let url = genreId ? `/api/genre/movie/${genreId}` : `/api/${type === 'popular' ? 'popular/movie' : type === 'top_rated' ? 'top_rated/movie' : 'trending'}`;
    const r = await fetch(url);
    const d = await r.json();
    return d.results || [];
  } catch(e) { console.error(e); return []; }
}

async function fetchSeries() {
  try {
    const r = await fetch('/api/popular/tv');
    const d = await r.json();
    return d.results || [];
  } catch(e) { return []; }
}

function buildCard(m) {
  const div = document.createElement('div');
  div.className = 'movie-card';
  const type = m.media_type || (m.name ? 'tv' : 'movie');
  const title = m.title || m.name || '?';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
  const isFav = S.fav.includes(m.id);
  div.innerHTML = '<div class="card-poster">' +
    (m.poster_path ? '<img src="' + IMG_W + m.poster_path + '" loading="lazy" alt="' + title + '" />' : '<div style="width:100%;height:100%;background:var(--surface2);display:flex;align-items:center;justify-content:center;font-size:.8rem;color:var(--text3)">لا صورة</div>') +
    '<button class="card-fav' + (isFav ? ' active' : '') + '" onclick="event.stopPropagation();toggleFav(' + m.id + ',this)">♥</button>' +
    '<div class="card-rating">★ ' + rating + '</div></div>' +
    '<div class="card-info"><div class="card-title">' + title + '</div><div class="card-year">' + year + '</div></div>';
  div.onclick = () => openModal(m.id, type);
  return div;
}

async function init() {
  const trending = await fetchMovies('trending');
  const popular = await fetchMovies('popular');
  const series = await fetchSeries();
  S.tmdbMovies = [...trending, ...popular, ...series];
  renderHero(trending);
  renderRow('trending-row', trending);
  renderRow('popular-row', popular);
  renderRow('series-row', series);
  renderGenres();
  renderGrid(popular);
  renderMatches();
}

function renderHero(movies) {
  const m = movies.find(x => x.backdrop_path) || movies[0];
  if (!m) return;
  S.currentMovie = m;
  document.getElementById('hero-bg').style.backgroundImage = "url('" + IMG_O + m.backdrop_path + "')";
  document.getElementById('hero-title').textContent = m.title || m.name || '?';
  document.getElementById('hero-meta').innerHTML = '<span class="accent">★ ' + (m.vote_average?.toFixed(1) || 'N/A') + '</span><span class="sep">|</span><span>' + (m.release_date || m.first_air_date || '').substring(0, 4) + '</span><span class="sep">|</span><span>' + (m.media_type === 'tv' ? 'مسلسل' : 'فيلم') + '</span>';
  document.getElementById('hero-desc').textContent = m.overview || '';
}

function renderRow(id, movies) {
  const row = document.getElementById(id);
  row.innerHTML = '';
  movies.slice(0, 15).forEach(m => row.appendChild(buildCard(m)));
}

function renderGrid(movies) {
  const grid = document.getElementById('browse-grid');
  grid.innerHTML = '';
  movies.slice(0, 20).forEach(m => grid.appendChild(buildCard(m)));
}

function renderGenres() {
  const strip = document.getElementById('genre-strip');
  const genres = [{name:'الكل', id:null}, {name:'أكشن', id:28}, {name:'دراما', id:18}, {name:'كوميديا', id:35}, {name:'خيال علمي', id:878}, {name:'رعب', id:27}, {name:'رومانسي', id:10749}, {name:'مغامرة', id:12}];
  strip.innerHTML = genres.map((g, i) => '<button class="genre-chip' + (i === 0 ? ' active' : '') + '" onclick="filterGenre(' + (g.id || 'null') + ', this)">' + g.name + '</button>').join('');
}

async function filterGenre(gid, btn) {
  document.querySelectorAll('#genre-strip .genre-chip').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const grid = document.getElementById('browse-grid');
  grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  const movies = gid ? await fetchMovies('popular', gid) : await fetchMovies('popular');
  renderGrid(movies);
}

function openSearch() {
  document.getElementById('search-overlay').classList.add('open');
  setTimeout(() => document.getElementById('search-input').focus(), 100);
}

function closeSearch() {
  document.getElementById('search-overlay').classList.remove('open');
  document.getElementById('search-input').value = '';
  document.getElementById('search-results-list').innerHTML = '';
}

document.getElementById('search-input')?.addEventListener('input', async (e) => {
  const q = e.target.value.trim();
  const list = document.getElementById('search-results-list');
  if (!q) { list.innerHTML = ''; return; }
  list.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  try {
    const r = await fetch('/api/search?q=' + encodeURIComponent(q));
    const d = await r.json();
    const results = (d.results || []).slice(0, 10);
    if (!results.length) { list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text2)">لا توجد نتائج</div>'; return; }
    list.innerHTML = results.map(m => {
      const type = m.media_type || 'movie';
      const title = m.title || m.name || '?';
      return '<div class="search-result-item" onclick="closeSearch();openModal(' + m.id + ',\'' + type + '\')">' +
        (m.poster_path ? '<img src="' + IMG_W + m.poster_path + '" />' : '<div style="width:44px;height:64px;background:var(--surface2);border-radius:6px"></div>') +
        '<div class="search-result-info"><strong>' + title + '</strong><span>' + (m.release_date || m.first_air_date || '').substring(0, 4) + ' • ★ ' + (m.vote_average?.toFixed(1) || 'N/A') + '</span></div></div>';
    }).join('');
  } catch(e) { list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--accent2)">خطأ في البحث</div>'; }
});

async function openModal(id, type = 'movie') {
  const m = S.tmdbMovies.find(x => x.id === id);
  S.currentMovie = { id: id, type: type };
  document.getElementById('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
  const pframe = document.getElementById('pframe');
  const placeholder = document.getElementById('player-placeholder');
  pframe.style.display = 'none';
  pframe.src = 'about:blank';
  placeholder.style.display = 'flex';
  
  if (m) {
    document.getElementById('modal-title').textContent = m.title || m.name || '?';
    document.getElementById('modal-meta').innerHTML = '<span class="accent">★ ' + (m.vote_average?.toFixed(1) || 'N/A') + '</span><span class="sep">|</span><span>' + (m.release_date || m.first_air_date || '').substring(0, 4) + '</span>';
    document.getElementById('modal-desc').textContent = m.overview || 'لا يوجد وصف متاح';
    if (m.backdrop_path) document.getElementById('modal-backdrop').style.backgroundImage = "url('" + IMG_O + m.backdrop_path + "')";
  }
  
  try {
    const r = await fetch('/api/' + type + '/' + id);
    const full = await r.json();
    document.getElementById('modal-title').textContent = full.title || full.name || '?';
    document.getElementById('modal-meta').innerHTML = '<span class="accent">★ ' + (full.vote_average?.toFixed(1) || 'N/A') + '</span><span class="sep">|</span><span>' + (full.release_date || full.first_air_date || '').substring(0, 4) + '</span><span class="sep">|</span><span>⏱ ' + (full.runtime || '?') + ' د</span>';
    document.getElementById('modal-desc').textContent = full.overview || 'لا يوجد وصف متاح';
    const best = pickBestSource(full, type);
    S.currentSourceIdx = best.idx;
    const qb = document.getElementById('quality-badge');
    qb.textContent = best.quality;
    qb.className = 'quality-badge ' + (best.quality === '4K' ? 'q4k' : best.quality === 'HD' ? 'qhd' : 'qsd');
    const cast = full.credits?.cast?.slice(0, 8) || [];
    const castSection = document.getElementById('cast-section');
    if (cast.length) {
      castSection.innerHTML = '<h4>طاقم التمثيل</h4><div class="cast-list">' + cast.map(c => {
        const avatar = c.profile_path ? '<img src="https://image.tmdb.org/t/p/w185' + c.profile_path + '" />' : (c.name || '?')[0];
        return '<div class="cast-item"><div class="cast-avatar">' + avatar + '</div><div class="cast-name">' + (c.name || '?') + '</div><div class="cast-role">' + (c.character || '') + '</div></div>';
      }).join('') + '</div>';
    } else { castSection.innerHTML = ''; }
    const ur = S.ratings[id] || 0;
    document.getElementById('stars-row').innerHTML = [1,2,3,4,5].map(n => '<button class="star-btn' + (n <= ur ? ' lit' : '') + '" onclick="rateMovie(' + id + ',' + n + ')">★</button>').join('');
    updateFavBtn(id);
    setTimeout(() => startStream(best.idx, 1, 1), 300);
  } catch(e) { console.error(e); }
}

function pickBestSource(m, type) {
  let preferred = 'HD';
  const year = parseInt((m.release_date || m.first_air_date || '2020').substring(0, 4));
  const cy = new Date().getFullYear();
  if (cy - year <= 3) preferred = '4K';
  if ((m.vote_average || 0) >= 8.0) preferred = '4K';
  if (type === 'tv') preferred = 'HD';
  let idx = 0;
  for (let i = 0; i < SOURCES.length; i++) { if (SOURCES[i].q === preferred) { idx = i; break; } }
  return { idx, quality: SOURCES[idx].q };
}

function startStream(idx, season, episode) {
  if (!S.currentMovie) return;
  const pframe = document.getElementById('pframe');
  const placeholder = document.getElementById('player-placeholder');
  placeholder.style.display = 'flex';
  pframe.style.display = 'none';
  const url = '/player?type=' + S.currentMovie.type + '&id=' + S.currentMovie.id + '&source=' + idx + '&season=' + (season || 1) + '&episode=' + (episode || 1);
  pframe.src = url;
  S.currentSourceIdx = idx;
  pframe.onload = () => { setTimeout(() => { placeholder.style.display = 'none'; pframe.style.display = 'block'; }, 500); };
}

function playNow() {
  if (!S.currentMovie) return;
  startStream(S.currentSourceIdx, 1, 1);
  showToast('▶ جاري التشغيل...');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
  const pframe = document.getElementById('pframe');
  if (pframe) pframe.src = 'about:blank';
}

function toggleFav(id, btn) {
  if (S.fav.includes(id)) { S.fav = S.fav.filter(x => x !== id); showToast('💔 حُذف من المفضلة'); }
  else { S.fav.push(id); showToast('❤️ أُضيف للمفضلة'); }
  localStorage.setItem('ca_favs', JSON.stringify(S.fav));
  if (btn) btn.classList.toggle('active', S.fav.includes(id));
}

function toggleFavCurrent() {
  if (!S.currentMovie) return;
  toggleFav(S.currentMovie.id);
  updateFavBtn(S.currentMovie.id);
}

function updateFavBtn(id) {
  const btn = document.getElementById('fav-btn');
  btn.textContent = S.fav.includes(id) ? '❤️ في المفضلة' : '🤍 المفضّلة';
}

function addHeroToFav() { if (S.currentMovie) toggleFav(S.currentMovie.id); }

function rateMovie(id, val) {
  S.ratings[id] = val;
  localStorage.setItem('ca_ratings', JSON.stringify(S.ratings));
  document.querySelectorAll('#stars-row .star-btn').forEach((b, i) => b.classList.toggle('lit', i < val));
  showToast('⭐ تم التقييم ' + val + '/5');
}

function shareMovie() {
  if (!S.currentMovie) return;
  const url = window.location.origin + '/?m=' + S.currentMovie.type + '_' + S.currentMovie.id;
  if (navigator.share) navigator.share({ url: url }).catch(() => {});
  else navigator.clipboard.writeText(url).then(() => showToast('✅ تم نسخ الرابط')).catch(() => {});
}

const MATCHES = [
  { league:'الدوري السعودي', team1:'النصر', team2:'الهلال', s1:'2', s2:'1', status:'live', ch:'SSC', date:'اليوم' },
  { league:'الدوري المصري', team1:'الأهلي', team2:'الزمالك', s1:'-', s2:'-', status:'upcoming', ch:'ON TV', date:'19:00' },
  { league:'الإسباني', team1:'ريال مدريد', team2:'برشلونة', s1:'3', s2:'2', status:'finished', ch:'beIN', date:'أمس' },
  { league:'أبطال أوروبا', team1:'مان سيتي', team2:'ريال مدريد', s1:'1', s2:'1', status:'live', ch:'beIN', date:'الآن' },
];

function renderMatches() {
  const grid = document.getElementById('matches-grid');
  grid.innerHTML = MATCHES.map(m => {
    const statusText = m.status === 'live' ? '🔴 مباشر' : m.status === 'upcoming' ? '⏰ ' + m.date : '✅ انتهت';
    return '<div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px">' +
      '<div style="font-size:.72rem;font-weight:700;color:var(--accent);text-transform:uppercase;margin-bottom:10px">' + m.league + '</div>' +
      '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:12px">' +
      '<div style="display:flex;justify-content:space-between;align-items:center"><span style="font-weight:600">' + m.team1 + '</span><span style="font-family:Bebas Neue;font-size:1.4rem;color:var(--accent)">' + m.s1 + '</span></div>' +
      '<div style="display:flex;justify-content:space-between;align-items:center"><span style="font-weight:600">' + m.team2 + '</span><span style="font-family:Bebas Neue;font-size:1.4rem;color:var(--accent)">' + m.s2 + '</span></div></div>' +
      '<div style="display:flex;justify-content:space-between;font-size:.74rem;color:var(--text2)"><span>' + statusText + '</span><span>' + m.ch + '</span></div></div>';
  }).join('');
}

function switchPage(page, event) {
  if (event) event.preventDefault();
  document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
  if (event && event.target) event.target.classList.add('active');
  document.getElementById('movies-page').style.display = page === 'movies' ? 'block' : 'none';
  document.getElementById('matches-page').style.display = page === 'matches' ? 'block' : 'none';
}

function playHero() {
  if (!S.currentMovie) return;
  openModal(S.currentMovie.id, S.currentMovie.media_type || 'movie');
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 2600);
}

console.log('[ONYX] Loaded. Sources:', SOURCES.length);
</script>
</body>
</html>
"""


# ══════════════════════════════════════════════════════════
# PLAYER HTML
# ══════════════════════════════════════════════════════════
PLAYER_HTML = r"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>*{margin:0;padding:0}html,body,iframe{width:100%;height:100%;background:#000;border:none;overflow:hidden}</style></head>
<body>
<iframe id="player" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerpolicy="origin"></iframe>
<script>
const SOURCES = __SOURCES__;
const p = new URLSearchParams(location.search);
const type = p.get('type') || 'movie';
const id = p.get('id');
const idx = parseInt(p.get('source') || '0');
const season = p.get('season') || '1';
const episode = p.get('episode') || '1';
const src = SOURCES[idx] || SOURCES[0];
if (src) {
  let url = src[type] || src.movie;
  url = url.replace(/{id}/g, id).replace(/{s}/g, season).replace(/{e}/g, episode);
  url = url.replace(/{season}/g, season).replace(/{episode}/g, episode);
  document.getElementById('player').src = url;
}
</script>
</body></html>
"""


# ══════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template_string(INDEX_HTML.replace("__SOURCES__", SOURCES_JSON))


@app.route("/player")
def player():
    return render_template_string(PLAYER_HTML.replace("__SOURCES__", SOURCES_JSON))


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


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()[:100]
    if not q:
        return jsonify({"results": []})
    return jsonify(tmdb("/search/multi", {"query": q}))


@app.route("/api/movie/<int:mid>")
def api_movie(mid):
    return jsonify(tmdb(f"/movie/{mid}", {"append_to_response": "credits,videos,similar"}))


@app.route("/api/tv/<int:tid>")
def api_tv(tid):
    return jsonify(tmdb(f"/tv/{tid}", {"append_to_response": "credits,videos,similar"}))


@app.route("/api/tv/<int:tid>/season/<int:s>")
def api_tv_season(tid, s):
    return jsonify(tmdb(f"/tv/{tid}/season/{s}"))


@app.route("/api/genre/<mt>/<int:gid>")
def api_genre(mt, gid):
    if mt not in ("movie", "tv"):
        return jsonify({"error": "invalid"}), 400
    return jsonify(tmdb(f"/discover/{mt}", {"with_genres": gid, "sort_by": "popularity.desc"}))


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ONYX CINEMA v8.0",
        "tmdb": "ok" if TMDB_API_KEY else "missing",
        "sources": len(PLAYER_SOURCES),
        "admin": ADMIN_EMAIL,
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
