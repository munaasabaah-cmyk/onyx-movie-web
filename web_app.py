# -*- coding: utf-8 -*-
"""
ONYX CINEMA v3.0 — Backend
Flask + TMDB + 20 Multi-Audio Sources + Security
"""

from flask import Flask, jsonify, request
import os
import time
import json
import hashlib
import secrets
import urllib.request
import urllib.parse
from collections import defaultdict
import re

app = Flask(__name__)

# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
SECRET_SALT = os.getenv("SECRET_SALT", "onyx_cinema_2025_secret_default")

RATE_LIMIT = 120
RATE_WINDOW = 60
BAN_THRESHOLD = 500
BAN_DURATION = 1800

# ══════════════════════════════════════════════════════════
# SECURITY
# ══════════════════════════════════════════════════════════

_rate_buckets = defaultdict(list)
_banned_ips = {}
_request_log = defaultdict(int)


def get_client_ip():
    if request.headers.get("CF-Connecting-IP"):
        return request.headers.get("CF-Connecting-IP")
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    if request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    return request.remote_addr or "unknown"


def is_banned(ip):
    if ip in _banned_ips:
        if time.time() < _banned_ips[ip]:
            return True
        del _banned_ips[ip]
    return False


def check_rate_limit(ip):
    now = time.time()
    _rate_buckets[ip] = [t for t in _rate_buckets[ip] if now - t < RATE_WINDOW]
    _rate_buckets[ip].append(now)
    _request_log[ip] += 1
    if _request_log[ip] > BAN_THRESHOLD:
        _banned_ips[ip] = now + BAN_DURATION
        return True
    return len(_rate_buckets[ip]) > RATE_LIMIT


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt + SECRET_SALT).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password, stored):
    try:
        salt, hashed = stored.split("$", 1)
        check = hashlib.sha256((password + salt + SECRET_SALT).encode()).hexdigest()
        return secrets.compare_digest(check, hashed)
    except Exception:
        return False


def sanitize(text, max_len=500):
    if not isinstance(text, str):
        return ""
    text = text[:max_len]
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;").replace("'", "&#x27;")
    return text.strip()


@app.before_request
def gatekeeper():
    ip = get_client_ip()
    if is_banned(ip):
        return jsonify({"error": "IP banned"}), 429
    if check_rate_limit(ip):
        _banned_ips[ip] = time.time() + BAN_DURATION
        return jsonify({"error": "Rate limit exceeded"}), 429
    ua = request.headers.get("User-Agent", "")
    if not ua:
        return jsonify({"error": "Missing User-Agent"}), 400


