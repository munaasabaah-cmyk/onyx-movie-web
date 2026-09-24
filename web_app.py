# -*- coding: utf-8 -*-
"""
ONYX CINEMA v3.0
Flask + TMDB + Multi-Audio Player Sources
"""

from flask import Flask, jsonify, request
import os
import time
import json
import hashlib
import secrets
import urllib.request
import urllib.parse
import re
from collections import defaultdict

app = Flask(__name__)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
SECRET_SALT = os.getenv("SECRET_SALT", "onyx_cinema_2025_secret")
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
    return r


# ══════════════════════════════════════════════════════════
# PLAYER SOURCES — 20 مصدر
# ══════════════════════════════════════════════════════════
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
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/3.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


# ══════════════════════════════════════════════════════════
# HTML
# ══════════════════════════════════════════════════════════
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ONYX CINEMA</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#141414;--bg2:#181818;--surface:#242424;--surface2:#2f2f2f;--accent:#e50914;--gold:#f5c518;--green:#22c55e;--text:#f0f0f0;--text2:#aaa;--text3:#666;--border:rgba(255,255,255,0.1);--font:'Cairo',sans-serif}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--font);overflow-x:hidden}
a{text-decoration:none;color:inherit}
img{max-width:100%;display:block}
button{cursor:pointer;font-family:var(--font);border:none}
input,textarea{font-family:var(--font)}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-track{background:var(--bg2)}
::-webkit-scrollbar-thumb{background:var(--accent);border-radius:4px}

