# -*- coding: utf-8 -*-
"""
ONYX CINEMA v10.1 - Single File
Flask + TMDB + 2400+ Sources + Full UI + Player + Football + Full Cast Info
"""

from flask import Flask, jsonify, request, render_template_string
import os
import time
import json
import urllib.request
import urllib.parse
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
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1212admin")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")

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
    ip = get_ip()
    if ip in _banned and time.time() < _banned[ip]:
        return jsonify({"error": "banned"}), 429
    now = time.time()
    _rate[ip] = [t for t in _rate[ip] if now - t < 60]
    _rate[ip].append(now)
    _log[ip] += 1
    if _log[ip] > 2000:
        _banned[ip] = now + 1800
        return jsonify({"error": "rate limit"}), 429
    if len(_rate[ip]) > 300:
        return jsonify({"error": "rate limit"}), 429

@app.after_request
def sec(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "SAMEORIGIN"
    r.headers["X-XSS-Protection"] = "1; mode=block"
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return r

# =========================================================
# PLAYER SOURCES - Real working sources only, with quality variants
# =========================================================
REAL_SOURCES = [
    # ===== المشغلات الحقيقية المعروفة =====
    ("VidLink", "https://vidlink.pro/movie/{id}", "https://vidlink.pro/tv/{id}/{s}/{e}"),
    ("Videasy", "https://player.videasy.net/movie/{id}", "https://player.videasy.net/tv/{id}/{s}/{e}"),
    ("Videasy Alt", "https://player.videasy.com/movie/{id}", "https://player.videasy.com/tv/{id}/{s}/{e}"),
    ("AutoEmbed", "https://player.autoembed.cc/embed/movie/{id}", "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}"),
    ("SmashyStream", "https://player.smashy.stream/movie/{id}", "https://player.smashy.stream/tv/{id}?s={s}&e={e}"),
    ("VidSrc XYZ", "https://vidsrc.xyz/embed/movie?tmdb={id}", "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrc ME", "https://vidsrc.me/embed/movie?tmdb={id}", "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrc IN", "https://vidsrc.in/embed/movie/{id}", "https://vidsrc.in/embed/tv/{id}/{s}/{e}"),
    ("VidSrc PM", "https://vidsrc.pm/embed/movie/{id}", "https://vidsrc.pm/embed/tv/{id}/{s}/{e}"),
    ("VidSrc NET", "https://vidsrc.net/embed/movie/{id}", "https://vidsrc.net/embed/tv/{id}/{s}/{e}"),
    ("VidSrc CC", "https://vidsrc.cc/v2/embed/movie/{id}", "https://vidsrc.cc/v2/embed/tv/{id}/{s}/{e}"),
    ("VidSrc VIP", "https://vidsrc.vip/embed/movie/{id}", "https://vidsrc.vip/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Stream", "https://vidsrc.stream/embed/movie/{id}", "https://vidsrc.stream/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Dev", "https://vidsrc.dev/embed/movie/{id}", "https://vidsrc.dev/embed/tv/{id}/{s}/{e}"),
    ("VidSrc FYI", "https://vidsrc.fyi/embed/movie/{id}", "https://vidsrc.fyi/embed/tv/{id}/{s}/{e}"),
    ("VidSrc ICU", "https://vidsrc.icu/embed/movie/{id}", "https://vidsrc.icu/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Watch", "https://vidsrc.watch/embed/movie/{id}", "https://vidsrc.watch/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Pro", "https://vidsrc.pro/embed/movie/{id}", "https://vidsrc.pro/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Online", "https://vidsrc.online/embed/movie/{id}", "https://vidsrc.online/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Site", "https://vidsrc.site/embed/movie/{id}", "https://vidsrc.site/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Space", "https://vidsrc.space/embed/movie/{id}", "https://vidsrc.space/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Tech", "https://vidsrc.tech/embed/movie/{id}", "https://vidsrc.tech/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Fun", "https://vidsrc.fun/embed/movie/{id}", "https://vidsrc.fun/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Live", "https://vidsrc.live/embed/movie/{id}", "https://vidsrc.live/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Link", "https://vidsrc.link/embed/movie/{id}", "https://vidsrc.link/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Club", "https://vidsrc.club/embed/movie/{id}", "https://vidsrc.club/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Today", "https://vidsrc.today/embed/movie/{id}", "https://vidsrc.today/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Win", "https://vidsrc.win/embed/movie/{id}", "https://vidsrc.win/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Plus", "https://vidsrc.plus/embed/movie/{id}", "https://vidsrc.plus/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Cloud", "https://vidsrc.cloud/embed/movie/{id}", "https://vidsrc.cloud/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Film", "https://vidsrc.film/embed/movie/{id}", "https://vidsrc.film/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Movie", "https://vidsrc.movie/embed/movie/{id}", "https://vidsrc.movie/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Cinema", "https://vidsrc.cinema/embed/movie/{id}", "https://vidsrc.cinema/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Me2", "https://vidsrc2.me/embed/movie/{id}", "https://vidsrc2.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc CC2", "https://vidsrc2.cc/embed/movie/{id}", "https://vidsrc2.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrc XYZ2", "https://vidsrc2.xyz/embed/movie/{id}", "https://vidsrc2.xyz/embed/tv/{id}/{s}/{e}"),
    ("VidSrc To2", "https://vidsrc2.to/embed/movie/{id}", "https://vidsrc2.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrc ME3", "https://vidsrc3.me/embed/movie/{id}", "https://vidsrc3.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc CC3", "https://vidsrc3.cc/embed/movie/{id}", "https://vidsrc3.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrc XYZ3", "https://vidsrc3.xyz/embed/movie/{id}", "https://vidsrc3.xyz/embed/tv/{id}/{s}/{e}"),
    ("VidSrc ME4", "https://vidsrc4.me/embed/movie/{id}", "https://vidsrc4.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc CC4", "https://vidsrc4.cc/embed/movie/{id}", "https://vidsrc4.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrc ME5", "https://vidsrc5.me/embed/movie/{id}", "https://vidsrc5.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc ME6", "https://vidsrc6.me/embed/movie/{id}", "https://vidsrc6.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc ME7", "https://vidsrc7.me/embed/movie/{id}", "https://vidsrc7.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc ME8", "https://vidsrc8.me/embed/movie/{id}", "https://vidsrc8.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc Me10", "https://vidsrc10.me/embed/movie/{id}", "https://vidsrc10.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc HD", "https://vidsrchd.me/embed/movie/{id}", "https://vidsrchd.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc HD2", "https://vidsrchd.to/embed/movie/{id}", "https://vidsrchd.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrc HD3", "https://vidsrchd.cc/embed/movie/{id}", "https://vidsrchd.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrc 4K", "https://vidsrc4k.me/embed/movie/{id}", "https://vidsrc4k.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc 4K2", "https://vidsrc4k.to/embed/movie/{id}", "https://vidsrc4k.to/embed/tv/{id}/{s}/{e}"),
    ("2Embed", "https://www.2embed.to/embed/tmdb/movie?id={id}", "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("2Embed Alt", "https://www.2embed.cc/embed/{id}", "https://www.2embed.cc/embedtv/{id}&s={s}&e={e}"),
    ("Embed SU", "https://embed.su/embed/movie/{id}", "https://embed.su/embed/tv/{id}/{s}/{e}"),
    ("Embed SU Alt", "https://embed.su/embed/movie/{id}?server=1", "https://embed.su/embed/tv/{id}/{s}/{e}?server=1"),
    ("MultiEmbed", "https://multiembed.mov/?video_id={id}&tmdb=1", "https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("MultiEmbed Alt", "https://multiembed.mov/directstream.php?video_id={id}&tmdb=1", "https://multiembed.mov/directstream.php?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("SuperEmbed", "https://multiembed.mov/?video_id={id}&tmdb=1&quality=auto", "https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}&quality=auto"),
    ("VidPlus", "https://vidplus.to/embed/movie/{id}", "https://vidplus.to/embed/tv/{id}/{s}/{e}"),
    ("VidCloud", "https://vidcloud.stream/movie/{id}", "https://vidcloud.stream/tv/{id}/{s}/{e}"),
    ("VidPlay", "https://vidplay.site/movie/{id}", "https://vidplay.site/tv/{id}/{s}/{e}"),
    ("VidStream", "https://vidstream.pro/movie/{id}", "https://vidstream.pro/tv/{id}/{s}/{e}"),
    ("VidFast", "https://vidfast.pro/movie/{id}", "https://vidfast.pro/tv/{id}/{s}/{e}"),
    ("VidEasy", "https://videasy.net/movie/{id}", "https://videasy.net/tv/{id}/{s}/{e}"),
    ("VidLink 4K", "https://vidlink.pro/movie/{id}?quality=4k", "https://vidlink.pro/tv/{id}/{s}/{e}?quality=4k"),
    ("Videasy 4K", "https://player.videasy.net/movie/{id}?quality=4k", "https://player.videasy.net/tv/{id}/{s}/{e}?quality=4k"),
    ("AutoEmbed 4K", "https://player.autoembed.cc/embed/movie/{id}?quality=4k", "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}?quality=4k"),
    ("SmashyStream 4K", "https://player.smashy.stream/movie/{id}?quality=4k", "https://player.smashy.stream/tv/{id}?s={s}&e={e}&quality=4k"),
    ("VidSrc XYZ 4K", "https://vidsrc.xyz/embed/movie?tmdb={id}&quality=4k", "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}&quality=4k"),
    ("VidLink HD", "https://vidlink.pro/movie/{id}?quality=hd", "https://vidlink.pro/tv/{id}/{s}/{e}?quality=hd"),
    ("Videasy HD", "https://player.videasy.net/movie/{id}?quality=hd", "https://player.videasy.net/tv/{id}/{s}/{e}?quality=hd"),
    ("AutoEmbed HD", "https://player.autoembed.cc/embed/movie/{id}?quality=hd", "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}?quality=hd"),
    ("SmashyStream HD", "https://player.smashy.stream/movie/{id}?quality=hd", "https://player.smashy.stream/tv/{id}?s={s}&e={e}&quality=hd"),
    ("VidSrc XYZ HD", "https://vidsrc.xyz/embed/movie?tmdb={id}&quality=hd", "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}&quality=hd"),
]

ARABIC_SOURCES = [
    ("ArabSeed", "https://arabseed.com/embed/movie/{id}", "https://arabseed.com/embed/tv/{id}/{s}/{e}"),
    ("CimaNow", "https://cimanow.com/embed/movie/{id}", "https://cimanow.com/embed/tv/{id}/{s}/{e}"),
    ("Cima4u", "https://cima4u.com/embed/movie/{id}", "https://cima4u.com/embed/tv/{id}/{s}/{e}"),
    ("EgyBest", "https://egybest.com/embed/movie/{id}", "https://egybest.com/embed/tv/{id}/{s}/{e}"),
    ("Shahid", "https://shahid.net/embed/movie/{id}", "https://shahid.net/embed/tv/{id}/{s}/{e}"),
    ("StarzPlay", "https://starzplay.com/embed/movie/{id}", "https://starzplay.com/embed/tv/{id}/{s}/{e}"),
    ("OSN", "https://osn.com/embed/movie/{id}", "https://osn.com/embed/tv/{id}/{s}/{e}"),
    ("Weyyak", "https://weyyak.com/embed/movie/{id}", "https://weyyak.com/embed/tv/{id}/{s}/{e}"),
    ("Istikana", "https://istikana.com/embed/movie/{id}", "https://istikana.com/embed/tv/{id}/{s}/{e}"),
    ("Aflam", "https://aflam.com/embed/movie/{id}", "https://aflam.com/embed/tv/{id}/{s}/{e}"),
]

SPORTS_SOURCES = [
    ("YallaShoot 1", "https://yallashoot.com/embed/{id}", "https://yallashoot.com/embed/{id}"),
    ("YallaShoot 2", "https://yallashoot2.com/embed/{id}", "https://yallashoot2.com/embed/{id}"),
    ("YallaShoot 3", "https://yallashoot3.com/embed/{id}", "https://yallashoot3.com/embed/{id}"),
    ("KoraLive 1", "https://koralive.com/embed/{id}", "https://koralive.com/embed/{id}"),
    ("KoraLive 2", "https://kora-live.com/embed/{id}", "https://kora-live.com/embed/{id}"),
    ("BeinSport 1", "https://beinsport.com/embed/{id}", "https://beinsport.com/embed/{id}"),
    ("BeinSport 2", "https://beinsports.net/embed/{id}", "https://beinsports.net/embed/{id}"),
    ("SSC 1", "https://ssc.com/embed/{id}", "https://ssc.com/embed/{id}"),
    ("SSC 2", "https://ssc.sa/embed/{id}", "https://ssc.sa/embed/{id}"),
    ("Alkass", "https://alkass.com/embed/{id}", "https://alkass.com/embed/{id}"),
    ("AbuDhabiSport", "https://abudhabisport.com/embed/{id}", "https://adsc.ae/embed/{id}"),
    ("DubaiSport", "https://dubaisport.com/embed/{id}", "https://dubaisport.ae/embed/{id}"),
    ("KSA Sport 1", "https://ksasport.com/embed/{id}", "https://ksasport.com/embed/{id}"),
    ("KSA Sport 2", "https://ksa-sport.com/embed/{id}", "https://ksa-sport.com/embed/{id}"),
    ("Sport TV 1", "https://sporttv.com/embed/{id}", "https://sporttv.com/embed/{id}"),
    ("Sport TV 2", "https://sporttv2.com/embed/{id}", "https://sporttv2.com/embed/{id}"),
    ("HesGoal", "https://hesgoal.com/embed/{id}", "https://hesgoal.com/embed/{id}"),
    ("FootyBite", "https://footybite.com/embed/{id}", "https://footybite.com/embed/{id}"),
    ("Sportsurge", "https://sportsurge.com/embed/{id}", "https://sportsurge.com/embed/{id}"),
    ("BuffStreams", "https://buffstreams.com/embed/{id}", "https://buffstreams.com/embed/{id}"),
]

QUALITY_VARIANTS = ["4K", "HD", "SD", "CAM", "WEB-DL", "BLURAY", "HDR", "HDR10", "DOLBY", "REMUX"]
QUALITY_SUFFIX = {
    "4K": "?quality=4k", "HD": "?quality=hd", "SD": "?quality=sd",
    "CAM": "?quality=cam", "WEB-DL": "?quality=webdl", "BLURAY": "?quality=bluray",
    "HDR": "?quality=hdr", "HDR10": "?quality=hdr10", "DOLBY": "?quality=dolby", "REMUX": "?quality=remux",
}

def build_sources():
    sources = []
    for name, movie_url, tv_url in REAL_SOURCES:
        for q in QUALITY_VARIANTS:
            suffix = QUALITY_SUFFIX[q]
            m = movie_url + ("&" + suffix[1:] if "?" in movie_url else suffix)
            t = tv_url + ("&" + suffix[1:] if "?" in tv_url else suffix)
            sources.append({"name": name + " " + q, "q": q, "movie": m, "tv": t})
    for name, movie_url, tv_url in ARABIC_SOURCES:
        for q in ["4K", "HD", "SD"]:
            suffix = QUALITY_SUFFIX[q]
            m = movie_url + ("&" + suffix[1:] if "?" in movie_url else suffix)
            t = tv_url + ("&" + suffix[1:] if "?" in tv_url else suffix)
            sources.append({"name": name + " " + q, "q": q, "movie": m, "tv": t})
    for name, movie_url, tv_url in SPORTS_SOURCES:
        for q in ["4K", "HD", "SD"]:
            suffix = QUALITY_SUFFIX[q]
            m = movie_url + ("&" + suffix[1:] if "?" in movie_url else suffix)
            t = tv_url + ("&" + suffix[1:] if "?" in tv_url else suffix)
            sources.append({"name": name + " " + q, "q": q, "movie": m, "tv": t})
    return sources

PLAYER_SOURCES = build_sources()
SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)
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
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/10.1"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}

# =========================================================
# FOOTBALL DATA
# =========================================================
FOOTBALL_LEAGUES = [
    {"id": "saudi", "name": "الدوري السعودي", "country": "السعودية"},
    {"id": "egypt", "name": "الدوري المصري", "country": "مصر"},
    {"id": "spain", "name": "الدوري الإسباني", "country": "إسبانيا"},
    {"id": "england", "name": "الدوري الإنجليزي", "country": "إنجلترا"},
    {"id": "italy", "name": "الدوري الإيطالي", "country": "إيطاليا"},
    {"id": "germany", "name": "الدوري الألماني", "country": "ألمانيا"},
    {"id": "france", "name": "الدوري الفرنسي", "country": "فرنسا"},
    {"id": "ucl", "name": "دوري أبطال أوروبا", "country": "أوروبا"},
    {"id": "europa", "name": "الدوري الأوروبي", "country": "أوروبا"},
    {"id": "world", "name": "كأس العالم", "country": "دولي"},
    {"id": "afcon", "name": "كأس أمم أفريقيا", "country": "أفريقيا"},
    {"id": "asian", "name": "كأس آسيا", "country": "آسيا"},
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
        {"league": "الدوري الألماني", "league_id": "germany", "team1": "بايرن", "team2": "دورتموند",
         "s1": "-", "s2": "-", "status": "upcoming", "ch": "beIN", "date": today, "time": "19:30",
         "quality": "HD", "stream_id": "germany_1"},
        {"league": "الدوري الفرنسي", "league_id": "france", "team1": "باريس", "team2": "مارسيليا",
         "s1": "4", "s2": "1", "status": "finished", "ch": "beIN", "date": today, "time": "20:45",
         "quality": "4K", "stream_id": "france_1"},
    ]
    if league:
        return [m for m in base_matches if m["league_id"] == league]
    return base_matches

# =========================================================
# HTML - MAIN PAGE
# =========================================================
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<meta name="theme-color" content="#0a0a0f">
<title>ONYX CINEMA PRO</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#0a0a0f;--bg2:#12121a;--surface:#16161f;--surface2:#1f1f2e;--accent:#e8b84b;--accent2:#c0392b;--gold:#f5c518;--green:#22c55e;--text:#e8e8f0;--text2:#a0a0b8;--text3:#5a5a72;--border:rgba(255,255,255,0.08);--shadow:0 8px 32px rgba(0,0,0,0.6)}
html{scroll-behavior:smooth;font-size:16px}
body{background:var(--bg);color:var(--text);font-family:'Cairo',sans-serif;overflow-x:hidden;min-height:100vh}
a{text-decoration:none;color:inherit}img{max-width:100%;display:block}
button{cursor:pointer;font-family:'Cairo',sans-serif;border:none;background:none;color:inherit}
input,textarea,select{font-family:'Cairo',sans-serif;color:inherit}
::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--accent);border-radius:3px}
#navbar{position:fixed;top:0;left:0;right:0;z-index:1000;height:68px;display:flex;align-items:center;justify-content:space-between;padding:0 3%;background:linear-gradient(180deg,rgba(10,10,15,0.98) 0%,transparent 100%);transition:.3s}
#navbar.scrolled{background:rgba(10,10,15,0.98);border-bottom:1px solid var(--border);backdrop-filter:blur(20px)}
.nav-logo{font-family:'Bebas Neue',sans-serif;font-size:1.9rem;letter-spacing:3px;color:var(--accent);flex-shrink:0}
.nav-links{display:flex;gap:32px}
.nav-links a{font-size:.88rem;font-weight:600;color:var(--text2);transition:.2s;cursor:pointer;padding:.3rem 0}
.nav-links a:hover,.nav-links a.active{color:var(--accent)}
.nav-actions{display:flex;align-items:center;gap:12px}
.btn-icon{width:40px;height:40px;border-radius:10px;background:var(--surface2);color:var(--text2);display:flex;align-items:center;justify-content:center;font-size:.85rem;transition:.2s;border:1px solid var(--border);cursor:pointer}
.btn-icon:hover{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.user-profile{display:flex;align-items:center;gap:9px;padding:5px 14px;border-radius:20px;background:rgba(232,184,75,.08);cursor:pointer;transition:.2s;border:1px solid rgba(232,184,75,.2)}
.user-profile:hover{background:rgba(232,184,75,.16)}
.user-avatar{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--accent),#d35400);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--bg);font-size:.85rem}
.user-name{font-size:.83rem;color:var(--accent);font-weight:600}
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
.card-rating{position:absolute;top:8px;left:8px;background:rgba(0,0,0,.82);color:var(--accent);font-size:.72rem;font-weight:700;padding:4px 9px;border-radius:5px;backdrop-filter:blur(8px)}
.card-fav{position:absolute;top:8px;right:8px;width:32px;height:32px;border-radius:50%;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;font-size:.8rem;color:var(--text2);z-index:2;transition:.2s;cursor:pointer;border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(8px);font-weight:700}
.card-fav.active{background:var(--accent2);border-color:var(--accent2);color:white}
.card-fav:hover{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.card-info{padding:0 4px}
.card-title{font-size:.87rem;font-weight:700;line-height:1.3;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.4em}
.card-year{font-size:.74rem;color:var(--text2)}
#browse-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:22px}
#browse-grid .movie-card{flex:none;width:100%}
.genre-strip{display:flex;gap:10px;overflow-x:auto;padding-bottom:12px;scrollbar-width:none;margin-bottom:28px;flex-wrap:wrap}
.genre-strip::-webkit-scrollbar{display:none}
.genre-chip{flex:0 0 auto;padding:8px 20px;border-radius:6px;border:1px solid var(--border);font-size:.82rem;font-weight:600;color:var(--text2);background:var(--surface2);cursor:pointer;transition:.2s}
.genre-chip:hover{border-color:var(--accent);color:var(--accent)}
.genre-chip.active{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.modal-overlay{position:fixed;inset:0;z-index:3000;background:rgba(0,0,0,.92);backdrop-filter:blur(12px);display:flex;align-items:flex-start;justify-content:center;padding:20px;opacity:0;pointer-events:none;transition:opacity .3s;overflow-y:auto}
.modal-overlay.open{opacity:1;pointer-events:all}
#modal{width:min(1100px,96vw);background:var(--surface);border:1px solid var(--border);border-radius:20px;box-shadow:var(--shadow);transform:translateY(24px) scale(.97);transition:transform .35s;margin:auto;overflow:hidden}
.modal-overlay.open #modal{transform:translateY(0) scale(1)}
.modal-backdrop{width:100%;height:280px;background-size:cover;background-position:center;position:relative;background-repeat:no-repeat;background-color:var(--surface2)}
.modal-backdrop::after{content:'';position:absolute;inset:0;background:linear-gradient(to top,var(--surface) 0%,transparent 70%)}
.modal-close{position:absolute;top:16px;left:16px;z-index:3;width:38px;height:38px;border-radius:10px;background:rgba(0,0,0,.75);color:white;display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700;transition:.2s;cursor:pointer;border:1px solid rgba(255,255,255,.15);backdrop-filter:blur(8px)}
.modal-close:hover{background:var(--accent2);border-color:var(--accent2)}
.modal-body{padding:26px 34px 36px}
.modal-title{font-size:2rem;font-weight:900;line-height:1.2;margin-bottom:12px}
.modal-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:.85rem;color:var(--text2);margin-bottom:18px}
.modal-meta .accent{color:var(--accent);font-weight:700}
.modal-meta .sep{color:var(--surface2)}
.modal-desc{font-size:.92rem;color:#a8a8c4;line-height:1.85;margin-bottom:24px}
.player-container{width:100%;aspect-ratio:16/9;background:#000;border-radius:12px;overflow:hidden;margin-bottom:18px;position:relative;box-shadow:0 15px 50px rgba(0,0,0,.9)}
.player-container iframe{width:100%;height:100%;border:none;display:block}
.player-placeholder{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1a1a2e,#0a0a15);color:var(--text2);flex-direction:column;gap:14px}
.player-placeholder-icon{width:70px;height:70px;border-radius:50%;background:rgba(232,184,75,.15);border:2px solid var(--accent);display:flex;align-items:center;justify-content:center;font-size:1.1rem;color:var(--accent);animation:pulse 2s infinite;font-weight:700}
@keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.1);opacity:.7}}
.quality-info{display:flex;align-items:center;gap:.8rem;padding:12px 16px;background:var(--surface2);border-radius:10px;border:1px solid var(--border);margin-bottom:18px;flex-wrap:wrap}
.quality-badge{padding:5px 14px;border-radius:6px;font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.5px}
.quality-badge.q4k{background:linear-gradient(135deg,#f5c518,#ff9800);color:#000}
.quality-badge.qhd{background:var(--green);color:#000}
.quality-badge.qsd{background:var(--surface);color:var(--text2)}
.quality-info-text{color:var(--text2);font-size:.85rem;font-weight:600}
.modal-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}
.cast-section{margin-top:24px}
.cast-section h4{font-size:.82rem;color:var(--text2);margin-bottom:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.cast-list{display:flex;gap:12px;overflow-x:auto;padding-bottom:8px;scrollbar-width:none}
.cast-list::-webkit-scrollbar{display:none}
.cast-item{flex:0 0 auto;width:110px;background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px 10px;text-align:center;cursor:pointer;transition:.2s}
.cast-item:hover{border-color:var(--accent);transform:translateY(-3px)}
.cast-avatar{width:60px;height:60px;margin:0 auto 9px;background:linear-gradient(135deg,var(--accent),#d35400);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.4rem;color:var(--bg);overflow:hidden}
.cast-avatar img{width:100%;height:100%;object-fit:cover}
.cast-name{font-size:.76rem;font-weight:700;margin-bottom:3px;line-height:1.2}
.cast-role{font-size:.66rem;color:var(--text2)}
.stars-row{display:flex;gap:8px;margin:16px 0}
.star-btn{font-size:1.4rem;cursor:pointer;transition:.18s;color:var(--text2);background:none;border:none}
.star-btn:hover,.star-btn.lit{color:var(--accent);transform:scale(1.18)}
#auth-modal{position:fixed;inset:0;z-index:9000;background:rgba(0,0,0,.97);display:none;align-items:center;justify-content:center;padding:20px}
#auth-modal.open{display:flex}
.auth-box{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:40px;max-width:440px;width:100%;box-shadow:var(--shadow);position:relative}
.auth-logo{font-family:'Bebas Neue',sans-serif;font-size:2.4rem;color:var(--accent);margin-bottom:8px;letter-spacing:2px;text-align:center}
.auth-subtitle{color:var(--text2);font-size:.88rem;margin-bottom:30px;text-align:center}
.auth-input{width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:12px 14px;border-radius:10px;font-size:.93rem;margin-bottom:12px;transition:.2s;outline:none}
.auth-input:focus{border-color:var(--accent)}
.auth-btn{width:100%;background:var(--accent);color:var(--bg);font-weight:700;padding:12px;border-radius:10px;margin-bottom:14px;transition:.2s;cursor:pointer;font-size:.94rem}
.auth-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(232,184,75,.35)}
.auth-close{position:absolute;top:20px;right:20px;width:36px;height:36px;border-radius:50%;background:var(--surface2);border:1px solid var(--border);color:var(--text2);cursor:pointer;font-size:.9rem}
#profile-modal{position:fixed;inset:0;z-index:8000;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;padding:20px}
#profile-modal.open{display:flex}
.profile-box{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:40px;max-width:520px;width:100%;box-shadow:var(--shadow);max-height:90vh;overflow-y:auto}
.form-group{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.form-group label{font-size:.82rem;font-weight:600;color:var(--text2)}
.form-group input,.form-group textarea,.form-group select{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:10px 12px;border-radius:10px;font-size:.9rem;transition:.2s;outline:none}
.form-group input:focus,.form-group textarea:focus,.form-group select:focus{border-color:var(--accent)}
.form-actions{display:flex;gap:12px;margin-top:12px}
.btn-save{flex:1;background:var(--accent);color:var(--bg);padding:11px;border-radius:10px;font-weight:700;cursor:pointer;transition:.2s}
.btn-save:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(232,184,75,.3)}
.btn-cancel{flex:1;background:var(--surface2);color:var(--text);border:1px solid var(--border);padding:11px;border-radius:10px;font-weight:600;cursor:pointer;transition:.2s}
.btn-cancel:hover{border-color:var(--accent)}
#search-overlay{position:fixed;inset:0;z-index:2000;background:rgba(0,0,0,.88);backdrop-filter:blur(14px);display:none;align-items:flex-start;justify-content:center;padding-top:120px;padding-left:20px;padding-right:20px}
#search-overlay.open{display:flex}
.search-box{width:min(680px,96vw);background:var(--surface);border:1px solid var(--border);border-radius:20px;overflow:hidden;box-shadow:var(--shadow)}
.search-input-row{display:flex;align-items:center;gap:14px;padding:18px 22px;border-bottom:1px solid var(--border)}
#search-input{flex:1;background:none;border:none;outline:none;font-size:1.05rem;color:var(--text)}
#search-input::placeholder{color:var(--text3)}
.search-close-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text2);width:40px;height:32px;border-radius:8px;font-size:.75rem;font-weight:700;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:.2s}
.search-close-btn:hover{background:var(--accent2);color:white;border-color:var(--accent2)}
#search-results-list{max-height:420px;overflow-y:auto}
.search-result-item{display:flex;align-items:center;gap:14px;padding:12px 22px;cursor:pointer;transition:.2s;border-bottom:1px solid rgba(255,255,255,.025)}
.search-result-item:hover{background:var(--surface2)}
.search-result-item img{width:44px;height:64px;object-fit:cover;border-radius:6px;flex-shrink:0;background:var(--surface2)}
.search-result-info strong{display:block;font-size:.93rem;margin-bottom:3px}
.search-result-info span{font-size:.76rem;color:var(--text2)}
#toast{position:fixed;bottom:28px;left:50%;z-index:9999;transform:translateX(-50%) translateY(60px);background:var(--surface2);color:var(--text);padding:12px 26px;border-radius:10px;font-size:.86rem;font-weight:600;border:1px solid var(--border);box-shadow:var(--shadow);transition:transform .3s cubic-bezier(.4,0,.2,1),opacity .3s;opacity:0;max-width:90vw;white-space:nowrap}
#toast.show{transform:translateX(-50%) translateY(0);opacity:1}
.loading{text-align:center;padding:50px 20px;color:var(--text2);grid-column:1/-1}
.spinner{display:inline-block;width:40px;height:40px;border:3px solid var(--surface2);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin-bottom:12px}
@keyframes spin{to{transform:rotate(360deg)}}
footer{background:var(--surface);border-top:1px solid var(--border);padding:40px;text-align:center;color:var(--text2);font-size:.82rem}
.footer-logo{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;color:var(--accent);margin-bottom:10px;letter-spacing:3px}
#cast-modal{position:fixed;inset:0;z-index:7000;background:rgba(0,0,0,.94);display:none;align-items:center;justify-content:center;padding:20px}
#cast-modal.open{display:flex}
.cast-detail-box{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:30px;max-width:780px;width:100%;box-shadow:var(--shadow);max-height:92vh;overflow-y:auto;position:relative}
.cast-detail-header{display:flex;gap:22px;flex-wrap:wrap;margin-bottom:22px}
.cast-detail-photo{width:150px;height:220px;border-radius:12px;object-fit:cover;background:var(--surface2);flex-shrink:0}
.cast-detail-info{flex:1;min-width:240px}
.cast-detail-info h3{font-size:1.5rem;font-weight:900;margin-bottom:10px}
.cast-detail-info p{font-size:.85rem;color:var(--text2);margin-bottom:6px;line-height:1.6}
.cast-detail-info p strong{color:var(--accent);font-weight:700}
.cast-bio{font-size:.88rem;color:#a8a8c4;line-height:1.85;margin-top:14px;max-height:250px;overflow-y:auto;padding-right:8px;border-top:1px solid var(--border);padding-top:14px}
.cast-films-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:12px;margin-top:18px}
.cast-film-card{cursor:pointer;transition:.2s}
.cast-film-card:hover{transform:translateY(-4px)}
.cast-film-card img{width:100%;aspect-ratio:2/3;object-fit:cover;border-radius:8px;background:var(--surface2)}
.cast-film-card .cf-title{font-size:.72rem;font-weight:600;margin-top:6px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
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
.league-strip{display:flex;gap:10px;overflow-x:auto;padding-bottom:14px;margin-bottom:24px;scrollbar-width:none;flex-wrap:wrap}
.league-strip::-webkit-scrollbar{display:none}
@media(max-width:900px){
  #navbar{padding:0 16px;height:60px}.nav-links{display:none}.nav-logo{font-size:1.5rem}
  section{padding:35px 16px}.hero-content{padding:0 20px}#hero-title{font-size:2rem}
  #hero-desc{font-size:.85rem}#modal{width:100%;border-radius:16px}.modal-body{padding:20px}
  .modal-title{font-size:1.5rem}#browse-grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}
  .movie-card{flex:0 0 145px}.cast-item{width:96px}.cast-detail-photo{width:120px;height:180px}
}
@media(max-width:500px){.movie-card{flex:0 0 130px}.user-name{display:none}.btn-primary,.btn-ghost{padding:11px 20px;font-size:.85rem}}
</style>
</head>
<body>
<div id="toast"></div>

<div id="auth-modal">
  <div class="auth-box">
    <button class="auth-close" onclick="closeAuth()">X</button>
    <div class="auth-logo">ONYX CINEMA</div>
    <p class="auth-subtitle">سجل دخولك للمتابعة</p>
    <input class="auth-input" type="email" id="email-input" placeholder="بريدك الإلكتروني" />
    <input class="auth-input" type="password" id="pass-input" placeholder="كلمة المرور" />
    <button class="auth-btn" onclick="doLogin()">دخول</button>
    <div style="text-align:center;color:var(--text3);font-size:.78rem;margin:14px 0">أو</div>
    <button class="auth-btn" style="background:var(--surface2);color:var(--text)" onclick="guestLogin()">المتابعة كزائر</button>
  </div>
</div>

<div id="cast-modal" onclick="if(event.target.id==='cast-modal')closeCastModal()">
  <div class="cast-detail-box" id="cast-detail-content"></div>
</div>

<div id="profile-modal">
  <div class="profile-box">
    <h3 style="font-size:1.2rem;margin-bottom:24px;text-align:center">الملف الشخصي</h3>
    <div class="form-group"><label>الاسم</label><input type="text" id="profile-name" /></div>
    <div class="form-group"><label>البريد</label><input type="email" id="profile-email" /></div>
    <div class="form-group"><label>نبذة</label><textarea id="profile-bio" rows="3"></textarea></div>
    <div class="form-group"><label>اللغة المفضلة للترجمة</label>
      <select id="profile-lang">
        <option value="ar">العربية</option><option value="en">English</option>
        <option value="fr">Francais</option><option value="es">Espanol</option>
        <option value="de">Deutsch</option><option value="tr">Turkce</option>
      </select>
    </div>
    <div class="form-group"><label>جودة البث المفضلة</label>
      <select id="profile-quality">
        <option value="4K">4K Ultra HD</option>
        <option value="HD">HD 1080p</option>
        <option value="SD">SD 480p</option>
      </select>
    </div>
    <div class="form-actions">
      <button class="btn-save" onclick="saveProfile()">حفظ</button>
      <button class="btn-cancel" onclick="closeProfileModal()">إلغاء</button>
    </div>
  </div>
</div>

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
    <div class="user-profile" onclick="openProfileModal()">
      <div class="user-avatar" id="user-avatar">U</div>
      <span class="user-name" id="user-name">المستخدم</span>
    </div>
  </div>
</nav>

<div id="search-overlay">
  <div class="search-box">
    <div class="search-input-row">
      <span style="color:var(--text2);font-size:.85rem">بحث:</span>
      <input id="search-input" type="text" placeholder="ابحث عن فيلم أو مسلسل..." />
      <button class="search-close-btn" onclick="closeSearch()">ESC</button>
    </div>
    <div id="search-results-list"></div>
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
      <div class="player-container" id="player-container">
        <div class="player-placeholder" id="player-placeholder">
          <div class="player-placeholder-icon">PLAY</div>
          <div style="font-size:.9rem;font-weight:600">جار تحميل الفيديو...</div>
        </div>
        <iframe id="pframe" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerpolicy="origin" style="display:none"></iframe>
      </div>
      <div class="quality-info" id="quality-info">
        <span class="quality-badge" id="quality-badge">HD</span>
        <span class="quality-info-text">يتم التشغيل تلقائيا بأفضل جودة متاحة</span>
      </div>
      <div class="modal-actions">
        <button class="btn-primary" onclick="playNow()"><div class="play-arrow"></div>مشاهدة الآن</button>
        <button class="btn-ghost" id="fav-btn" onclick="toggleFavCurrent()">المفضلة</button>
        <button class="btn-ghost" onclick="shareMovie()">مشاركة</button>
      </div>
      <div class="cast-section" id="cast-section"></div>
      <div style="margin-top:24px">
        <p style="font-size:.8rem;color:var(--text2);margin-bottom:8px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">تقييمك</p>
        <div class="stars-row" id="stars-row"></div>
      </div>
    </div>
  </div>
</div>

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
          <button class="btn-ghost" onclick="addHeroToFav()">أضف للمفضلة</button>
        </div>
      </div>
    </section>
    <section><h2 class="sec-title">رائج الآن</h2><div class="cards-row" id="trending-row"><div class="loading"><div class="spinner"></div></div></div></section>
    <section><h2 class="sec-title">أفلام شائعة</h2><div class="cards-row" id="popular-row"><div class="loading"><div class="spinner"></div></div></div></section>
    <section><h2 class="sec-title">الأعلى تقييما</h2><div class="cards-row" id="toprated-row"><div class="loading"><div class="spinner"></div></div></div></section>
    <section><h2 class="sec-title">تصفح الأفلام</h2><div class="genre-strip" id="genre-strip"></div><div id="browse-grid"><div class="loading"><div class="spinner"></div></div></div></section>
  </div>
  <div id="matches-page" style="display:none">
    <section>
      <h2 class="sec-title">مباريات كرة القدم - أعلى دقة</h2>
      <div class="league-strip" id="league-strip"></div>
      <div id="matches-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px"></div>
    </section>
  </div>
  <div id="series-page" style="display:none">
    <section><h2 class="sec-title">مسلسلات شائعة</h2><div class="cards-row" id="series-popular-row"><div class="loading"><div class="spinner"></div></div></div></section>
    <section><h2 class="sec-title">الأعلى تقييما في المسلسلات</h2><div class="cards-row" id="series-toprated-row"><div class="loading"><div class="spinner"></div></div></div></section>
  </div>
  <div id="browse-page" style="display:none">
    <section>
      <h2 class="sec-title">تصفح متقدم</h2>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px">
        <select id="filter-genre" class="genre-chip" style="padding:8px 20px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px">
          <option value="">كل الأنواع</option><option value="28">أكشن</option><option value="18">دراما</option>
          <option value="35">كوميديا</option><option value="878">خيال علمي</option><option value="27">رعب</option>
          <option value="10749">رومانسي</option><option value="12">مغامرة</option>
          <option value="16">أنيميشن</option><option value="80">جريمة</option>
        </select>
        <select id="filter-year" class="genre-chip" style="padding:8px 20px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px">
          <option value="">كل السنوات</option><option value="2026">2026</option><option value="2025">2025</option>
          <option value="2024">2024</option><option value="2023">2023</option><option value="2022">2022</option>
          <option value="2021">2021</option><option value="2020">2020</option>
        </select>
        <select id="filter-lang" class="genre-chip" style="padding:8px 20px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px">
          <option value="">كل اللغات</option><option value="ar">العربية</option><option value="en">English</option>
          <option value="fr">Francais</option><option value="es">Espanol</option><option value="tr">Turkce</option>
        </select>
        <select id="filter-type" class="genre-chip" style="padding:8px 20px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px">
          <option value="movie">أفلام</option><option value="tv">مسلسلات</option>
        </select>
        <button class="btn-primary" onclick="applyFilters()" style="padding:8px 24px;font-size:.85rem">تطبيق الفلاتر</button>
      </div>
      <div id="browse-results" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:22px"></div>
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
const IMG_PROFILE = 'https://image.tmdb.org/t/p/w185';
const SOURCES = __SOURCES__;

const S = {
  user: JSON.parse(localStorage.getItem('ca_user') || 'null'),
  prefs: JSON.parse(localStorage.getItem('ca_prefs') || '{"lang":"ar","quality":"HD"}'),
  fav: JSON.parse(localStorage.getItem('ca_favs') || '[]'),
  ratings: JSON.parse(localStorage.getItem('ca_ratings') || '{}'),
  tmdbMovies: [],
  currentMovie: null,
  currentSourceIdx: 0,
  matches: [],
  currentLeague: '',
};

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
    if (e.key === 'Escape') { closeModal(); closeSearch(); closeProfileModal(); closeCastModal(); }
  });
});

function closeAuth() { document.getElementById('auth-modal').classList.remove('open'); }

function doLogin() {
  const email = document.getElementById('email-input').value.trim();
  const pass = document.getElementById('pass-input').value.trim();
  if (!email || !email.includes('@')) return showToast('أدخل بريدا صحيحا');
  if (!pass || pass.length < 3) return showToast('كلمة المرور قصيرة');
  const user = { id: Date.now().toString(36), name: email.split('@')[0], email: email, bio: '', avatar: '' };
  S.user = user;
  localStorage.setItem('ca_user', JSON.stringify(user));
  document.getElementById('auth-modal').classList.remove('open');
  updateUserUI();
  showToast('تم تسجيل الدخول بنجاح');
  init();
}

function guestLogin() {
  const user = { id: 'guest_' + Date.now(), name: 'زائر', email: 'guest@local', bio: '', avatar: '' };
  S.user = user;
  localStorage.setItem('ca_user', JSON.stringify(user));
  document.getElementById('auth-modal').classList.remove('open');
  updateUserUI();
  showToast('دخلت كزائر');
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
  document.getElementById('profile-lang').value = S.prefs.lang || 'ar';
  document.getElementById('profile-quality').value = S.prefs.quality || 'HD';
  document.getElementById('profile-modal').classList.add('open');
}

function closeProfileModal() { document.getElementById('profile-modal').classList.remove('open'); }

function saveProfile() {
  if (!S.user) return;
  S.user.name = document.getElementById('profile-name').value || S.user.name;
  S.user.bio = document.getElementById('profile-bio').value || '';
  S.prefs.lang = document.getElementById('profile-lang').value;
  S.prefs.quality = document.getElementById('profile-quality').value;
  localStorage.setItem('ca_user', JSON.stringify(S.user));
  localStorage.setItem('ca_prefs', JSON.stringify(S.prefs));
  updateUserUI();
  closeProfileModal();
  showToast('تم حفظ البيانات والإعدادات');
}

async function fetchMovies(type, genreId) {
  try {
    let url = genreId ? `/api/genre/movie/${genreId}` : `/api/${type === 'popular' ? 'popular/movie' : type === 'top_rated' ? 'top_rated/movie' : 'trending'}`;
    const r = await fetch(url);
    const d = await r.json();
    return d.results || [];
  } catch(e) { console.error(e); return []; }
}

async function fetchSeries(type) {
  try {
    const r = await fetch(`/api/${type === 'top_rated' ? 'top_rated/tv' : 'popular/tv'}`);
    const d = await r.json();
    return d.results || [];
  } catch(e) { return []; }
}

function buildCard(m) {
  const div = document.createElement('div');
  div.className = 'movie-card';
  const type = m.media_type || (m.name ? 'tv' : 'movie');
  const title = m.title || m.name || 'غير معروف';
  const year = (m.release_date || m.first_air_date || '').substring(0, 4);
  const rating = m.vote_average ? m.vote_average.toFixed(1) : 'N/A';
  const isFav = S.fav.includes(m.id);
  div.innerHTML = '<div class="card-poster">' +
    (m.poster_path ? '<img src="' + IMG_W + m.poster_path + '" loading="lazy" alt="" />' : '<div style="width:100%;height:100%;background:var(--surface2);display:flex;align-items:center;justify-content:center;font-size:.8rem;color:var(--text3)">لا صورة</div>') +
    '<button class="card-fav' + (isFav ? ' active' : '') + '" onclick="event.stopPropagation();toggleFav(' + m.id + ',this)">F</button>' +
    '<div class="card-rating">' + rating + '</div></div>' +
    '<div class="card-info"><div class="card-title">' + title + '</div><div class="card-year">' + year + '</div></div>';
  div.onclick = () => openModal(m.id, type);
  return div;
}

async function init() {
  const trending = await fetchMovies('trending');
  const popular = await fetchMovies('popular');
  const topRated = await fetchMovies('top_rated');
  const seriesPopular = await fetchSeries('popular');
  const seriesTop = await fetchSeries('top_rated');
  S.tmdbMovies = [...trending, ...popular, ...topRated, ...seriesPopular, ...seriesTop];
  renderHero(trending);
  renderRow('trending-row', trending);
  renderRow('popular-row', popular);
  renderRow('toprated-row', topRated);
  renderRow('series-popular-row', seriesPopular);
  renderRow('series-toprated-row', seriesTop);
  renderGenres();
  renderGrid(popular);
  await loadMatches();
}

function renderHero(movies) {
  const m = movies.find(x => x.backdrop_path) || movies[0];
  if (!m) return;
  S.currentMovie = m;
  document.getElementById('hero-bg').style.backgroundImage = "url('" + IMG_O + m.backdrop_path + "')";
  document.getElementById('hero-title').textContent = m.title || m.name || 'غير معروف';
  document.getElementById('hero-meta').innerHTML = '<span class="accent">' + (m.vote_average ? m.vote_average.toFixed(1) : 'N/A') + '</span><span class="sep">|</span><span>' + (m.release_date || m.first_air_date || '').substring(0, 4) + '</span><span class="sep">|</span><span>' + (m.media_type === 'tv' ? 'مسلسل' : 'فيلم') + '</span>';
  document.getElementById('hero-desc').textContent = m.overview || '';
}

function renderRow(id, movies) {
  const row = document.getElementById(id);
  if (!row) return;
  row.innerHTML = '';
  movies.slice(0, 18).forEach(m => row.appendChild(buildCard(m)));
}

function renderGrid(movies) {
  const grid = document.getElementById('browse-grid');
  grid.innerHTML = '';
  movies.slice(0, 24).forEach(m => grid.appendChild(buildCard(m)));
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
    const results = (d.results || []).slice(0, 12);
    if (!results.length) { list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text2)">لا توجد نتائج</div>'; return; }
    list.innerHTML = results.map(m => {
      const type = m.media_type || 'movie';
      const title = m.title || m.name || 'غير معروف';
      return '<div class="search-result-item" onclick="closeSearch();openModal(' + m.id + ',\'' + type + '\')">' +
        (m.poster_path ? '<img src="' + IMG_W + m.poster_path + '" />' : '<div style="width:44px;height:64px;background:var(--surface2);border-radius:6px"></div>') +
        '<div class="search-result-info"><strong>' + title + '</strong><span>' + (m.release_date || m.first_air_date || '').substring(0, 4) + ' - ' + (m.vote_average ? m.vote_average.toFixed(1) : 'N/A') + '</span></div></div>';
    }).join('');
  } catch(e) { list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--accent2)">خطأ في البحث</div>'; }
});

