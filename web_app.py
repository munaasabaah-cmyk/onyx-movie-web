# -*- coding: utf-8 -*-
"""ONYX CINEMA v7.0 — Templates Mode"""

from flask import Flask, jsonify, request, render_template
import os
import time
import json
import urllib.request
import urllib.parse
from collections import defaultdict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__, template_folder="templates", static_folder="static")

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"

# Security
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


# PLAYER SOURCES
PLAYER_SOURCES = [
    {"name": "VidLink 4K", "q": "4K", "movie": "https://vidlink.pro/movie/{id}", "tv": "https://vidlink.pro/tv/{id}/{s}/{e}"},
    {"name": "Videasy 4K", "q": "4K", "movie": "https://player.videasy.net/movie/{id}", "tv": "https://player.videasy.net/tv/{id}/{s}/{e}"},
    {"name": "AutoEmbed HD", "q": "HD", "movie": "https://player.autoembed.cc/embed/movie/{id}", "tv": "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}"},
    {"name": "SmashyStream HD", "q": "HD", "movie": "https://player.smashy.stream/movie/{id}", "tv": "https://player.smashy.stream/tv/{id}?s={s}&e={e}"},
    {"name": "VidSrc XYZ", "q": "HD", "movie": "https://vidsrc.xyz/embed/movie?tmdb={id}", "tv": "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}"},
    {"name": "2Embed.to", "q": "HD", "movie": "https://www.2embed.to/embed/tmdb/movie?id={id}", "tv": "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"},
    {"name": "Embed.su", "q": "HD", "movie": "https://embed.su/embed/movie/{id}", "tv": "https://embed.su/embed/tv/{id}/{s}/{e}"},
    {"name": "VidSrc.to", "q": "SD", "movie": "https://vidsrc.to/embed/movie/{id}", "tv": "https://vidsrc.to/embed/tv/{id}/{s}/{e}"},
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
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/7.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


# ══════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html", sources_json=SOURCES_JSON)


@app.route("/player")
def player():
    return render_template("player.html", sources_json=SOURCES_JSON)


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
    return jsonify({"status": "ok", "service": "ONYX v7.0", "sources": len(PLAYER_SOURCES)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
