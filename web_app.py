# -*- coding: utf-8 -*-
"""ONYX CINEMA v4.0"""

from flask import Flask, jsonify, request
import os
import time
import json
import urllib.request
import urllib.parse
from collections import defaultdict

app = Flask(__name__)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"

# SECURITY
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


@app.after_request
def sec(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "SAMEORIGIN"
    r.headers["X-XSS-Protection"] = "1; mode=block"
    return r


# 20 SOURCES
PLAYER_SOURCES = [
    {"name": "VidLink 4K", "q": "4K", "ads": "none",
     "movie": "https://vidlink.pro/movie/{id}", "tv": "https://vidlink.pro/tv/{id}/{s}/{e}"},
    {"name": "Videasy 4K", "q": "4K", "ads": "none",
     "movie": "https://player.videasy.net/movie/{id}", "tv": "https://player.videasy.net/tv/{id}/{s}/{e}"},
    {"name": "AutoEmbed", "q": "HD", "ads": "none",
     "movie": "https://player.autoembed.cc/embed/movie/{id}", "tv": "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}"},
    {"name": "SmashyStream", "q": "HD", "ads": "none",
     "movie": "https://player.smashy.stream/movie/{id}", "tv": "https://player.smashy.stream/tv/{id}?s={s}&e={e}"},
    {"name": "VidPlus", "q": "HD", "ads": "low",
     "movie": "https://vidplus.to/embed/movie/{id}", "tv": "https://vidplus.to/embed/tv/{id}/{s}/{e}"},
    {"name": "VidSrc XYZ", "q": "HD", "ads": "low",
     "movie": "https://vidsrc.xyz/embed/movie?tmdb={id}", "tv": "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}"},
    {"name": "2Embed.to", "q": "HD", "ads": "low",
     "movie": "https://www.2embed.to/embed/tmdb/movie?id={id}", "tv": "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"},
    {"name": "Embed.su", "q": "HD", "ads": "low",
     "movie": "https://embed.su/embed/movie/{id}", "tv": "https://embed.su/embed/tv/{id}/{s}/{e}"},
    {"name": "MoviesAPI", "q": "HD", "ads": "low",
     "movie": "https://moviesapi.club/movie/{id}", "tv": "https://moviesapi.club/tv/{id}-{s}-{e}"},
    {"name": "VidSrc IO", "q": "HD", "ads": "low",
     "movie": "https://vidsrc.io/embed/movie/{id}", "tv": "https://vidsrc.io/embed/tv/{id}/{s}/{e}"},
    {"name": "VidSrc CC", "q": "SD", "ads": "medium",
     "movie": "https://vidsrc.cc/v2/embed/movie/{id}", "tv": "https://vidsrc.cc/v2/embed/tv/{id}/{s}/{e}"},
    {"name": "VidSrc WTF", "q": "SD", "ads": "medium",
     "movie": "https://vidsrc.wtf/api/1/movie/?id={id}", "tv": "https://vidsrc.wtf/api/1/tv/?id={id}&s={s}&e={e}"},
    {"name": "VidSrc DEV", "q": "SD", "ads": "medium",
     "movie": "https://vidsrc.dev/embed/movie/{id}", "tv": "https://vidsrc.dev/embed/tv/{id}/{s}/{e}"},
    {"name": "VidSrc.to", "q": "SD", "ads": "medium",
     "movie": "https://vidsrc.to/embed/movie/{id}", "tv": "https://vidsrc.to/embed/tv/{id}/{s}/{e}"},
    {"name": "VidSrc.me", "q": "SD", "ads": "medium",
     "movie": "https://vidsrc.me/embed/movie?tmdb={id}", "tv": "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}"},
    {"name": "SuperEmbed", "q": "SD", "ads": "high",
     "movie": "https://multiembed.mov/?video_id={id}&tmdb=1", "tv": "https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}"},
    {"name": "MultiEmbed", "q": "SD", "ads": "high",
     "movie": "https://multiembed.mov/directstream.php?video_id={id}&tmdb=1", "tv": "https://multiembed.mov/directstream.php?video_id={id}&tmdb=1&s={s}&e={e}"},
    {"name": "2Embed.cc", "q": "SD", "ads": "high",
     "movie": "https://www.2embed.cc/embed/{id}", "tv": "https://www.2embed.cc/embedtv/{id}&s={s}&e={e}"},
    {"name": "VidSrc.lol", "q": "SD", "ads": "high",
     "movie": "https://vidsrc.lol/embed/movie/{id}", "tv": "https://vidsrc.lol/embed/tv/{id}/{s}/{e}"},
    {"name": "Player4u", "q": "SD", "ads": "high",
     "movie": "https://player4u.xyz/embed/movie/{id}", "tv": "https://player4u.xyz/embed/tv/{id}/{s}/{e}"},
]
SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)


def tmdb(ep, params=None):
    if not TMDB_API_KEY:
        return {"error": "no key", "results": []}
    p = params or {}
    p["api_key"] = TMDB_API_KEY
    p["language"] = "ar"
    url = f"{TMDB_BASE}{ep}?{urllib.parse.urlencode(p)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/4.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#141414">
<title>ONYX CINEMA</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#141414;--bg2:#181818;--surface:#242424;--surface2:#2f2f2f;--accent:#e50914;--gold:#f5c518;--green:#22c55e;--text:#f0f0f0;--text2:#aaa;--text3:#666;--border:rgba(255,255,255,0.1)}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'Cairo',sans-serif;overflow-x:hidden}
a{text-decoration:none;color:inherit}
img{max-width:100%;display:block}
button{cursor:pointer;font-family:'Cairo',sans-serif;border:none}
input,textarea{font-family:'Cairo',sans-serif}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-track{background:var(--bg2)}
::-webkit-scrollbar-thumb{background:var(--accent);border-radius:4px}