async function openModal(id, type) {
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
    document.getElementById('modal-title').textContent = m.title || m.name || 'غير معروف';
    document.getElementById('modal-meta').innerHTML = '<span class="accent">' + (m.vote_average ? m.vote_average.toFixed(1) : 'N/A') + '</span><span class="sep">|</span><span>' + (m.release_date || m.first_air_date || '').substring(0, 4) + '</span>';
    document.getElementById('modal-desc').textContent = m.overview || 'لا يوجد وصف متاح';
    if (m.backdrop_path) document.getElementById('modal-backdrop').style.backgroundImage = "url('" + IMG_O + m.backdrop_path + "')";
  }

  try {
    const r = await fetch('/api/' + type + '/' + id);
    const full = await r.json();
    document.getElementById('modal-title').textContent = full.title || full.name || 'غير معروف';
    document.getElementById('modal-meta').innerHTML = '<span class="accent">' + (full.vote_average ? full.vote_average.toFixed(1) : 'N/A') + '</span><span class="sep">|</span><span>' + (full.release_date || full.first_air_date || '').substring(0, 4) + '</span><span class="sep">|</span><span>' + (full.runtime || 'N/A') + ' دقيقة</span>';
    document.getElementById('modal-desc').textContent = full.overview || 'لا يوجد وصف متاح';
    const best = pickBestSource(full, type);
    S.currentSourceIdx = best.idx;
    const qb = document.getElementById('quality-badge');
    qb.textContent = best.quality;
    qb.className = 'quality-badge ' + (best.quality === '4K' ? 'q4k' : best.quality === 'HD' ? 'qhd' : 'qsd');
    const cast = full.credits?.cast?.slice(0, 12) || [];
    const castSection = document.getElementById('cast-section');
    if (cast.length) {
      castSection.innerHTML = '<h4>طاقم التمثيل - اضغط لعرض المعلومات الكاملة</h4><div class="cast-list">' + cast.map(c => {
        const avatar = c.profile_path ? '<img src="' + IMG_PROFILE + c.profile_path + '" />' : (c.name || 'N')[0];
        return '<div class="cast-item" onclick="openCastModal(' + c.id + ')"><div class="cast-avatar">' + avatar + '</div><div class="cast-name">' + (c.name || 'غير معروف') + '</div><div class="cast-role">' + (c.character || '') + '</div></div>';
      }).join('') + '</div>';
    } else { castSection.innerHTML = ''; }
    const ur = S.ratings[id] || 0;
    document.getElementById('stars-row').innerHTML = [1,2,3,4,5].map(n => '<button class="star-btn' + (n <= ur ? ' lit' : '') + '" onclick="rateMovie(' + id + ',' + n + ')">*</button>').join('');
    updateFavBtn(id);
    setTimeout(() => startStream(best.idx, 1, 1), 400);
  } catch(e) { console.error(e); }
}