@app.after_request
def apply_security(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' https: data:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://accounts.google.com https://apis.google.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "frame-src 'self' https: data:; "
        "connect-src 'self' https:; "
        "media-src 'self' https: data: blob:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response


# ══════════════════════════════════════════════════════════
# 20 PLAYER SOURCES
# ══════════════════════════════════════════════════════════

PLAYER_SOURCES = [
    {"name": "VidLink 4K Multi", "quality": "4K", "ads": "none",
     "langs": "ar,en,ru,es,fr,de,it,pt,tr",
     "movie": "https://vidlink.pro/movie/{id}?primaryColor=e50914&autoplay=true&multiLang=true",
     "tv": "https://vidlink.pro/tv/{id}/{season}/{episode}?primaryColor=e50914&autoplay=true&multiLang=true"},

    {"name": "Videasy 4K", "quality": "4K", "ads": "none",
     "langs": "ar,en,ru,es,fr,de,it,pt,tr,ko,ja",
     "movie": "https://player.videasy.net/movie/{id}",
     "tv": "https://player.videasy.net/tv/{id}/{season}/{episode}"},

    {"name": "AutoEmbed", "quality": "HD", "ads": "none",
     "langs": "ar,en,ru,es",
     "movie": "https://player.autoembed.cc/embed/movie/{id}",
     "tv": "https://player.autoembed.cc/embed/tv/{id}/{season}/{episode}"},

    {"name": "SmashyStream", "quality": "HD", "ads": "none",
     "langs": "ar,en,ru,es,fr,de",
     "movie": "https://player.smashy.stream/movie/{id}",
     "tv": "https://player.smashy.stream/tv/{id}?s={season}&e={episode}"},

    {"name": "VidPlus", "quality": "HD", "ads": "low",
     "langs": "ar,en,ru,es,fr",
     "movie": "https://vidplus.to/embed/movie/{id}",
     "tv": "https://vidplus.to/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc XYZ", "quality": "HD", "ads": "low",
     "langs": "ar,en",
     "movie": "https://vidsrc.xyz/embed/movie?tmdb={id}",
     "tv": "https://vidsrc.xyz/embed/tv?tmdb={id}&season={season}&episode={episode}"},

    {"name": "2Embed.to", "quality": "HD", "ads": "low",
     "langs": "ar,en,ru",
     "movie": "https://www.2embed.to/embed/tmdb/movie?id={id}",
     "tv": "https://www.2embed.to/embed/tmdb/tv?id={id}&s={season}&e={episode}"},

    {"name": "Embed.su", "quality": "HD", "ads": "low",
     "langs": "ar,en,ru",
     "movie": "https://embed.su/embed/movie/{id}",
     "tv": "https://embed.su/embed/tv/{id}/{season}/{episode}"},

    {"name": "MoviesAPI", "quality": "HD", "ads": "low",
     "langs": "ar,en",
     "movie": "https://moviesapi.club/movie/{id}",
     "tv": "https://moviesapi.club/tv/{id}-{season}-{episode}"},

    {"name": "VidSrc IO", "quality": "HD", "ads": "low",
     "langs": "ar,en",
     "movie": "https://vidsrc.io/embed/movie/{id}",
     "tv": "https://vidsrc.io/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc CC", "quality": "SD", "ads": "medium",
     "langs": "ar,en",
     "movie": "https://vidsrc.cc/v2/embed/movie/{id}",
     "tv": "https://vidsrc.cc/v2/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc WTF", "quality": "SD", "ads": "medium",
     "langs": "ar,en",
     "movie": "https://vidsrc.wtf/api/1/movie/?id={id}",
     "tv": "https://vidsrc.wtf/api/1/tv/?id={id}&s={season}&e={episode}"},

    {"name": "VidSrc DEV", "quality": "SD", "ads": "medium",
     "langs": "ar,en",
     "movie": "https://vidsrc.dev/embed/movie/{id}",
     "tv": "https://vidsrc.dev/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc.to", "quality": "SD", "ads": "medium",
     "langs": "ar,en",
     "movie": "https://vidsrc.to/embed/movie/{id}",
     "tv": "https://vidsrc.to/embed/tv/{id}/{season}/{episode}"},

    {"name": "VidSrc.me", "quality": "SD", "ads": "medium",
     "langs": "ar,en",
     "movie": "https://vidsrc.me/embed/movie?tmdb={id}",
     "tv": "https://vidsrc.me/embed/tv?tmdb={id}&season={season}&episode={episode}"},

    {"name": "SuperEmbed", "quality": "SD", "ads": "high",
     "langs": "ar,en",
     "movie": "https://multiembed.mov/?video_id={id}&tmdb=1",
     "tv": "https://multiembed.mov/?video_id={id}&tmdb=1&s={season}&e={episode}"},

    {"name": "MultiEmbed", "quality": "SD", "ads": "high",
     "langs": "ar,en",
     "movie": "https://multiembed.mov/directstream.php?video_id={id}&tmdb=1",
     "tv": "https://multiembed.mov/directstream.php?video_id={id}&tmdb=1&s={season}&e={episode}"},

    {"name": "2Embed.cc", "quality": "SD", "ads": "high",
     "langs": "ar,en",
     "movie": "https://www.2embed.cc/embed/{id}",
     "tv": "https://www.2embed.cc/embedtv/{id}&s={season}&e={episode}"},

    {"name": "VidSrc.lol", "quality": "SD", "ads": "high",
     "langs": "ar,en",
     "movie": "https://vidsrc.lol/embed/movie/{id}",
     "tv": "https://vidsrc.lol/embed/tv/{id}/{season}/{episode}"},

    {"name": "Player4u", "quality": "SD", "ads": "high",
     "langs": "ar,en",
     "movie": "https://player4u.xyz/embed/movie/{id}",
     "tv": "https://player4u.xyz/embed/tv/{id}/{season}/{episode}"},
]

SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)


# ══════════════════════════════════════════════════════════
# TMDB HELPER
# ══════════════════════════════════════════════════════════

def tmdb_get(endpoint, params=None):
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY missing", "results": []}
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    lang = request.args.get("lang", "ar")
    params["language"] = "en-US" if lang == "en" else "ar"
    url = f"{TMDB_BASE}{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX-CINEMA/3.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