#nav{position:fixed;top:0;left:0;right:0;z-index:1000;height:68px;padding:0 4%;display:flex;align-items:center;background:linear-gradient(180deg,rgba(0,0,0,.95) 0%,transparent 100%);transition:.3s}
#nav.solid{background:#141414;box-shadow:0 2px 20px rgba(0,0,0,.8)}
.nav-inner{width:100%;display:flex;align-items:center;gap:2rem;max-width:1800px;margin:0 auto}
.logo{font-family:'Bebas Neue',sans-serif;font-size:2.2rem;color:var(--accent);letter-spacing:.08em;flex-shrink:0}
.nav-links{display:flex;gap:.3rem;flex:1;list-style:none}
.nav-links a{padding:.5rem 1rem;font-size:.9rem;font-weight:600;color:var(--text2);transition:.2s;cursor:pointer;border-radius:4px}
.nav-links a:hover{color:#fff;background:rgba(255,255,255,.05)}
.nav-search{display:flex;align-items:center;background:rgba(0,0,0,.75);border:1px solid var(--border);border-radius:6px;overflow:hidden}
.nav-search input{background:transparent;border:none;outline:none;color:#fff;padding:.5rem 1rem;width:220px;font-size:.85rem}
.nav-search button{background:var(--accent);color:#fff;padding:.5rem 1rem;font-size:.85rem;font-weight:700}
.btn-login{background:var(--accent);color:#fff;padding:.55rem 1.2rem;border-radius:6px;font-size:.85rem;font-weight:700;cursor:pointer}
.user-ava{position:relative;display:none}
.user-ava.show{display:block}
.user-ava img{width:38px;height:38px;border-radius:50%;border:2px solid var(--accent);cursor:pointer;object-fit:cover}
.dropdown{position:absolute;top:calc(100% + .5rem);left:0;background:var(--surface);border:1px solid var(--border);border-radius:8px;min-width:220px;padding:.5rem 0;display:none;box-shadow:0 10px 40px rgba(0,0,0,.8);z-index:100}
.user-ava:hover .dropdown{display:block}
.dropdown a{display:block;padding:.6rem 1rem;font-size:.85rem;color:var(--text2);cursor:pointer;transition:.2s}
.dropdown a:hover{background:var(--surface2);color:#fff}
.dropdown hr{border:none;border-top:1px solid var(--border);margin:.3rem 0}

.hero{position:relative;height:85vh;min-height:560px;overflow:hidden;display:flex;align-items:center}
.hero-bg{position:absolute;inset:0}
.hero-slide{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transition:opacity 1.2s ease}
.hero-slide.on{opacity:1}
.hero-ov{position:absolute;inset:0;background:linear-gradient(90deg,#141414 0%,rgba(20,20,20,.5) 50%,transparent 100%),linear-gradient(0deg,#141414 0%,transparent 40%)}
.hero-body{position:relative;z-index:2;max-width:680px;padding:0 4%}
.hero-badge{display:inline-block;background:var(--accent);color:#fff;font-size:.72rem;font-weight:700;padding:.3rem .8rem;border-radius:4px;margin-bottom:1rem}
.hero-title{font-size:clamp(2.5rem,5vw,4rem);font-weight:900;line-height:1.1;color:#fff;margin-bottom:1rem;text-shadow:0 4px 30px rgba(0,0,0,.6)}
.hero-meta{display:flex;gap:1rem;color:var(--text2);font-size:.95rem;font-weight:600;margin-bottom:1rem;flex-wrap:wrap;align-items:center}
.hero-meta .rating{color:var(--gold)}
.hero-desc{color:#ddd;font-size:.95rem;line-height:1.6;max-width:600px;margin-bottom:1.5rem;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.btn-play{background:#fff;color:#000;padding:.75rem 2rem;border-radius:6px;font-size:1rem;font-weight:700;transition:.2s;display:inline-flex;align-items:center;gap:.5rem;cursor:pointer}
.btn-play:hover{background:rgba(255,255,255,.8);transform:scale(1.03)}
.hero-dots{position:absolute;bottom:2rem;left:50%;transform:translateX(-50%);z-index:3;display:flex;gap:.5rem}
.hero-dot{width:8px;height:8px;background:rgba(255,255,255,.3);border-radius:50%;cursor:pointer;transition:.2s}
.hero-dot.on{background:var(--accent);width:24px;border-radius:4px}

.section{padding:1.5rem 4%;max-width:1800px;margin:0 auto}
.sec-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem}
.sec-title{font-size:1.5rem;font-weight:700;color:#fff}
.sec-sub{font-size:.85rem;color:var(--text2)}

.row{display:flex;gap:.8rem;overflow-x:auto;padding:1rem 0;scroll-snap-type:x mandatory}
.row::-webkit-scrollbar{height:6px}
.card{flex:0 0 180px;scroll-snap-align:start;background:var(--surface);border-radius:6px;overflow:hidden;cursor:pointer;transition:transform .3s,box-shadow .3s;position:relative}
.card:hover{transform:scale(1.06);z-index:5;box-shadow:0 15px 40px rgba(0,0,0,.9)}
.card img{width:100%;aspect-ratio:2/3;object-fit:cover;background:var(--surface2)}
.card-info{padding:.6rem}
.card-title{font-size:.85rem;font-weight:700;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:.2rem}
.card-meta{font-size:.72rem;color:var(--text2);display:flex;gap:.4rem;flex-wrap:wrap}
.card-meta .rating{color:var(--gold);font-weight:700}
.card-badge{position:absolute;top:.5rem;right:.5rem;background:var(--accent);color:#fff;font-size:.65rem;font-weight:700;padding:.2rem .5rem;border-radius:3px}

.top-list{display:flex;flex-direction:column;gap:.6rem}
.top-item{display:flex;align-items:center;gap:1rem;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.7rem 1rem;cursor:pointer;transition:.2s}
.top-item:hover{background:var(--surface2);transform:translateX(-4px)}
.top-rank{font-family:'Bebas Neue',sans-serif;font-size:1.6rem;color:var(--accent);width:2rem;text-align:center;flex-shrink:0}
.top-item:nth-child(1) .top-rank{color:var(--gold)}
.top-item:nth-child(2) .top-rank{color:#c0c0c0}
.top-item:nth-child(3) .top-rank{color:#cd7f32}
.top-thumb{width:55px;height:80px;border-radius:4px;object-fit:cover}
.top-info{flex:1}
.top-title{font-size:.95rem;font-weight:700;margin-bottom:.2rem}
.top-meta{font-size:.78rem;color:var(--text2);display:flex;gap:.7rem}
.top-meta .rating{color:var(--gold)}

.mo{position:fixed;inset:0;background:rgba(0,0,0,.95);backdrop-filter:blur(8px);z-index:5000;display:none;align-items:flex-start;justify-content:center;padding:1.5rem;overflow-y:auto}
.mo.on{display:flex}
.mo-box{background:#181818;border:1px solid var(--border);border-radius:12px;padding:2rem;width:95%;max-width:1300px;position:relative;margin:auto}
.mo-close{position:absolute;top:1rem;left:1rem;background:var(--surface2);color:#fff;width:40px;height:40px;border-radius:50%;font-size:1.1rem;z-index:10;cursor:pointer;transition:.2s}
.mo-close:hover{background:var(--accent)}
.mo-box.narrow{max-width:460px}

.pwrap{display:none;margin-bottom:1.5rem}
.pwrap.on{display:block}
.pcont{width:100%;aspect-ratio:16/9;background:#000;border-radius:6px;overflow:hidden;margin-bottom:.75rem}
.pcont iframe{width:100%;height:100%;border:none}
.psrcs{display:flex;gap:.4rem;overflow-x:auto;padding:.5rem;background:var(--surface);border-radius:6px;border:1px solid var(--border);margin-bottom:.75rem}
.psrcs::-webkit-scrollbar{height:4px}
.psrc{background:var(--bg2);border:1px solid var(--border);color:var(--text2);padding:.4rem .8rem;border-radius:5px;font-size:.72rem;font-weight:600;white-space:nowrap;cursor:pointer;transition:.2s}
.psrc.on{background:var(--accent);border-color:var(--accent);color:#fff}
.psrc:hover:not(.on){color:var(--accent);border-color:var(--accent)}

.mh{display:flex;gap:2rem;flex-wrap:wrap;margin-bottom:1.5rem}
.mp{width:220px;flex-shrink:0;border-radius:6px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.8)}
.mp img{width:100%}
.mi{flex:1;min-width:280px}
.mi h2{font-size:2.2rem;margin-bottom:.6rem;font-weight:800;line-height:1.2}
.mm{display:flex;gap:.8rem;flex-wrap:wrap;color:var(--text2);font-size:.9rem;margin-bottom:1rem;align-items:center}
.mm .rating{color:var(--gold);font-weight:700;background:rgba(245,197,24,.1);padding:.2rem .6rem;border-radius:4px}
.mm .lang{background:var(--surface2);color:#fff;padding:.2rem .6rem;border-radius:4px;font-weight:700;text-transform:uppercase;font-size:.8rem}
.mg{color:var(--text2);font-size:.88rem;margin-bottom:1rem}
.md{color:#ccc;line-height:1.7;font-size:.95rem;margin-bottom:1.5rem;max-width:850px}
.btn-watch{background:var(--accent);color:#fff;padding:.8rem 2rem;border-radius:6px;font-size:1rem;font-weight:700;display:inline-flex;align-items:center;gap:.5rem;transition:.2s;cursor:pointer}
.btn-watch:hover{background:#ff1e27;transform:scale(1.03)}

.seasons-sec{margin-top:1.5rem;border-top:1px solid var(--border);padding-top:1.5rem}
.seasons-sec h3{font-size:1.2rem;margin-bottom:1rem}
.sel{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem}
.sbtn{background:var(--surface);border:1px solid var(--border);color:var(--text2);padding:.5rem 1rem;border-radius:6px;font-size:.85rem;font-weight:700;cursor:pointer;transition:.2s}
.sbtn.on,.sbtn:hover{background:var(--accent);border-color:var(--accent);color:#fff}
.egrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem}
.ecard{background:var(--surface);border-radius:6px;overflow:hidden;border:1px solid var(--border);cursor:pointer;transition:.2s}
.ecard:hover{transform:translateY(-3px);border-color:var(--accent)}
.ethumb{width:100%;aspect-ratio:16/9;object-fit:cover;background:var(--surface2)}
.edet{padding:.7rem}
.etitle{font-size:.85rem;font-weight:700;margin-bottom:.2rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.enum{font-size:.72rem;color:var(--accent);font-weight:700}

.cmt-sec{margin-top:1.5rem;border-top:1px solid var(--border);padding-top:1.5rem}
.cmt-sec h3{font-size:1.2rem;margin-bottom:1rem}
.cmt-form{display:flex;gap:.7rem;margin-bottom:1rem;flex-wrap:wrap}
.cmt-form textarea{flex:1;min-width:200px;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:#fff;padding:.6rem;font-size:.88rem;min-height:60px;resize:vertical;outline:none}
.cmt-form textarea:focus{border-color:var(--accent)}
.cmt-send{background:var(--accent);color:#fff;padding:.6rem 1.5rem;border-radius:6px;font-weight:700;align-self:flex-end;cursor:pointer}
.cmt-list{display:flex;flex-direction:column;gap:.7rem}
.cmt{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.8rem;display:flex;gap:.7rem}
.cmt-ava{width:38px;height:38px;border-radius:50%;object-fit:cover;flex-shrink:0}
.cmt-body{flex:1}
.cmt-head{display:flex;gap:.5rem;align-items:center;margin-bottom:.3rem}
.cmt-name{font-size:.85rem;font-weight:700}
.cmt-date{font-size:.72rem;color:var(--text3)}
.cmt-text{font-size:.85rem;color:#ccc;line-height:1.6}

.auth-logo{text-align:center;font-family:'Bebas Neue',sans-serif;font-size:2rem;color:var(--accent);margin-bottom:.3rem;letter-spacing:.08em}
.auth-title{text-align:center;font-size:1.3rem;font-weight:700;margin-bottom:1.5rem}
.fg{margin-bottom:1rem}
.fg label{display:block;font-size:.82rem;color:var(--text2);font-weight:600;margin-bottom:.3rem}
.fg input,.fg textarea{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:#fff;padding:.65rem;font-size:.88rem;outline:none;transition:.2s}
.fg input:focus{border-color:var(--accent)}
.btn-sub{width:100%;background:var(--accent);color:#fff;padding:.75rem;border-radius:6px;font-size:.95rem;font-weight:700;margin-top:.5rem;cursor:pointer}
.btn-sub:hover{background:#ff1e27}
.oauth-btns{display:flex;gap:.5rem;margin-bottom:1rem}
.oauth-btn{flex:1;background:var(--surface);border:1px solid var(--border);color:#fff;padding:.65rem;border-radius:6px;font-size:.85rem;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:.5rem;transition:.2s}
.oauth-btn:hover{border-color:#fff}
.divider{display:flex;align-items:center;gap:.7rem;margin:1rem 0;color:var(--text3);font-size:.78rem}
.divider::before,.divider::after{content:'';flex:1;height:1px;background:var(--border)}
.switch-txt{text-align:center;font-size:.83rem;color:var(--text2);margin-top:.8rem}
.switch-txt a{color:var(--accent);cursor:pointer}

.admin-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.8rem;margin-bottom:1.5rem}
.a-stat{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1rem;text-align:center}
.a-num{font-family:'Bebas Neue',sans-serif;font-size:2rem;color:var(--accent);display:block;line-height:1}
.a-label{font-size:.75rem;color:var(--text2);margin-top:.3rem}
.tbl-wrap{background:var(--surface);border:1px solid var(--border);border-radius:6px;overflow:hidden;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.82rem}
thead{background:var(--surface2)}
th{padding:.7rem 1rem;text-align:right;color:var(--text2);font-weight:600}
td{padding:.6rem 1rem;border-top:1px solid var(--border);color:#ccc}
tr:hover td{background:rgba(255,255,255,.02)}
.code-txt{font-family:monospace;font-size:.72rem;color:var(--accent);background:rgba(229,9,20,.1);padding:.2rem .4rem;border-radius:3px}

.prof-hd{display:flex;gap:1.2rem;padding-bottom:1rem;border-bottom:1px solid var(--border);margin-bottom:1rem;flex-wrap:wrap;align-items:center}
.ava-big{width:90px;height:90px;border-radius:50%;object-fit:cover;border:3px solid var(--accent);cursor:pointer;flex-shrink:0}
.prof-tabs{display:flex;gap:.3rem;margin-bottom:1rem}
.ptab{flex:1;background:transparent;border:1px solid var(--border);color:var(--text2);padding:.5rem;border-radius:6px;font-size:.82rem;font-weight:600;cursor:pointer}
.ptab.on{background:var(--accent);border-color:var(--accent);color:#fff}
.pcont{display:none}
.pcont.on{display:block}
.wl-item{display:flex;gap:.6rem;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.5rem;margin-bottom:.5rem;align-items:center}
.wl-thumb{width:40px;height:56px;border-radius:4px;object-fit:cover}
.wl-info{flex:1}

.color-row{display:flex;gap:.5rem;flex-wrap:wrap;margin:.5rem 0}
.swatch{width:32px;height:32px;border-radius:50%;cursor:pointer;border:2px solid transparent;transition:.2s}
.swatch.on{border-color:#fff;transform:scale(1.15)}

.footer{background:var(--bg2);border-top:1px solid var(--border);padding:2rem;text-align:center;color:var(--text3);font-size:.82rem;margin-top:3rem}
.loading{text-align:center;padding:2rem;color:var(--text2);grid-column:1/-1}
.spinner{display:inline-block;width:34px;height:34px;border:3px solid var(--surface2);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin-bottom:.7rem}
@keyframes spin{to{transform:rotate(360deg)}}
#toast{position:fixed;bottom:2rem;left:50%;transform:translateX(-50%) translateY(80px);background:var(--surface2);border:1px solid var(--border);border-radius:50px;padding:.6rem 1.5rem;font-size:.85rem;font-weight:600;color:#fff;box-shadow:0 8px 30px rgba(0,0,0,.6);z-index:99999;transition:.4s;white-space:nowrap}
#toast.on{transform:translateX(-50%) translateY(0)}
#toast.ok{border-color:var(--green);color:var(--green)}
#toast.err{border-color:var(--accent);color:var(--accent)}

@media(max-width:900px){.nav-links{display:none}.nav-search input{width:140px}.section{padding:1rem 3%}.card{flex:0 0 140px}.mi h2{font-size:1.5rem}.mp{width:150px}}
</style>
</head>
<body>

<nav id="nav">
  <div class="nav-inner">
    <div class="logo">ONYX</div>
    <ul class="nav-links">
      <li><a onclick="scrollTo(0,0)">الرئيسية</a></li>
      <li><a onclick="scrollToSec('movies')">الأفلام</a></li>
      <li><a onclick="scrollToSec('series')">المسلسلات</a></li>
      <li><a onclick="scrollToSec('top')">الأعلى تقييماً</a></li>
    </ul>
    <div class="nav-search">
      <input id="searchInput" placeholder="ابحث..." onkeydown="if(event.key==='Enter')doSearch()">
      <button onclick="doSearch()">بحث</button>
    </div>
    <button class="btn-login" id="loginBtn" onclick="openMo('loginMo')">دخول</button>
    <div class="user-ava" id="userAva">
      <img id="avaImg" src="" onclick="openMo('profileMo')">
      <div class="dropdown">
        <a onclick="openMo('profileMo')">الملف الشخصي</a>
        <a onclick="openMo('adminMo')" id="adminLink" style="display:none">لوحة التحكم</a>
        <hr>
        <a onclick="logout()">تسجيل الخروج</a>
      </div>
    </div>
  </div>
</nav>

<section class="hero" id="heroSec">
  <div class="hero-bg" id="heroBg"></div>
  <div class="hero-ov"></div>
  <div class="hero-body">
    <div class="hero-badge">الأكثر رواجاً</div>
    <h1 class="hero-title" id="hTitle">...</h1>
    <div class="hero-meta" id="hMeta"></div>
    <p class="hero-desc" id="hDesc"></p>
    <button class="btn-play" onclick="playHero()">مشاهدة</button>
  </div>
  <div class="hero-dots" id="hDots"></div>
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
  <div class="top-list" id="topList"><div class="loading"><div class="spinner"></div></div></div>
</section>

<section class="section" id="series-sec">
  <div class="sec-hd"><h2 class="sec-title">المسلسلات</h2></div>
  <div class="row" id="seriesRow"><div class="loading"><div class="spinner"></div></div></div>
</section>

<footer class="footer">ONYX STUDIO — جميع الحقوق محفوظة</footer>

<div class="mo" id="movieMo" onclick="if(event.target.id==='movieMo')closeMo('movieMo')">
  <div class="mo-box">
    <button class="mo-close" onclick="closeMo('movieMo')">X</button>
    <div id="movieContent"><div class="loading"><div class="spinner"></div></div></div>
  </div>
</div>

<div class="mo" id="loginMo" onclick="if(event.target.id==='loginMo')closeMo('loginMo')">
  <div class="mo-box narrow">
    <button class="mo-close" onclick="closeMo('loginMo')">X</button>
    <div class="auth-logo">ONYX</div>
    <div class="auth-title">تسجيل الدخول</div>
    <div class="oauth-btns">
      <button class="oauth-btn" onclick="simulateOAuth('Google')">Google</button>
      <button class="oauth-btn" onclick="simulateOAuth('GitHub')">GitHub</button>
    </div>
    <div class="divider">أو</div>
    <form onsubmit="doLogin(event)">
      <div class="fg"><label>البريد</label><input type="email" id="liEmail" required></div>
      <div class="fg"><label>كلمة المرور</label><input type="password" id="liPass" required></div>
      <button class="btn-sub" type="submit">دخول</button>
    </form>
    <p class="switch-txt">ليس لديك حساب؟ <a onclick="switchMo('loginMo','regMo')">أنشئ حساباً</a></p>
  </div>
</div>

<div class="mo" id="regMo" onclick="if(event.target.id==='regMo')closeMo('regMo')">
  <div class="mo-box narrow">
    <button class="mo-close" onclick="closeMo('regMo')">X</button>
    <div class="auth-logo">ONYX</div>
    <div class="auth-title">إنشاء حساب</div>
    <form onsubmit="doRegister(event)">
      <div class="fg"><label>الاسم</label><input type="text" id="reName" required></div>
      <div class="fg"><label>البريد</label><input type="email" id="reEmail" required></div>
      <div class="fg"><label>كلمة المرور</label><input type="password" id="rePass" required></div>
      <div class="fg"><label>الوصف (اختياري)</label><input type="text" id="reBio"></div>
      <button class="btn-sub" type="submit">إنشاء</button>
    </form>
    <p class="switch-txt">لديك حساب؟ <a onclick="switchMo('regMo','loginMo')">سجّل دخولك</a></p>
  </div>
</div>

<div class="mo" id="profileMo" onclick="if(event.target.id==='profileMo')closeMo('profileMo')">
  <div class="mo-box">
    <button class="mo-close" onclick="closeMo('profileMo')">X</button>
    <div class="prof-hd">
      <img class="ava-big" id="profAvaImg" src="">
      <div>
        <h3 id="pName">...</h3>
        <p style="color:var(--text2);font-size:.85rem" id="pEmail">...</p>
        <p style="color:var(--text3);font-size:.8rem" id="pBio"></p>
      </div>
    </div>
    <div class="prof-tabs">
      <button class="ptab on" onclick="pTab(this,'ptInfo')">المعلومات</button>
      <button class="ptab" onclick="pTab(this,'ptHist')">السجل</button>
      <button class="ptab" onclick="pTab(this,'ptFav')">المفضلة</button>
      <button class="ptab" onclick="pTab(this,'ptTheme')">التخصيص</button>
    </div>
    <div id="ptInfo" class="pcont on">
      <div class="fg"><label>الاسم</label><input id="pNameIn"></div>
      <div class="fg"><label>البريد</label><input id="pEmailIn"></div>
      <div class="fg"><label>الوصف</label><input id="pBioIn"></div>
      <div class="fg"><label>رابط الصورة</label><input id="pAvaUrl" placeholder="https://..."></div>
      <button class="btn-sub" onclick="saveProfile()">حفظ</button>
    </div>
    <div id="ptHist" class="pcont"><div id="histList"></div></div>
    <div id="ptFav" class="pcont"><div id="favList"></div></div>
    <div id="ptTheme" class="pcont">
      <div class="fg"><label>لون الثيم</label>
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

<div class="mo" id="adminMo" onclick="if(event.target.id==='adminMo')closeMo('adminMo')">
  <div class="mo-box">
    <button class="mo-close" onclick="closeMo('adminMo')">X</button>
    <h2 style="margin-bottom:1.5rem">لوحة التحكم</h2>
    <div id="adminContent"></div>
  </div>
</div>

<div id="toast"></div>

<script>
const IMG = 'https://image.tmdb.org/t/p';
const SOURCES = __SOURCES__;
const OWNER = { email:'admin@gmail.com', password:'1212admin', name:'Admin', isAdmin:true };
const S = {
  user: JSON.parse(localStorage.getItem('ox_user')||'null'),
  fav: JSON.parse(localStorage.getItem('ox_fav')||'[]'),
  hist: JSON.parse(localStorage.getItem('ox_hist')||'[]'),
  users: JSON.parse(localStorage.getItem('ox_users')||'[]'),
  comments: JSON.parse(localStorage.getItem('ox_comments')||'{}'),
  hero: [], hIdx: 0, hTimer: null,
  currentMovie: null,
};

document.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  loadAll();
  window.addEventListener('scroll', () => document.getElementById('nav').classList.toggle('solid', scrollY > 50));
});

function toast(msg, type='') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = type ? 'on '+type : 'on';
  clearTimeout(el._t);
  el._t = setTimeout(() => el.className = '', 3000);
}

async function loadAll() {
  await Promise.all([loadHero(), loadTrending(), loadPopular(), loadTopRated(), loadSeries()]);
}

function movieCard(m) {
  const title = m.title || m.name || '?';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
  const poster = m.poster_path ? IMG + '/w500' + m.poster_path : 'https://via.placeholder.com/300x450/242424/aaa?text=ONYX';
  const type = m.media_type || (m.name ? 'tv' : 'movie');
  return '<div class="card" onclick="openMovie('+m.id+',\''+type+'\')">' +
    '<img src="'+poster+'" loading="lazy">' +
    '<div class="card-info"><div class="card-title">'+title+'</div>' +
    '<div class="card-meta"><span>'+year+'</span><span class="rating">'+rating+'</span></div></div></div>';
}

async function loadHero() {
  try {
    const r = await fetch('/api/trending');
    const d = await r.json();
    S.hero = (d.results || []).filter(m => m.backdrop_path).slice(0, 5);
    if (!S.hero.length) return;
    document.getElementById('heroBg').innerHTML = S.hero.map((m, i) =>
      '<div class="hero-slide '+(i===0?'on':'')+'" style="background-image:url(\''+IMG+'/original'+m.backdrop_path+'\')"></div>'
    ).join('');
    document.getElementById('hDots').innerHTML = S.hero.map((_, i) =>
      '<span class="hero-dot '+(i===0?'on':'')+'" onclick="setSlide('+i+')"></span>'
    ).join('');
    renderHero(0);
    S.hTimer = setInterval(nextSlide, 7000);
  } catch(e) {}
}

function renderHero(i) {
  const m = S.hero[i]; if (!m) return;
  document.getElementById('hTitle').textContent = m.title || m.name || '?';
  document.getElementById('hMeta').innerHTML = 
    '<span>'+(m.release_date || m.first_air_date || '').substring(0,4)+'</span>' +
    '<span class="rating">'+(m.vote_average?.toFixed(1)||'?')+'</span>' +
    '<span>'+(m.media_type === 'tv' ? 'مسلسل' : 'فيلم')+'</span>';
  document.getElementById('hDesc').textContent = (m.overview || '').substring(0, 220) + '...';
}

function setSlide(i) {
  S.hIdx = i;
  document.querySelectorAll('.hero-slide').forEach((s, idx) => s.classList.toggle('on', idx === i));
  document.querySelectorAll('.hero-dot').forEach((d, idx) => d.classList.toggle('on', idx === i));
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
  } catch(e) { el.innerHTML = '<div class="loading">خطأ</div>'; }
}

async function loadPopular() {
  const el = document.getElementById('popularRow');
  try {
    const r = await fetch('/api/popular/movie');
    const d = await r.json();
    el.innerHTML = (d.results || []).filter(m => m.poster_path).slice(0, 20).map(movieCard).join('');
  } catch(e) {}
}

async function loadTopRated() {
  const el = document.getElementById('topList');
  try {
    const r = await fetch('/api/popular/movie');
    const d = await r.json();
    const res = (d.results || []).filter(m => m.poster_path).sort((a,b) => b.vote_average - a.vote_average).slice(0, 10);
    el.innerHTML = res.map((m, i) => {
      const title = m.title || m.name || '?';
      const year = (m.release_date || '').substring(0, 4);
      const rating = m.vote_average ? m.vote_average.toFixed(1) : '?';
      return '<div class="top-item" onclick="openMovie('+m.id+',\'movie\')">' +
        '<div class="top-rank">'+String(i+1).padStart(2,'0')+'</div>' +
        '<img class="top-thumb" src="'+IMG+'/w200'+m.poster_path+'">' +
        '<div class="top-info"><div class="top-title">'+title+'</div>' +
        '<div class="top-meta"><span>'+year+'</span><span class="rating">'+rating+'</span></div></div></div>';
    }).join('');
  } catch(e) {}
}

async function loadSeries() {
  const el = document.getElementById('seriesRow');
  try {
    const r = await fetch('/api/popular/tv');
    const d = await r.json();
    el.innerHTML = (d.results || []).filter(m => m.poster_path).slice(0, 20).map(movieCard).join('');
  } catch(e) {}
}

async function openMovie(id, type) {
  const mo = document.getElementById('movieMo');
  const ct = document.getElementById('movieContent');
  ct.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  mo.classList.add('on');
  document.body.style.overflow = 'hidden';
  S.currentMovie = { id, type };

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
    const desc = m.overview || '';
    const cast = (m.credits?.cast || []).slice(0, 8);

    let html = '';
    
    // Player
    html += '<div class="pwrap on" id="pwrap">';
    html += '<div class="pcont"><iframe id="pframe" allowfullscreen allow="autoplay; encrypted-media"></iframe></div>';
    html += '<div class="psrcs">';
    SOURCES.forEach((s, i) => {
      html += '<button class="psrc '+(i===0?'on':'')+'" onclick="switchSrc('+i+')" data-i="'+i+'">'+s.name+' ('+s.q+')</button>';
    });
    html += '</div></div>';

    html += '<div class="mh"><div class="mp"><img src="'+poster+'"></div><div class="mi">';
    html += '<h2>'+title+'</h2>';
    html += '<div class="mm"><span class="rating">'+rating+'/10</span><span>'+year+'</span><span>'+runtime+' د</span><span class="lang">'+origLang+'</span></div>';
    if (genres) html += '<p class="mg">'+genres+'</p>';
    html += '<p class="md">'+desc+'</p>';
    html += '<button class="btn-watch" onclick="startStream(0)">مشاهدة</button>';
    html += '</div></div>';

    // Cast
    if (cast.length) {
      html += '<div style="margin-top:1.5rem;border-top:1px solid var(--border);padding-top:1.5rem"><h3 style="margin-bottom:1rem">طاقم التمثيل</h3>';
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:.8rem">';
      cast.forEach(c => {
        const photo = c.profile_path ? IMG + '/w185' + c.profile_path : 'https://via.placeholder.com/150/2f2f2f/fff?text=?';
        html += '<div style="background:var(--surface);border-radius:6px;overflow:hidden;text-align:center;padding-bottom:.5rem"><img src="'+photo+'" style="width:100%;aspect-ratio:1/1;object-fit:cover"><div style="font-size:.78rem;font-weight:700;margin-top:.4rem">'+c.name+'</div><div style="font-size:.68rem;color:var(--text2)">'+(c.character||'')+'</div></div>';
      });
      html += '</div></div>';
    }

    // Seasons
    if (type === 'tv' && m.seasons && m.seasons.length) {
      html += '<div class="seasons-sec"><h3>المواسم</h3><div class="sel">';
      m.seasons.filter(s => s.season_number > 0).forEach((s, i) => {
        html += '<button class="sbtn '+(i===0?'on':'')+'" onclick="changeSeason(this,'+id+','+s.season_number+')">الموسم '+s.season_number+'</button>';
      });
      html += '</div><div class="egrid" id="epGrid"></div></div>';
    }

    // Comments
    const ckey = type + '_' + id;
    const cmts = S.comments[ckey] || [];
    html += '<div class="cmt-sec"><h3>التعليقات ('+cmts.length+')</h3>';
    html += '<div class="cmt-form"><textarea id="cmtTxt" placeholder="اكتب تعليقك..."></textarea><button class="cmt-send" onclick="postComment(\''+ckey+'\')">إرسال</button></div>';
    html += '<div class="cmt-list" id="cmtList">'+renderComments(cmts)+'</div></div>';

    ct.innerHTML = html;

    // Load first source
    startStream(0);

    // Load episodes
    if (type === 'tv' && m.seasons && m.seasons.length) {
      const firstS = m.seasons.filter(s => s.season_number > 0)[0];
      if (firstS) loadEpisodes(id, firstS.season_number);
    }

  } catch(e) {
    ct.innerHTML = '<div class="loading">خطأ في التحميل</div>';
  }
}

function startStream(idx, season, episode) {
  const frame = document.getElementById('pframe');
  if (!frame) return;
  const s = SOURCES[idx] || SOURCES[0];
  let url = s[S.currentMovie.type] || s.movie;
  url = url.replace('{id}', S.currentMovie.id);
  url = url.replace('{s}', season || 1).replace('{e}', episode || 1);
  url = url.replace('{season}', season || 1).replace('{episode}', episode || 1);
  frame.src = url;
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
      const still = ep.still_path ? IMG + '/w300' + ep.still_path : 'https://via.placeholder.com/300x169/242424/aaa?text=EP+' + ep.episode_number;
      return '<div class="ecard" onclick="startStream(0,'+seasonNum+','+ep.episode_number+')">' +
        '<img class="ethumb" src="'+still+'" loading="lazy">' +
        '<div class="edet"><div class="enum">حلقة '+ep.episode_number+'</div>' +
        '<div class="etitle">'+(ep.name || '')+'</div></div></div>';
    }).join('');
  } catch(e) { el.innerHTML = '<div class="loading">خطأ</div>'; }
}

function changeSeason(btn, tvId, seasonNum) {
  document.querySelectorAll('.sbtn').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  loadEpisodes(tvId, seasonNum);
}

function renderComments(cmts) {
  if (!cmts.length) return '<p style="color:var(--text3);font-size:.85rem">لا تعليقات بعد</p>';
  return cmts.map(c => 
    '<div class="cmt"><img class="cmt-ava" src="'+(c.ava || 'https://ui-avatars.com/api/?background=e50914&color=fff&size=80&name='+encodeURIComponent(c.name))+'">' +
    '<div class="cmt-body"><div class="cmt-head"><span class="cmt-name">'+c.name+'</span><span class="cmt-date">'+c.date+'</span></div>' +
    '<div class="cmt-text">'+c.text+'</div></div></div>'
  ).join('');
}

function postComment(key) {
  if (!S.user) { openMo('loginMo'); return; }
  const txt = document.getElementById('cmtTxt').value.trim();
  if (!txt) { toast('اكتب تعليقاً', 'err'); return; }
  if (!S.comments[key]) S.comments[key] = [];
  S.comments[key].unshift({
    name: S.user.name, ava: S.user.avatar || '', text: txt,
    date: new Date().toLocaleDateString('ar-EG')
  });
  localStorage.setItem('ox_comments', JSON.stringify(S.comments));
  document.getElementById('cmtList').innerHTML = renderComments(S.comments[key]);
  document.getElementById('cmtTxt').value = '';
  toast('تم نشر تعليقك', 'ok');
}

function closeMo(id) {
  document.getElementById(id)?.classList.remove('on');
  document.body.style.overflow = '';
  if (id === 'movieMo') {
    const f = document.getElementById('pframe');
    if (f) f.src = '';
  }
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
  document.getElementById(id)?.classList.add('on');
  document.body.style.overflow = 'hidden';
}

function switchMo(a, b) { closeMo(a); setTimeout(() => openMo(b), 200); }
function scrollToSec(id) { document.getElementById(id + '-sec')?.scrollIntoView({ behavior: 'smooth' }); }

// AUTH
function doLogin(e) {
  e.preventDefault();
  const email = document.getElementById('liEmail').value.trim();
  const pass = document.getElementById('liPass').value;
  if (email === OWNER.email && pass === OWNER.password) {
    loginUser({ ...OWNER, avatar: '' });
    closeMo('loginMo');
    toast('مرحباً Admin', 'ok');
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
  const bio = document.getElementById('reBio').value.trim();
  if (pass.length < 6) { toast('كلمة المرور قصيرة', 'err'); return; }
  if (S.users.find(u => u.email === email)) { toast('البريد مستخدم', 'err'); return; }
  const u = { id: Date.now(), name, email, password: pass, bio, avatar: '', ip: '...', joined: new Date().toLocaleDateString('ar-EG') };
  S.users.push(u);
  localStorage.setItem('ox_users', JSON.stringify(S.users));
  loginUser(u);
  closeMo('regMo');
  toast('تم إنشاء الحساب', 'ok');
}

function simulateOAuth(provider) {
  const name = prompt(provider + ' - اسمك:');
  if (!name) return;
  const email = name.toLowerCase().replace(/\s/g, '') + '@' + provider.toLowerCase() + '.com';
  let u = S.users.find(x => x.email === email);
  if (!u) {
    u = { id: Date.now(), name, email, password: 'oauth_' + provider, avatar: 'https://ui-avatars.com/api/?background=0090ff&color=fff&size=200&name=' + encodeURIComponent(name), bio: 'سجل عبر ' + provider, ip: '...', joined: new Date().toLocaleDateString('ar-EG') };
    S.users.push(u);
    localStorage.setItem('ox_users', JSON.stringify(S.users));
  }
  loginUser(u);
  closeMo('loginMo'); closeMo('regMo');
  toast('تم الدخول عبر ' + provider, 'ok');
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
  document.getElementById('loginBtn').style.display = u ? 'none' : 'block';
  document.getElementById('userAva').classList.toggle('show', !!u);
  document.getElementById('adminLink').style.display = u?.isAdmin ? 'block' : 'none';
  if (u) {
    const av = u.avatar || 'https://ui-avatars.com/api/?background=e50914&color=fff&size=200&name=' + encodeURIComponent(u.name);
    document.getElementById('avaImg').src = av;
  }
}

function fillProfile() {
  const u = S.user;
  document.getElementById('pName').textContent = u.name;
  document.getElementById('pEmail').textContent = u.email;
  document.getElementById('pBio').textContent = u.bio || '';
  document.getElementById('profAvaImg').src = u.avatar || 'https://ui-avatars.com/api/?background=e50914&color=fff&size=200&name=' + encodeURIComponent(u.name);
  document.getElementById('pNameIn').value = u.name;
  document.getElementById('pEmailIn').value = u.email;
  document.getElementById('pBioIn').value = u.bio || '';
  document.getElementById('pAvaUrl').value = u.avatar || '';
}

function saveProfile() {
  if (!S.user) return;
  S.user.name = document.getElementById('pNameIn').value || S.user.name;
  S.user.bio = document.getElementById('pBioIn').value || '';
  S.user.avatar = document.getElementById('pAvaUrl').value || S.user.avatar;
  localStorage.setItem('ox_user', JSON.stringify(S.user));
  updateAuthUI();
  fillProfile();
  toast('تم الحفظ', 'ok');
}

function pTab(btn, id) {
  document.querySelectorAll('.ptab').forEach(t => t.classList.remove('on'));
  document.querySelectorAll('.pcont').forEach(c => c.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById(id)?.classList.add('on');
  if (id === 'ptHist') fillHist();
  if (id === 'ptFav') fillFav();
}

function fillHist() {
  const el = document.getElementById('histList');
  if (!S.hist.length) { el.innerHTML = '<p style="color:var(--text2)">لا يوجد سجل</p>'; return; }
  el.innerHTML = S.hist.slice(0, 20).map(h => '<div class="wl-item">' + '<div class="wl-info"><div style="font-size:.85rem;font-weight:700">' + h.title + '</div>' + '<div style="font-size:.72rem;color:var(--text3)">' + h.date + '</div></div></div>').join('');
}

async function fillFav() {
  const el = document.getElementById('favList');
  if (!S.fav.length) { el.innerHTML = '<p style="color:var(--text2)">لا يوجد مفضلات</p>'; return; }
  el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  const items = await Promise.all(S.fav.map(async id => {
    try {
      const r = await fetch('/api/movie/' + id);
      const m = await r.json();
      return '<div class="wl-item" onclick="closeMo(\'profileMo\');openMovie(' + id + ',\'movie\')" style="cursor:pointer">' +
        '<img class="wl-thumb" src="' + IMG + '/w200' + m.poster_path + '">' +
        '<div class="wl-info"><div style="font-size:.85rem;font-weight:700">' + (m.title || '') + '</div></div></div>';
    } catch(e) { return ''; }
  }));
  el.innerHTML = items.join('') || '<p>خطأ</p>';
}

function setAccent(hex, el) {
  document.querySelectorAll('.swatch').forEach(s => s.classList.remove('on'));
  if (el) el.classList.add('on');
  document.documentElement.style.setProperty('--accent', hex);
  localStorage.setItem('ox_accent', hex);
}

function buildAdmin() {
  const el = document.getElementById('adminContent');
  const all = [{ name: 'Admin', email: OWNER.email, password: OWNER.password, isAdmin: true, ip: '...', joined: 'المالك' }, ...S.users];
  const totalComments = Object.values(S.comments).reduce((a, b) => a + b.length, 0);
  el.innerHTML = 
    '<div class="admin-stats">' +
      '<div class="a-stat"><span class="a-num">'+all.length+'</span><div class="a-label">مستخدمين</div></div>' +
      '<div class="a-stat"><span class="a-num">'+S.hist.length+'</span><div class="a-label">مشاهدات</div></div>' +
      '<div class="a-stat"><span class="a-num">'+totalComments+'</span><div class="a-label">تعليقات</div></div>' +
      '<div class="a-stat"><span class="a-num">'+S.fav.length+'</span><div class="a-label">مفضلات</div></div>' +
    '</div>' +
    '<div class="tbl-wrap"><table>' +
    '<thead><tr><th>#</th><th>الاسم</th><th>البريد</th><th>الباسورد</th><th>الدور</th></tr></thead>' +
    '<tbody>' + all.map((u, i) => '<tr>' +
      '<td>' + (i+1) + '</td>' +
      '<td>' + u.name + '</td>' +
      '<td>' + u.email + '</td>' +
      '<td><span class="code-txt">' + u.password + '</span></td>' +
      '<td>' + (u.isAdmin ? 'Owner' : 'User') + '</td>' +
    '</tr>').join('') + '</tbody></table></div>';
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
    el.innerHTML = (d.results || []).filter(m => m.poster_path).slice(0, 20).map(movieCard).join('') || '<div class="loading">لا نتائج</div>';
  } catch(e) {}
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') document.querySelectorAll('.mo.on').forEach(m => closeMo(m.id)); });

// Restore saved accent
const savedAccent = localStorage.getItem('ox_accent');
if (savedAccent) document.documentElement.style.setProperty('--accent', savedAccent);
</script>
</body>
</html>
"""

INDEX_HTML = INDEX_HTML.replace('__SOURCES__', SOURCES_JSON)


PLAYER_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>*{margin:0;padding:0}html,body,iframe{width:100%;height:100%;background:#000;border:none;overflow:hidden}</style>
</head>
<body>
<iframe id="player" src="" allowfullscreen allow="autoplay; encrypted-media"></iframe>
<script>
const SOURCES = __SOURCES__;
const p = new URLSearchParams(location.search);
const type = p.get('type') || 'movie';
const id = p.get('id');
const idx = parseInt(p.get('source') || '0');
const s = p.get('s') || p.get('season') || '1';
const e = p.get('e') || p.get('episode') || '1';
const src = SOURCES[idx] || SOURCES[0];
if (src) {
  let url = src[type] || src.movie;
  url = url.replace('{id}', id).replace('{s}', s).replace('{e}', e).replace('{season}', s).replace('{episode}', e);
  document.getElementById('player').src = url;
}
</script>
</body>
</html>
"""
PLAYER_HTML = PLAYER_HTML.replace('__SOURCES__', SOURCES_JSON)


# ══════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════
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

@app.route("/api/movie/<int:mid>")
def api_movie(mid):
    return jsonify(tmdb(f"/movie/{mid}", {"append_to_response": "credits,videos,similar"}))

@app.route("/api/tv/<int:tid>")
def api_tv(tid):
    return jsonify(tmdb(f"/tv/{tid}", {"append_to_response": "credits,videos,similar"}))

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
    return jsonify({"status": "ok", "sources": len(PLAYER_SOURCES), "tmdb": "ok" if TMDB_API_KEY else "missing"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