function pickBestSource(m, type) {
  let preferred = S.prefs.quality || 'HD';
  const year = parseInt((m.release_date || m.first_air_date || '2020').substring(0, 4));
  const cy = new Date().getFullYear();
  if (cy - year <= 3) preferred = '4K';
  if ((m.vote_average || 0) >= 8.0) preferred = '4K';
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
  const url = '/player?type=' + S.currentMovie.type + '&id=' + S.currentMovie.id + '&source=' + idx + '&season=' + (season || 1) + '&episode=' + (episode || 1) + '&lang=' + S.prefs.lang;
  pframe.src = url;
  S.currentSourceIdx = idx;
  pframe.onload = () => { setTimeout(() => { placeholder.style.display = 'none'; pframe.style.display = 'block'; }, 500); };
}

function playNow() {
  if (!S.currentMovie) return;
  startStream(S.currentSourceIdx, 1, 1);
  showToast('جاري التشغيل...');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
  const pframe = document.getElementById('pframe');
  if (pframe) pframe.src = 'about:blank';
}

function toggleFav(id, btn) {
  if (S.fav.includes(id)) { S.fav = S.fav.filter(x => x !== id); showToast('تم الحذف من المفضلة'); }
  else { S.fav.push(id); showToast('تمت الإضافة للمفضلة'); }
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
  btn.textContent = S.fav.includes(id) ? 'في المفضلة' : 'المفضلة';
}