#nav{position:fixed;top:0;left:0;right:0;z-index:1000;height:60px;padding:0 3%;display:flex;align-items:center;background:linear-gradient(180deg,rgba(0,0,0,.95) 0%,transparent 100%);transition:.3s}
#nav.solid{background:#141414;box-shadow:0 2px 20px rgba(0,0,0,.8)}
.nav-inner{width:100%;display:flex;align-items:center;gap:1rem;max-width:1900px;margin:0 auto}
.logo{font-family:'Bebas Neue',sans-serif;font-size:1.9rem;color:var(--accent);letter-spacing:.08em;flex-shrink:0}
.nav-links{display:flex;gap:.2rem;flex:1;list-style:none}
.nav-links a{padding:.5rem .9rem;font-size:.85rem;font-weight:600;color:var(--text2);transition:.2s;cursor:pointer;border-radius:4px}
.nav-links a:hover,.nav-links a.on{color:#fff;background:rgba(255,255,255,.05)}
.nav-search{display:flex;align-items:center;background:rgba(0,0,0,.75);border:1px solid var(--border);border-radius:6px;overflow:hidden}
.nav-search input{background:transparent;border:none;outline:none;color:#fff;padding:.45rem .9rem;width:200px;font-size:.82rem}
.nav-search button{background:var(--accent);color:#fff;padding:.45rem .9rem;font-size:.8rem;font-weight:700}
.btn-login{background:var(--accent);color:#fff;padding:.5rem 1.1rem;border-radius:6px;font-size:.82rem;font-weight:700;cursor:pointer}
.mobile-menu-btn{display:none;background:transparent;color:#fff;font-size:1.4rem;padding:.3rem .6rem;cursor:pointer}

.hero{position:relative;height:85vh;min-height:520px;overflow:hidden;display:flex;align-items:center;margin-top:60px}
.hero-bg{position:absolute;inset:0}
.hero-slide{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transition:opacity 1.2s}
.hero-slide.on{opacity:1}
.hero-ov{position:absolute;inset:0;background:linear-gradient(90deg,#141414 0%,rgba(20,20,20,.5) 50%,transparent 100%),linear-gradient(0deg,#141414 0%,transparent 40%)}
.hero-body{position:relative;z-index:2;max-width:680px;padding:0 4%}
.hero-badge{display:inline-block;background:var(--accent);color:#fff;font-size:.7rem;font-weight:700;padding:.28rem .75rem;border-radius:4px;margin-bottom:.9rem}
.hero-title{font-size:clamp(1.8rem,4.5vw,3.5rem);font-weight:900;line-height:1.1;color:#fff;margin-bottom:.9rem;text-shadow:0 4px 30px rgba(0,0,0,.6)}
.hero-meta{display:flex;gap:.8rem;color:var(--text2);font-size:.9rem;font-weight:600;margin-bottom:.9rem;flex-wrap:wrap;align-items:center}
.hero-meta .rating{color:var(--gold)}
.hero-desc{color:#ddd;font-size:.9rem;line-height:1.6;max-width:560px;margin-bottom:1.3rem;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.btn-play{background:#fff;color:#000;padding:.7rem 1.8rem;border-radius:6px;font-size:.95rem;font-weight:700;transition:.2s;cursor:pointer}
.btn-play:hover{background:rgba(255,255,255,.85);transform:scale(1.03)}

.section{padding:1.5rem 4%;max-width:1900px;margin:0 auto}
.sec-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem}
.sec-title{font-size:1.3rem;font-weight:700;color:#fff}
.row{display:flex;gap:.7rem;overflow-x:auto;padding:1rem 0;scroll-snap-type:x mandatory;scrollbar-width:thin}
.row::-webkit-scrollbar{height:6px}
.card{flex:0 0 170px;scroll-snap-align:start;background:var(--surface);border-radius:6px;overflow:hidden;cursor:pointer;transition:transform .3s,box-shadow .3s;position:relative}
.card:hover{transform:scale(1.05);z-index:5;box-shadow:0 15px 40px rgba(0,0,0,.9)}
.card img{width:100%;aspect-ratio:2/3;object-fit:cover;background:var(--surface2)}
.card-info{padding:.55rem}
.card-title{font-size:.82rem;font-weight:700;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:.15rem}
.card-meta{font-size:.7rem;color:var(--text2);display:flex;gap:.4rem;flex-wrap:wrap}
.card-meta .rating{color:var(--gold);font-weight:700}

.mo{position:fixed;inset:0;background:rgba(0,0,0,.95);backdrop-filter:blur(8px);z-index:5000;display:none;align-items:flex-start;justify-content:center;padding:1rem;overflow-y:auto}
.mo.on{display:flex}
.mo-box{background:#181818;border:1px solid var(--border);border-radius:12px;padding:1.5rem;width:98%;max-width:1200px;position:relative;margin:auto}
.mo-close{position:absolute;top:.8rem;left:.8rem;background:var(--surface2);color:#fff;width:36px;height:36px;border-radius:50%;font-size:1rem;z-index:10;cursor:pointer;transition:.2s}
.mo-close:hover{background:var(--accent)}

.pwrap{display:none;margin-bottom:1.2rem}
.pwrap.on{display:block}
.pcont{width:100%;aspect-ratio:16/9;background:#000;border-radius:6px;overflow:hidden;margin-bottom:.6rem}
.pcont iframe{width:100%;height:100%;border:none}
.psrcs{display:flex;gap:.4rem;overflow-x:auto;padding:.4rem;background:var(--surface);border-radius:6px;border:1px solid var(--border)}
.psrcs::-webkit-scrollbar{height:4px}
.psrc{background:var(--bg2);border:1px solid var(--border);color:var(--text2);padding:.35rem .7rem;border-radius:5px;font-size:.7rem;font-weight:600;white-space:nowrap;cursor:pointer;transition:.2s}
.psrc.on{background:var(--accent);border-color:var(--accent);color:#fff}
.psrc:hover:not(.on){color:var(--accent);border-color:var(--accent)}

.mh{display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:1.2rem}
.mp{width:180px;flex-shrink:0;border-radius:6px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.8)}
.mp img{width:100%}
.mi{flex:1;min-width:250px}
.mi h2{font-size:1.6rem;margin-bottom:.5rem;font-weight:800;line-height:1.2}
.mm{display:flex;gap:.6rem;flex-wrap:wrap;color:var(--text2);font-size:.85rem;margin-bottom:.9rem;align-items:center}
.mm .rating{color:var(--gold);font-weight:700;background:rgba(245,197,24,.1);padding:.15rem .5rem;border-radius:4px}
.mm .lang{background:var(--surface2);color:#fff;padding:.15rem .5rem;border-radius:4px;font-weight:700;text-transform:uppercase;font-size:.75rem}
.mg{color:var(--text2);font-size:.85rem;margin-bottom:.9rem}
.md{color:#ccc;line-height:1.7;font-size:.9rem;margin-bottom:1.2rem}
.btn-watch{background:var(--accent);color:#fff;padding:.7rem 1.8rem;border-radius:6px;font-size:.95rem;font-weight:700;transition:.2s;cursor:pointer}
.btn-watch:hover{background:#ff1e27;transform:scale(1.03)}

.seasons-sec{margin-top:1.2rem;border-top:1px solid var(--border);padding-top:1.2rem}
.seasons-sec h3{font-size:1.1rem;margin-bottom:.9rem}
.sel{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.9rem}
.sbtn{background:var(--surface);border:1px solid var(--border);color:var(--text2);padding:.4rem .9rem;border-radius:6px;font-size:.8rem;font-weight:700;cursor:pointer;transition:.2s}
.sbtn.on,.sbtn:hover{background:var(--accent);border-color:var(--accent);color:#fff}
.egrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.8rem}
.ecard{background:var(--surface);border-radius:6px;overflow:hidden;border:1px solid var(--border);cursor:pointer;transition:.2s}
.ecard:hover{transform:translateY(-3px);border-color:var(--accent)}
.ethumb{width:100%;aspect-ratio:16/9;object-fit:cover;background:var(--surface2)}
.edet{padding:.6rem}
.etitle{font-size:.8rem;font-weight:700;margin-bottom:.15rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.enum{font-size:.68rem;color:var(--accent);font-weight:700}

.cmt-sec{margin-top:1.2rem;border-top:1px solid var(--border);padding-top:1.2rem}
.cmt-sec h3{font-size:1.1rem;margin-bottom:.9rem}
.cmt-form{display:flex;gap:.6rem;margin-bottom:.9rem;flex-wrap:wrap}
.cmt-form textarea{flex:1;min-width:180px;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:#fff;padding:.55rem;font-size:.85rem;min-height:55px;resize:vertical;outline:none}
.cmt-form textarea:focus{border-color:var(--accent)}
.cmt-send{background:var(--accent);color:#fff;padding:.55rem 1.3rem;border-radius:6px;font-weight:700;align-self:flex-end;cursor:pointer}
.cmt-list{display:flex;flex-direction:column;gap:.6rem}
.cmt{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.7rem;display:flex;gap:.6rem}
.cmt-ava{width:34px;height:34px;border-radius:50%;object-fit:cover;flex-shrink:0}
.cmt-body{flex:1}
.cmt-head{display:flex;gap:.5rem;align-items:center;margin-bottom:.25rem}
.cmt-name{font-size:.82rem;font-weight:700}
.cmt-date{font-size:.7rem;color:var(--text3)}
.cmt-text{font-size:.82rem;color:#ccc;line-height:1.6}

.auth-logo{text-align:center;font-family:'Bebas Neue',sans-serif;font-size:1.9rem;color:var(--accent);margin-bottom:.3rem;letter-spacing:.08em}
.auth-title{text-align:center;font-size:1.2rem;font-weight:700;margin-bottom:1.2rem}
.fg{margin-bottom:.9rem}
.fg label{display:block;font-size:.8rem;color:var(--text2);font-weight:600;margin-bottom:.25rem}
.fg input,.fg textarea{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:#fff;padding:.6rem;font-size:.85rem;outline:none;transition:.2s}
.fg input:focus{border-color:var(--accent)}
.btn-sub{width:100%;background:var(--accent);color:#fff;padding:.7rem;border-radius:6px;font-size:.9rem;font-weight:700;margin-top:.4rem;cursor:pointer}
.btn-sub:hover{background:#ff1e27}
.oauth-btns{display:flex;gap:.5rem;margin-bottom:.9rem}
.oauth-btn{flex:1;background:var(--surface);border:1px solid var(--border);color:#fff;padding:.6rem;border-radius:6px;font-size:.82rem;font-weight:600;cursor:pointer;transition:.2s}
.oauth-btn:hover{border-color:#fff}
.divider{display:flex;align-items:center;gap:.6rem;margin:.9rem 0;color:var(--text3);font-size:.75rem}
.divider::before,.divider::after{content:'';flex:1;height:1px;background:var(--border)}
.switch-txt{text-align:center;font-size:.8rem;color:var(--text2);margin-top:.7rem}
.switch-txt a{color:var(--accent);cursor:pointer}

.admin-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.7rem;margin-bottom:1.2rem}
.a-stat{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.9rem;text-align:center}
.a-num{font-family:'Bebas Neue',sans-serif;font-size:1.9rem;color:var(--accent);display:block;line-height:1}
.a-label{font-size:.72rem;color:var(--text2);margin-top:.25rem}
.tbl-wrap{background:var(--surface);border:1px solid var(--border);border-radius:6px;overflow:hidden;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.78rem}
thead{background:var(--surface2)}
th{padding:.6rem .9rem;text-align:right;color:var(--text2);font-weight:600}
td{padding:.5rem .9rem;border-top:1px solid var(--border);color:#ccc}
tr:hover td{background:rgba(255,255,255,.02)}
.code-txt{font-family:monospace;font-size:.7rem;color:var(--accent);background:rgba(229,9,20,.1);padding:.15rem .35rem;border-radius:3px}

.prof-hd{display:flex;gap:1rem;padding-bottom:.9rem;border-bottom:1px solid var(--border);margin-bottom:.9rem;flex-wrap:wrap;align-items:center}
.ava-big{width:80px;height:80px;border-radius:50%;object-fit:cover;border:3px solid var(--accent);cursor:pointer;flex-shrink:0}
.prof-tabs{display:flex;gap:.25rem;margin-bottom:.9rem;overflow-x:auto}
.ptab{flex:1;min-width:80px;background:transparent;border:1px solid var(--border);color:var(--text2);padding:.45rem;border-radius:6px;font-size:.78rem;font-weight:600;cursor:pointer;white-space:nowrap}
.ptab.on{background:var(--accent);border-color:var(--accent);color:#fff}
.pcont{display:none}
.pcont.on{display:block}
.wl-item{display:flex;gap:.55rem;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.45rem;margin-bottom:.45rem;align-items:center}
.wl-thumb{width:36px;height:50px;border-radius:4px;object-fit:cover}
.wl-info{flex:1}
.color-row{display:flex;gap:.5rem;flex-wrap:wrap;margin:.5rem 0}
.swatch{width:30px;height:30px;border-radius:50%;cursor:pointer;border:2px solid transparent;transition:.2s}
.swatch.on{border-color:#fff;transform:scale(1.15)}

.footer{background:var(--bg2);border-top:1px solid var(--border);padding:1.8rem 1rem;text-align:center;color:var(--text3);font-size:.8rem;margin-top:2.5rem}
.loading{text-align:center;padding:1.8rem;color:var(--text2);grid-column:1/-1}
.spinner{display:inline-block;width:32px;height:32px;border:3px solid var(--surface2);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin-bottom:.6rem}
@keyframes spin{to{transform:rotate(360deg)}}
#toast{position:fixed;bottom:1.8rem;left:50%;transform:translateX(-50%) translateY(80px);background:var(--surface2);border:1px solid var(--border);border-radius:50px;padding:.55rem 1.3rem;font-size:.82rem;font-weight:600;color:#fff;box-shadow:0 8px 30px rgba(0,0,0,.6);z-index:99999;transition:.4s;white-space:nowrap}
#toast.on{transform:translateX(-50%) translateY(0)}
#toast.ok{border-color:var(--green);color:var(--green)}
#toast.err{border-color:var(--accent);color:var(--accent)}

@media(max-width:900px){
  .nav-links{display:none}
  .nav-links.mobile{display:flex;flex-direction:column;position:absolute;top:60px;left:0;right:0;background:var(--bg2);padding:.9rem;border-bottom:1px solid var(--border);gap:.3rem}
  .nav-links.mobile a{padding:.7rem 1rem}
  .mobile-menu-btn{display:block}
  .nav-search{display:none}
  .nav-search.mobile{display:flex;width:100%;margin-top:.5rem}
  .nav-search.mobile input{width:100%}
  .section{padding:1rem 3%}
  .card{flex:0 0 140px}
  .mp{width:130px}
  .mi h2{font-size:1.3rem}
  .hero{height:70vh;min-height:420px}
  .hero-title{font-size:1.7rem}
}
@media(max-width:500px){
  .card{flex:0 0 130px}
  .logo{font-size:1.5rem}
  .hero-title{font-size:1.4rem}
  .mp{width:110px}
  .mi h2{font-size:1.15rem}
  .md{font-size:.83rem}
}
</style>
</head>
<body>

<nav id="nav">
  <div class="nav-inner">
    <div class="logo">ONYX</div>
    <ul class="nav-links" id="navLinks">
      <li><a onclick="goHome()" class="on">الرئيسية</a></li>
      <li><a onclick="scrollToSec('movies')">الأفلام</a></li>
      <li><a onclick="scrollToSec('series')">المسلسلات</a></li>
      <li><a onclick="scrollToSec('top')">الأعلى تقييماً</a></li>
    </ul>
    <div class="nav-search" id="navSearch">
      <input id="searchInput" placeholder="ابحث..." onkeydown="if(event.key==='Enter')doSearch()">
      <button onclick="doSearch()">بحث</button>
    </div>
    <button class="btn-login" id="loginBtn" onclick="openMo('loginMo')">دخول</button>
    <button class="mobile-menu-btn" onclick="toggleMobileMenu()">≡</button>
  </div>
</nav>

<section class="hero" id="heroSec">
  <div class="hero-bg" id="heroBg"></div>
  <div class="hero-ov"></div>
  <div class="hero-body">
    <div class="hero-badge">الأكثر رواجاً</div>
    <h1 class="hero-title" id="hTitle">جاري التحميل...</h1>
    <div class="hero-meta" id="hMeta"></div>
    <p class="hero-desc" id="hDesc"></p>
    <button class="btn-play" onclick="playHero()">▶ مشاهدة</button>
  </div>
</section>

<section class="section" id="movies-sec">
  <div class="sec-hd"><h2 class="sec-title">الأكثر رواجاً</h2></div>
  <div class="row" id="trendingRow"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section">
  <div class="sec-hd"><h2 class="sec-title">الأفلام الشائعة</h2></div>
  <div class="row" id="popularRow"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section" id="top-sec">
  <div class="sec-hd"><h2 class="sec-title">الأعلى تقييماً</h2></div>
  <div class="row" id="topRow"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section" id="series-sec">
  <div class="sec-hd"><h2 class="sec-title">المسلسلات</h2></div>
  <div class="row" id="seriesRow"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section">
  <div class="sec-hd"><h2 class="sec-title">تصنيفات</h2></div>
  <div class="row" id="genreRow" style="flex-wrap:wrap;gap:.5rem"></div>
</section>

<footer class="footer">ONYX STUDIO — جميع الحقوق محفوظة 2025</footer>

<!-- MOVIE MODAL -->
<div class="mo" id="movieMo" onclick="if(event.target.id==='movieMo')closeMo('movieMo')">
  <div class="mo-box">
    <button class="mo-close" onclick="closeMo('movieMo')">✕</button>
    <div id="movieContent"><div class="loading"><div class="spinner"></div></div></div>
  </div>
</div>

<!-- LOGIN MODAL -->
<div class="mo" id="loginMo" onclick="if(event.target.id==='loginMo')closeMo('loginMo')">
  <div class="mo-box" style="max-width:420px">
    <button class="mo-close" onclick="closeMo('loginMo')">✕</button>
    <div class="auth-logo">ONYX</div>
    <div class="auth-title">تسجيل الدخول</div>
    <div class="oauth-btns">
      <button class="oauth-btn" onclick="simulateOAuth('Google')">Google</button>
      <button class="oauth-btn" onclick="simulateOAuth('GitHub')">GitHub</button>
    </div>
    <div class="divider">أو</div>
    <form onsubmit="doLogin(event)">
      <div class="fg"><label>البريد الإلكتروني</label><input type="email" id="liEmail" required></div>
      <div class="fg"><label>كلمة المرور</label><input type="password" id="liPass" required></div>
      <button class="btn-sub" type="submit">دخول</button>
    </form>
    <p class="switch-txt">ليس لديك حساب؟ <a onclick="switchMo('loginMo','regMo')">أنشئ حساباً</a></p>
  </div>
</div>

<!-- REGISTER MODAL -->
<div class="mo" id="regMo" onclick="if(event.target.id==='regMo')closeMo('regMo')">
  <div class="mo-box" style="max-width:420px">
    <button class="mo-close" onclick="closeMo('regMo')">✕</button>
    <div class="auth-logo">ONYX</div>
    <div class="auth-title">إنشاء حساب</div>
    <form onsubmit="doRegister(event)">
      <div class="fg"><label>الاسم</label><input type="text" id="reName" required></div>
      <div class="fg"><label>البريد</label><input type="email" id="reEmail" required></div>
      <div class="fg"><label>كلمة المرور</label><input type="password" id="rePass" required></div>
      <button class="btn-sub" type="submit">إنشاء</button>
    </form>
    <p class="switch-txt">لديك حساب؟ <a onclick="switchMo('regMo','loginMo')">سجّل دخولك</a></p>
  </div>
</div>

<!-- PROFILE MODAL -->
<div class="mo" id="profileMo" onclick="if(event.target.id==='profileMo')closeMo('profileMo')">
  <div class="mo-box" style="max-width:600px">
    <button class="mo-close" onclick="closeMo('profileMo')">✕</button>
    <div class="prof-hd">
      <img class="ava-big" id="profAvaImg" src="https://ui-avatars.com/api/?background=e50914&color=fff&size=200&name=User">
      <div>
        <h3 id="pName">...</h3>
        <p style="color:var(--text2);font-size:.8rem" id="pEmail">...</p>
      </div>
    </div>
    <div class="prof-tabs">
      <button class="ptab on" onclick="pTab(this,'ptInfo')">المعلومات</button>
      <button class="ptab" onclick="pTab(this,'ptTheme')">التخصيص</button>
    </div>
    <div id="ptInfo" class="pcont on">
      <div class="fg"><label>الاسم</label><input id="pNameIn"></div>
      <div class="fg"><label>الوصف</label><input id="pBioIn"></div>
      <div class="fg"><label>رابط الصورة</label><input id="pAvaUrl"></div>
      <button class="btn-sub" onclick="saveProfile()">حفظ</button>
    </div>
    <div id="ptTheme" class="pcont">
      <div class="fg">
        <label>لون الثيم</label>
        <div class="color-row">
          <div class="swatch on" style="background:#e50914" onclick="setAccent('#e50914',this)"></div>
          <div class="swatch" style="background:#0090ff" onclick="setAccent('#0090ff',this)"></div>
          <div class="swatch" style="background:#a855f7" onclick="setAccent('#a855f7',this)"></div>
          <div class="swatch" style="background:#22c55e" onclick="setAccent('#22c55e',this)"></div>
          <div class="swatch" style="background:#f5c518" onclick="setAccent('#f5c518',this)"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ADMIN MODAL -->
<div class="mo" id="adminMo" onclick="if(event.target.id==='adminMo')closeMo('adminMo')">
  <div class="mo-box" style="max-width:1000px">
    <button class="mo-close" onclick="closeMo('adminMo')">✕</button>
    <h2 style="margin-bottom:1.2rem;font-size:1.3rem">لوحة التحكم</h2>
    <div id="adminContent"></div>
  </div>
</div>

<div id="toast"></div>

<script>
const IMG = 'https://image.tmdb.org/t/p';
const SOURCES = __SOURCES__;
const OWNER = { email: 'admin@gmail.com', password: '1212admin', name: 'Admin', isAdmin: true };

const S = {
  user: JSON.parse(localStorage.getItem('ox_user') || 'null'),
  fav: JSON.parse(localStorage.getItem('ox_fav') || '[]'),
  users: JSON.parse(localStorage.getItem('ox_users') || '[]'),
  hero: [], hIdx: 0, hTimer: null,
  currentMovie: null, mobileMenuOpen: false,
};

document.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  loadAll();
  window.addEventListener('scroll', () => document.getElementById('nav').classList.toggle('solid', scrollY > 40));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') document.querySelectorAll('.mo.on').forEach(m => closeMo(m.id)); });
  const savedAccent = localStorage.getItem('ox_accent');
  if (savedAccent) document.documentElement.style.setProperty('--accent', savedAccent);
});

function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = type ? 'on ' + type : 'on';
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = ''; }, 3000);
}

async function loadAll() {
  await Promise.all([loadHero(), loadTrending(), loadPopular(), loadTopRated(), loadSeries(), loadGenres()]);
}

function movieCard(m) {
  const title = m.title || m.name || '?';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
  const poster = m.poster_path ? IMG + '/w500' + m.poster_path : 'https://via.placeholder.com/300x450/242424/aaa?text=ONYX';
  const type = m.media_type || (m.name ? 'tv' : 'movie');
  return '<div class="card" onclick="openMovie(' + m.id + ',\'' + type + '\')">' +
    '<img src="' + poster + '" loading="lazy">' +
    '<div class="card-info"><div class="card-title">' + title + '</div>' +
    '<div class="card-meta"><span>' + year + '</span><span class="rating">⭐ ' + rating + '</span></div></div></div>';
}

async function loadHero() {
  try {
    const r = await fetch('/api/trending');
    const d = await r.json();
    S.hero = (d.results || []).filter(m => m.backdrop_path).slice(0, 5);
    if (!S.hero.length) return;
    document.getElementById('heroBg').innerHTML = S.hero.map((m, i) =>
      '<div class="hero-slide ' + (i === 0 ? 'on' : '') + '" style="background-image:url(\'' + IMG + '/original' + m.backdrop_path + '\')"></div>'
    ).join('');
    renderHero(0);
    S.hTimer = setInterval(nextSlide, 7000);
  } catch (e) {}
}

function renderHero(i) {
  const m = S.hero[i]; if (!m) return;
  document.getElementById('hTitle').textContent = m.title || m.name || '?';
  document.getElementById('hMeta').innerHTML =
    '<span>' + (m.release_date || m.first_air_date || '').substring(0, 4) + '</span>' +
    '<span class="rating">⭐ ' + (m.vote_average ? m.vote_average.toFixed(1) : '?') + '</span>' +
    '<span>' + (m.media_type === 'tv' ? 'مسلسل' : 'فيلم') + '</span>';
  document.getElementById('hDesc').textContent = (m.overview || '').substring(0, 220) + '...';
}

function setSlide(i) {
  S.hIdx = i;
  document.querySelectorAll('.hero-slide').forEach((s, idx) => s.classList.toggle('on', idx === i));
  renderHero(i);
}
function nextSlide() { if (S.hero.length) setSlide((S.hIdx + 1) % S.hero.length); }
function playHero() { const m = S.hero[S.hIdx]; if (m) openMovie(m.id, m.media_type || 'movie'); }

async function loadTrending() {
  const el = document.getElementById('trendingRow');
  try {
    const r = await fetch('/api/trending');
    const d = await r.json();
    el.innerHTML = (d.results || []).filter(m => m.poster_path).slice(0, 20).map(movieCard).join('');
  } catch (e) { el.innerHTML = '<div class="loading">❌</div>'; }
}

async function loadPopular() {
  const el = document.getElementById('popularRow');
  try {
    const r = await fetch('/api/popular/movie');
    const d = await r.json();
    el.innerHTML = (d.results || []).filter(m => m.poster_path).slice(0, 20).map(movieCard).join('');
  } catch (e) {}
}

async function loadTopRated() {
  const el = document.getElementById('topRow');
  try {
    const r = await fetch('/api/top_rated/movie');
    const d = await r.json();
    el.innerHTML = (d.results || []).filter(m => m.poster_path).slice(0, 20).map(movieCard).join('');
  } catch (e) {}
}

async function loadSeries() {
  const el = document.getElementById('seriesRow');
  try {
    const r = await fetch('/api/popular/tv');
    const d = await r.json();
    el.innerHTML = (d.results || []).filter(m => m.poster_path).slice(0, 20).map(movieCard).join('');
  } catch (e) {}
}

const GENRES = [
  {id:28,name:'أكشن'},{id:18,name:'دراما'},{id:35,name:'كوميدي'},
  {id:878,name:'خيال علمي'},{id:27,name:'رعب'},{id:10749,name:'رومانسي'},
  {id:12,name:'مغامرة'},{id:16,name:'أنيميشن'},
];

function loadGenres() {
  document.getElementById('genreRow').innerHTML = GENRES.map(g =>
    '<button class="psrc" style="flex-shrink:0" onclick="filterGenre(' + g.id + ',\'' + g.name + '\')">' + g.name + '</button>'
  ).join('');
}

async function filterGenre(gid, gname) {
  const el = document.getElementById('trendingRow');
  const title = document.querySelector('#movies-sec .sec-title');
  el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  title.textContent = 'تصنيف: ' + gname;
  document.getElementById('movies-sec').scrollIntoView({ behavior: 'smooth' });
  try {
    const r = await fetch('/api/genre/movie/' + gid);
    const d = await r.json();
    const res = (d.results || []).filter(m => m.poster_path).slice(0, 20);
    el.innerHTML = res.map(movieCard).join('') || '<div class="loading">لا توجد نتائج</div>';
  } catch (e) { el.innerHTML = '<div class="loading">❌</div>'; }
}

async function doSearch() {
  const q = document.getElementById('searchInput').value.trim();
  if (!q) return;
  const el = document.getElementById('trendingRow');
  const title = document.querySelector('#movies-sec .sec-title');
  el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  title.textContent = 'نتائج: ' + q;
  document.getElementById('movies-sec').scrollIntoView({ behavior: 'smooth' });
  try {
    const r = await fetch('/api/search?q=' + encodeURIComponent(q));
    const d = await r.json();
    const res = (d.results || []).filter(m => m.poster_path).slice(0, 20);
    el.innerHTML = res.map(movieCard).join('') || '<div class="loading">لا نتائج</div>';
  } catch (e) {}
}

async function openMovie(id, type) {
  const mo = document.getElementById('movieMo');
  const ct = document.getElementById('movieContent');
  ct.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  mo.classList.add('on');
  document.body.style.overflow = 'hidden';
  S.currentMovie = { id: id, type: type };

  try {
    const r = await fetch('/api/' + type + '/' + id);
    const m = await r.json();
    const title = m.title || m.name || '?';
    const year = (m.release_date || m.first_air_date || '').substring(0, 4);
    const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
    const runtime = m.runtime || (m.episode_run_time && m.episode_run_time[0]) || '?';
    const origLang = (m.original_language || 'en').toUpperCase();
    const poster = m.poster_path ? IMG + '/w500' + m.poster_path : '';
    const genres = (m.genres || []).map(g => g.name).join(' • ');
    const desc = m.overview || 'لا يوجد وصف';

    let html = '';
    html += '<div class="pwrap on"><div class="pcont"><iframe id="pframe" allowfullscreen allow="autoplay; encrypted-media; fullscreen"></iframe></div>';
    html += '<div class="psrcs">';
    SOURCES.forEach((s, i) => {
      html += '<button class="psrc ' + (i === 0 ? 'on' : '') + '" onclick="switchSrc(' + i + ')">' + s.name + ' (' + s.q + ')</button>';
    });
    html += '</div></div>';

    html += '<div class="mh"><div class="mp"><img src="' + poster + '"></div><div class="mi">';
    html += '<h2>' + title + '</h2>';
    html += '<div class="mm"><span class="rating">⭐ ' + rating + '/10</span><span>' + year + '</span><span>⏱ ' + runtime + ' د</span><span class="lang">' + origLang + '</span></div>';
    if (genres) html += '<p class="mg">' + genres + '</p>';
    html += '<p class="md">' + desc + '</p>';
    html += '<button class="btn-watch" onclick="startStream(0)">▶ مشاهدة الآن</button>';
    html += '</div></div>';

    if (type === 'tv' && m.seasons && m.seasons.length) {
      html += '<div class="seasons-sec"><h3>المواسم</h3><div class="sel">';
      m.seasons.filter(s => s.season_number > 0).forEach((s, i) => {
        html += '<button class="sbtn ' + (i === 0 ? 'on' : '') + '" onclick="changeSeason(this,' + id + ',' + s.season_number + ')">الموسم ' + s.season_number + '</button>';
      });
      html += '</div><div class="egrid" id="epGrid"></div></div>';
    }

    ct.innerHTML = html;
    startStream(0);

    if (type === 'tv' && m.seasons && m.seasons.length) {
      const firstS = m.seasons.filter(s => s.season_number > 0)[0];
      if (firstS) loadEpisodes(id, firstS.season_number);
    }
  } catch (e) { ct.innerHTML = '<div class="loading">❌</div>'; }
}

function startStream(idx, season, episode) {
  const frame = document.getElementById('pframe');
  if (!frame) return;
  frame.src = '/player?type=' + S.currentMovie.type + '&id=' + S.currentMovie.id + '&source=' + idx + '&season=' + (season || 1) + '&episode=' + (episode || 1);
}

function switchSrc(idx) {
  document.querySelectorAll('.psrc').forEach((b, i) => b.classList.toggle('on', i === idx));
  startStream(idx);
}

async function loadEpisodes(tvId, seasonNum) {
  const el = document.getElementById('epGrid');
  if (!el) return;
  el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  try {
    const r = await fetch('/api/tv/' + tvId + '/season/' + seasonNum);
    const d = await r.json();
    const eps = d.episodes || [];
    el.innerHTML = eps.map(ep => {
      const still = ep.still_path ? IMG + '/w300' + ep.still_path : 'https://via.placeholder.com/300x169/242424/aaa';
      return '<div class="ecard" onclick="startStream(0,' + seasonNum + ',' + ep.episode_number + ')">' +
        '<img class="ethumb" src="' + still + '">' +
        '<div class="edet"><div class="enum">حلقة ' + ep.episode_number + '</div>' +
        '<div class="etitle">' + (ep.name || '') + '</div></div></div>';
    }).join('');
  } catch (e) { el.innerHTML = '<div class="loading">❌</div>'; }
}

function changeSeason(btn, tvId, seasonNum) {
  document.querySelectorAll('.sbtn').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  loadEpisodes(tvId, seasonNum);
}

function openMo(id) {
  if (id === 'adminMo') {
    if (!S.user?.isAdmin) { toast('غير مصرح', 'err'); return; }
    buildAdmin();
  }
  if (id === 'profileMo') {
    if (!S.user) { openMo('loginMo'); return; }
    fillProfile();
  }
  document.getElementById(id).classList.add('on');
  document.body.style.overflow = 'hidden';
}

function closeMo(id) {
  document.getElementById(id)?.classList.remove('on');
  document.body.style.overflow = '';
  if (id === 'movieMo') {
    const f = document.getElementById('pframe');
    if (f) f.src = '';
  }
}

function switchMo(a, b) { closeMo(a); setTimeout(() => openMo(b), 200); }

function doLogin(e) {
  e.preventDefault();
  const email = document.getElementById('liEmail').value.trim();
  const pass = document.getElementById('liPass').value;
  if (email === OWNER.email && pass === OWNER.password) {
    loginUser({ ...OWNER, avatar: '' });
    closeMo('loginMo');
    toast('👑 مرحباً Admin', 'ok');
    return;
  }
  const u = S.users.find(x => x.email === email && x.password === pass);
  if (!u) { toast('بيانات خاطئة', 'err'); return; }
  loginUser(u);
  closeMo('loginMo');
  toast('مرحباً ' + u.name, 'ok');
}

function doRegister(e) {
  e.preventDefault();
  const name = document.getElementById('reName').value.trim();
  const email = document.getElementById('reEmail').value.trim();
  const pass = document.getElementById('rePass').value;
  if (!name || !email || !pass) { toast('أكمل البيانات', 'err'); return; }
  if (pass.length < 6) { toast('كلمة المرور قصيرة', 'err'); return; }
  if (S.users.find(u => u.email === email)) { toast('البريد مستخدم', 'err'); return; }
  const u = { id: Date.now(), name, email, password: pass, bio: '', avatar: '', isAdmin: false, joined: new Date().toLocaleDateString('ar-EG') };
  S.users.push(u);
  localStorage.setItem('ox_users', JSON.stringify(S.users));
  loginUser(u);
  closeMo('regMo');
  toast('🎉 تم إنشاء الحساب', 'ok');
}

function simulateOAuth(provider) {
  const name = prompt(provider + ' — اسمك:');
  if (!name) return;
  const email = name.toLowerCase().replace(/\s/g, '') + '@' + provider.toLowerCase() + '.com';
  let u = S.users.find(x => x.email === email);
  if (!u) {
    u = { id: Date.now(), name, email, password: 'oauth_' + provider, bio: 'سجل عبر ' + provider,
          avatar: 'https://ui-avatars.com/api/?background=0090ff&color=fff&size=200&name=' + encodeURIComponent(name),
          isAdmin: false, joined: new Date().toLocaleDateString('ar-EG') };
    S.users.push(u);
    localStorage.setItem('ox_users', JSON.stringify(S.users));
  }
  loginUser(u);
  closeMo('loginMo');
  closeMo('regMo');
  toast('✅ تم الدخول عبر ' + provider, 'ok');
}

function loginUser(u) {
  S.user = u;
  localStorage.setItem('ox_user', JSON.stringify(u));
  updateAuthUI();
}

function logout() {
  S.user = null;
  localStorage.removeItem('ox_user');
  updateAuthUI();
  toast('تم تسجيل الخروج');
}

function updateAuthUI() {
  const u = S.user;
  const loginBtn = document.getElementById('loginBtn');
  ['userBtn', 'logoutBtn', 'adminBtn'].forEach(id => document.getElementById(id)?.remove());
  if (u) {
    loginBtn.style.display = 'none';
    const btn = document.createElement('button');
    btn.id = 'userBtn';
    btn.className = 'btn-login';
    btn.style.cssText = 'padding:0;background:transparent';
    btn.innerHTML = '<img src="' + (u.avatar || 'https://ui-avatars.com/api/?background=e50914&color=fff&size=200&name=' + encodeURIComponent(u.name)) + '" style="width:36px;height:36px;border-radius:50%;border:2px solid var(--accent);object-fit:cover">';
    btn.onclick = () => openMo('profileMo');
    loginBtn.parentNode.insertBefore(btn, loginBtn);
    const out = document.createElement('button');
    out.id = 'logoutBtn';
    out.className = 'btn-login';
    out.style.cssText = 'background:transparent;border:1px solid var(--border)';
    out.textContent = 'خروج';
    out.onclick = logout;
    loginBtn.parentNode.insertBefore(out, loginBtn);
    if (u.isAdmin) {
      const adm = document.createElement('button');
      adm.id = 'adminBtn';
      adm.className = 'btn-login';
      adm.style.cssText = 'background:#f5c518;color:#000';
      adm.textContent = 'لوحة التحكم';
      adm.onclick = () => openMo('adminMo');
      loginBtn.parentNode.insertBefore(adm, loginBtn);
    }
  } else {
    loginBtn.style.display = 'block';
  }
}

function fillProfile() {
  const u = S.user; if (!u) return;
  document.getElementById('pName').textContent = u.name;
  document.getElementById('pEmail').textContent = u.email;
  document.getElementById('profAvaImg').src = u.avatar || 'https://ui-avatars.com/api/?background=e50914&color=fff&size=200&name=' + encodeURIComponent(u.name);
  document.getElementById('pNameIn').value = u.name;
  document.getElementById('pBioIn').value = u.bio || '';
  document.getElementById('pAvaUrl').value = u.avatar || '';
}

function saveProfile() {
  if (!S.user) return;
  S.user.name = document.getElementById('pNameIn').value || S.user.name;
  S.user.bio = document.getElementById('pBioIn').value || '';
  S.user.avatar = document.getElementById('pAvaUrl').value || S.user.avatar;
  localStorage.setItem('ox_user', JSON.stringify(S.user));
  const idx = S.users.findIndex(u => u.email === S.user.email);
  if (idx !== -1) {
    S.users[idx] = { ...S.users[idx], ...S.user };
    localStorage.setItem('ox_users', JSON.stringify(S.users));
  }
  updateAuthUI();
  fillProfile();
  toast('✅ تم الحفظ', 'ok');
}

function pTab(btn, id) {
  document.querySelectorAll('.ptab').forEach(t => t.classList.remove('on'));
  document.querySelectorAll('.pcont').forEach(c => c.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById(id)?.classList.add('on');
}

function setAccent(hex, el) {
  document.querySelectorAll('.swatch').forEach(s => s.classList.remove('on'));
  if (el) el.classList.add('on');
  document.documentElement.style.setProperty('--accent', hex);
  localStorage.setItem('ox_accent', hex);
  toast('تم تغيير اللون', 'ok');
}

function buildAdmin() {
  const el = document.getElementById('adminContent');
  const all = [{ name: 'Admin', email: OWNER.email, password: OWNER.password, isAdmin: true }, ...S.users];
  el.innerHTML =
    '<div class="admin-stats">' +
      '<div class="a-stat"><span class="a-num">' + all.length + '</span><div class="a-label">مستخدمين</div></div>' +
      '<div class="a-stat"><span class="a-num">' + S.fav.length + '</span><div class="a-label">مفضلات</div></div>' +
    '</div>' +
    '<div class="tbl-wrap"><table>' +
      '<thead><tr><th>#</th><th>الاسم</th><th>البريد</th><th>الباسورد</th><th>الدور</th></tr></thead>' +
      '<tbody>' + all.map((u, i) =>
        '<tr><td>' + (i + 1) + '</td><td>' + u.name + '</td><td>' + u.email + '</td>' +
        '<td><span class="code-txt">' + u.password + '</span></td>' +
        '<td>' + (u.isAdmin ? '👑 Owner' : '👤 User') + '</td></tr>'
      ).join('') + '</tbody></table></div>';
}

function toggleMobileMenu() {
  S.mobileMenuOpen = !S.mobileMenuOpen;
  document.getElementById('navLinks').classList.toggle('mobile', S.mobileMenuOpen);
  document.getElementById('navSearch').classList.toggle('mobile', S.mobileMenuOpen);
}

function goHome() { window.scrollTo({ top: 0, behavior: 'smooth' }); }
function scrollToSec(id) { document.getElementById(id + '-sec')?.scrollIntoView({ behavior: 'smooth' }); }

console.log('[ONYX] Loaded. Sources:', SOURCES.length);
</script>

</body>
</html>
"""

INDEX_HTML = INDEX_HTML.replace('__SOURCES__', SOURCES_JSON)


PLAYER_HTML = r"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>*{margin:0;padding:0}html,body,iframe{width:100%;height:100%;background:#000;border:none;overflow:hidden}</style></head>
<body>
<iframe id="player" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen"></iframe>
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
PLAYER_HTML = PLAYER_HTML.replace('__SOURCES__', SOURCES_JSON)


# ROUTES
@app.route("/")
def index():
    return INDEX_HTML


@app.route("/player")
def player():
    return PLAYER_HTML


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
    return jsonify({"status": "ok", "tmdb": "ok" if TMDB_API_KEY else "missing", "sources": len(PLAYER_SOURCES)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