# ══════════════════════════════════════════════════════════
# HTML TEMPLATES (Placeholder - سنملأها في الأجزاء القادمة)
# ══════════════════════════════════════════════════════════

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>ONYX CINEMA - Setup</title>
<style>
body { background: #141414; color: #fff; font-family: Arial, sans-serif; padding: 40px; text-align: center; }
h1 { color: #e50914; font-size: 3rem; }
p { color: #aaa; }
</style>
</head>
<body>
<h1>ONYX CINEMA</h1>
<p>الجزء 1 مكتمل - ارفع web_app.py ثم انتظر الأجزاء القادمة</p>
<p>Sources: __SOURCE_COUNT__</p>
<p>TMDB: __TMDB_STATUS__</p>
</body>
</html>
"""

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
<iframe id="player" src="" allowfullscreen allow="autoplay; encrypted-media; fullscreen"></iframe>
<script>
const SOURCES = __SOURCES__;
const params = new URLSearchParams(window.location.search);
const type = params.get('type') || 'movie';
const id = params.get('id');
const sourceIdx = parseInt(params.get('source') || '0');
const season = params.get('season') || '1';
const episode = params.get('episode') || '1';

const src = SOURCES[sourceIdx] || SOURCES[0];
if (src) {
  let url = src[type] || src.movie;
  url = url.replace('{id}', id).replace('{season}', season).replace('{episode}', episode);
  document.getElementById('player').src = url;
}
</script>
</body>
</html>
"""


# ══════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════

@app.route("/")
def index():
    html = INDEX_HTML.replace("__SOURCE_COUNT__", str(len(PLAYER_SOURCES)))
    html = html.replace("__TMDB_STATUS__", "OK" if TMDB_API_KEY else "MISSING")
    return html


@app.route("/player")
def player():
    return PLAYER_HTML.replace("__SOURCES__", SOURCES_JSON)


@app.route("/api/trending")
def api_trending():
    return jsonify(tmdb_get("/trending/all/week"))


@app.route("/api/popular/<media_type>")
def api_popular(media_type):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400
    return jsonify(tmdb_get(f"/{media_type}/popular"))


@app.route("/api/top_rated/<media_type>")
def api_top_rated(media_type):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400
    return jsonify(tmdb_get(f"/{media_type}/top_rated"))


@app.route("/api/upcoming")
def api_upcoming():
    return jsonify(tmdb_get("/movie/upcoming"))


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()[:100]
    if not q:
        return jsonify({"results": []})
    return jsonify(tmdb_get("/search/multi", {"query": q}))


@app.route("/api/movie/<int:movie_id>")
def api_movie(movie_id):
    return jsonify(tmdb_get(f"/movie/{movie_id}", {"append_to_response": "credits,videos,similar,recommendations"}))


@app.route("/api/tv/<int:tv_id>")
def api_tv(tv_id):
    return jsonify(tmdb_get(f"/tv/{tv_id}", {"append_to_response": "credits,videos,similar,recommendations"}))


@app.route("/api/tv/<int:tv_id>/season/<int:season_num>")
def api_tv_season(tv_id, season_num):
    if season_num < 0 or season_num > 100:
        return jsonify({"error": "invalid season"}), 400
    return jsonify(tmdb_get(f"/tv/{tv_id}/season/{season_num}"))


@app.route("/api/collection/<int:col_id>")
def api_collection(col_id):
    return jsonify(tmdb_get(f"/collection/{col_id}"))


@app.route("/api/genre/<media_type>/<int:genre_id>")
def api_genre(media_type, genre_id):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400
    return jsonify(tmdb_get(f"/discover/{media_type}", {
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
    }))


@app.route("/api/auth/hash", methods=["POST"])
def api_auth_hash():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    if not isinstance(password, str) or len(password) < 6:
        return jsonify({"error": "password too short"}), 400
    if len(password) > 128:
        return jsonify({"error": "password too long"}), 400
    return jsonify({"hash": hash_password(password)})


@app.route("/health")
def health():
    ip = get_client_ip()
    return jsonify({
        "status": "ok",
        "service": "ONYX CINEMA v3.0",
        "tmdb": "configured" if TMDB_API_KEY else "missing",
        "sources": len(PLAYER_SOURCES),
        "your_ip": ip,
        "ban_count": len(_banned_ips),
        "time": int(time.time()),
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "internal server error"}), 500


@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "rate limited"}), 429


# ══════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