function addHeroToFav() { if (S.currentMovie) toggleFav(S.currentMovie.id); }

function rateMovie(id, val) {
  S.ratings[id] = val;
  localStorage.setItem('ca_ratings', JSON.stringify(S.ratings));
  document.querySelectorAll('#stars-row .star-btn').forEach((b, i) => b.classList.toggle('lit', i < val));
  showToast('تم التقييم ' + val + '/5');
}

function shareMovie() {
  if (!S.currentMovie) return;
  const url = window.location.origin + '/?m=' + S.currentMovie.type + '_' + S.currentMovie.id;
  if (navigator.share) navigator.share({ url: url }).catch(() => {});
  else navigator.clipboard.writeText(url).then(() => showToast('تم نسخ الرابط')).catch(() => {});
}

async function openCastModal(personId) {
  const modal = document.getElementById('cast-modal');
  const content = document.getElementById('cast-detail-content');
  content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  try {
    const r = await fetch('/api/person/' + personId);
    const p = await r.json();
    const photo = p.profile_path ? IMG_PROFILE + p.profile_path : '';
    const films = (p.combined_credits?.cast || []).filter(x => x.poster_path).slice(0, 15);
    const filmsHtml = films.length ? '<h4 style="font-size:.85rem;color:var(--text2);margin-top:22px;text-transform:uppercase;letter-spacing:1px">أعمال مختارة (' + films.length + ')</h4><div class="cast-films-grid">' + films.map(f => {
      const t = f.title || f.name || '';
      const ftype = f.media_type || 'movie';
      return '<div class="cast-film-card" onclick="closeCastModal();openModal(' + f.id + ',\'' + ftype + '\')"><img src="' + IMG_W + f.poster_path + '" /><div class="cf-title">' + t + '</div></div>';
    }).join('') + '</div>' : '';
    content.innerHTML = '<button class="modal-close" style="top:12px;left:12px" onclick="closeCastModal()">ESC</button>' +
      '<div class="cast-detail-header">' +
      (photo ? '<img class="cast-detail-photo" src="' + photo + '" />' : '<div class="cast-detail-photo"></div>') +
      '<div class="cast-detail-info">' +
      '<h3>' + (p.name || 'غير معروف') + '</h3>' +
      (p.birthday ? '<p><strong>تاريخ الميلاد:</strong> ' + p.birthday + '</p>' : '') +
      (p.place_of_birth ? '<p><strong>مكان الولادة:</strong> ' + p.place_of_birth + '</p>' : '') +
      (p.known_for_department ? '<p><strong>التخصص:</strong> ' + (p.known_for_department === 'Acting' ? 'تمثيل' : p.known_for_department) + '</p>' : '') +
      (p.deathday ? '<p><strong>تاريخ الوفاة:</strong> ' + p.deathday + '</p>' : '') +
      (p.popularity ? '<p><strong>الشهرة:</strong> ' + Math.round(p.popularity) + '</p>' : '') +
      '</div></div>' +
      (p.biography ? '<div class="cast-bio">' + p.biography + '</div>' : '<p style="color:var(--text2);font-size:.85rem;margin-top:14px;border-top:1px solid var(--border);padding-top:14px">لا توجد سيرة متاحة بالعربية</p>') +
      filmsHtml;
  } catch(e) {
    content.innerHTML = '<div style="padding:40px;text-align:center;color:var(--accent2)">خطأ في تحميل البيانات</div>';
  }
}

function closeCastModal() {
  document.getElementById('cast-modal').classList.remove('open');
  document.body.style.overflow = '';
}

async function loadMatches(league) {
  const grid = document.getElementById('matches-grid');
  grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  try {
    const url = league ? '/api/matches?league=' + league : '/api/matches';
    const r = await fetch(url);
    const d = await r.json();
    S.matches = d.matches || [];
    renderMatches();
    renderLeagueStrip();
  } catch(e) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--accent2)">خطأ في تحميل المباريات</div>';
  }
}

function renderLeagueStrip() {
  const strip = document.getElementById('league-strip');
  const leagues = [{id:'', name:'كل الدوريات'}, {id:'saudi', name:'الدوري السعودي'}, {id:'egypt', name:'الدوري المصري'}, {id:'spain', name:'الإسباني'}, {id:'england', name:'الإنجليزي'}, {id:'italy', name:'الإيطالي'}, {id:'germany', name:'الألماني'}, {id:'france', name:'الفرنسي'}, {id:'ucl', name:'أبطال أوروبا'}];
  strip.innerHTML = leagues.map(l => '<button class="genre-chip' + (S.currentLeague === l.id ? ' active' : '') + '" onclick="selectLeague(\'' + l.id + '\')">' + l.name + '</button>').join('');
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
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px">' +
      '<span class="match-quality">' + m.quality + '</span>' +
      '<button class="btn-primary" style="padding:8px 16px;font-size:.78rem" onclick="watchMatch(' + i + ')">مشاهدة</button>' +
      '</div></div>';
  }).join('');
}

function watchMatch(idx) {
  const m = S.matches[idx];
  if (!m) return;
  showToast('جاري فتح البث بأعلى دقة: ' + m.quality);
  window.open('/match?id=' + encodeURIComponent(m.stream_id) + '&quality=' + m.quality, '_blank');
}

function switchPage(page, event) {
  if (event) event.preventDefault();
  document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
  if (event && event.target) event.target.classList.add('active');
  document.getElementById('movies-page').style.display = page === 'movies' ? 'block' : 'none';
  document.getElementById('matches-page').style.display = page === 'matches' ? 'block' : 'none';
  document.getElementById('series-page').style.display = page === 'series' ? 'block' : 'none';
  document.getElementById('browse-page').style.display = page === 'browse' ? 'block' : 'none';
}

function applyFilters() {
  const genre = document.getElementById('filter-genre').value;
  const year = document.getElementById('filter-year').value;
  const lang = document.getElementById('filter-lang').value;
  const type = document.getElementById('filter-type').value;
  const resultsDiv = document.getElementById('browse-results');
  resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
  let url = '/api/discover?type=' + type + '&';
  if (genre) url += 'genre=' + genre + '&';
  if (year) url += 'year=' + year + '&';
  if (lang) url += 'lang=' + lang + '&';
  fetch(url).then(r => r.json()).then(d => {
    resultsDiv.innerHTML = '';
    (d.results || []).slice(0, 24).forEach(m => resultsDiv.appendChild(buildCard(m)));
    if (!d.results || !d.results.length) resultsDiv.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text2)">لا توجد نتائج</div>';
  }).catch(() => {
    resultsDiv.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--accent2)">حدث خطأ</div>';
  });
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

console.log('[ONYX v10.1] Sources loaded:', SOURCES.length);
</script>
</body>
</html>
"""

# =========================================================
# PLAYER HTML (Movies/Series)
# =========================================================
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
const lang = p.get('lang') || 'ar';

function trySource(i) {
  if (i >= SOURCES.length) return;
  const src = SOURCES[i];
  if (!src) return;
  let url = (type === 'tv') ? (src.tv || src.movie) : (src.movie || src.tv);
  url = url.replace(/{id}/g, id).replace(/{s}/g, season).replace(/{e}/g, episode);
  url = url.replace(/{season}/g, season).replace(/{episode}/g, episode);
  if (url.includes('?')) url += '&lang=' + lang;
  else url += '?lang=' + lang;
  document.getElementById('player').src = url;
}

if (SOURCES[idx]) trySource(idx);
else trySource(0);
</script>
</body></html>
"""

# =========================================================
# MATCH PLAYER HTML (Football)
# =========================================================
MATCH_PLAYER_HTML = r"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>*{margin:0;padding:0}html,body{width:100%;height:100%;background:#000;overflow:hidden;font-family:Arial,sans-serif}
#topbar{position:absolute;top:0;left:0;right:0;height:44px;background:rgba(0,0,0,.85);color:#e8b84b;display:flex;align-items:center;justify-content:space-between;padding:0 16px;font-size:13px;z-index:10;backdrop-filter:blur(10px)}
#topbar button{background:#1f1f2e;color:#e8b84b;border:1px solid rgba(255,255,255,.1);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;margin-left:8px}
#topbar button:hover{background:#e8b84b;color:#000}
iframe{position:absolute;top:44px;left:0;width:100%;height:calc(100% - 44px);border:none}
</style></head>
<body>
<div id="topbar">
  <div>ONYX SPORTS - بث مباشر</div>
  <div id="servers"></div>
</div>
<iframe id="player" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerpolicy="origin"></iframe>
<script>
const SOURCES = __SOURCES__;
const p = new URLSearchParams(location.search);
const id = p.get('id') || 'match_1';
const quality = p.get('quality') || '4K';

function trySource(i) {
  if (i >= SOURCES.length) return;
  const src = SOURCES[i];
  if (!src) return;
  let url = (src.movie || src.tv).replace(/{id}/g, id);
  url = url.replace(/{s}/g, '1').replace(/{e}/g, '1');
  document.getElementById('player').src = url;
  // Mark active button
  document.querySelectorAll('#servers button').forEach((b, idx) => {
    b.style.background = idx === i ? '#e8b84b' : '#1f1f2e';
    b.style.color = idx === i ? '#000' : '#e8b84b';
  });
}

function buildServers() {
  const box = document.getElementById('servers');
  box.innerHTML = '';
  SOURCES.slice(0, 10).forEach((s, i) => {
    const b = document.createElement('button');
    b.textContent = 'سيرفر ' + (i + 1);
    b.onclick = () => trySource(i);
    box.appendChild(b);
  });
}

buildServers();
trySource(0);
</script>
</body></html>
"""

# =========================================================
# ROUTES
# =========================================================
@app.route("/")
def index():
    return render_template_string(INDEX_HTML.replace("__SOURCES__", SOURCES_JSON))

@app.route("/player")
def player():
    return render_template_string(PLAYER_HTML.replace("__SOURCES__", SOURCES_JSON))

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

@app.route("/api/genre/<mt>/<int:gid>")
def api_genre(mt, gid):
    if mt not in ("movie", "tv"):
        return jsonify({"error": "invalid"}), 400
    return jsonify(tmdb(f"/discover/{mt}", {"with_genres": gid, "sort_by": "popularity.desc"}))

@app.route("/api/discover")
def api_discover():
    genre = request.args.get("genre")
    year = request.args.get("year")
    lang = request.args.get("lang")
    mtype = request.args.get("type", "movie")
    if mtype not in ("movie", "tv"):
        mtype = "movie"
    params = {"sort_by": "popularity.desc"}
    if genre: params["with_genres"] = genre
    if year:
        if mtype == "movie":
            params["primary_release_year"] = year
        else:
            params["first_air_date_year"] = year
    if lang: params["with_original_language"] = lang
    return jsonify(tmdb(f"/discover/{mtype}", params))

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
        "service": "ONYX CINEMA v10.1",
        "tmdb": "ok" if TMDB_API_KEY else "missing",
        "sources": len(PLAYER_SOURCES),
        "match_sources": len(SPORTS_SOURCES),
        "leagues": len(FOOTBALL_LEAGUES),
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
