# -*- coding: utf-8 -*-
"""
ONYX CINEMA v16.0 - Flask + Discord Bot + 4 Premium 4K Sources
"""

from flask import Flask, jsonify, request, render_template
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
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    r.headers.pop("X-Frame-Options", None)
    r.headers.pop("Content-Security-Policy", None)
    return r


# =========================================================
# SOURCES - 4 PREMIUM 4K ONLY
# =========================================================
REAL_SOURCES = [
    (
        "VidLink 4K",
        "https://vidlink.pro/movie/{id}?quality=4k&sub=ar",
        "https://vidlink.pro/tv/{id}/{s}/{e}?quality=4k&sub=ar",
    ),
    (
        "Videasy 4K",
        "https://player.videasy.net/movie/{id}?quality=4k&sub=ar",
        "https://player.videasy.net/tv/{id}/{s}/{e}?quality=4k&sub=ar",
    ),
    (
        "VidSrc 4K",
        "https://vidsrc.xyz/embed/movie?tmdb={id}&quality=4k&ds_lang=ar",
        "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}&quality=4k&ds_lang=ar",
    ),
    (
        "VidSrc ME 4K",
        "https://vidsrc.me/embed/movie?tmdb={id}&quality=4k&ds_lang=ar",
        "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}&quality=4k&ds_lang=ar",
    ),
]

QUALITY_VARIANTS = ["4K"]


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
    {"name": "YallaShoot 4K", "q": "4K", "movie": "https://yallashoot.com/embed/{id}?quality=4k", "tv": "https://yallashoot.com/embed/{id}?quality=4k"},
    {"name": "KoraLive 4K", "q": "4K", "movie": "https://koralive.com/embed/{id}?quality=4k", "tv": "https://koralive.com/embed/{id}?quality=4k"},
    {"name": "BeinSport 4K", "q": "4K", "movie": "https://beinsport.com/embed/{id}?quality=4k", "tv": "https://beinsport.com/embed/{id}?quality=4k"},
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
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/16.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


# =========================================================
# FOOTBALL
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
    base_matches = [
        {"league": "الدوري السعودي", "league_id": "saudi", "team1": "النصر", "team2": "الهلال",
         "s1": "2", "s2": "1", "status": "live", "ch": "SSC", "date": today, "time": "21:00",
         "quality": "4K", "stream_id": "saudi_1"},
        {"league": "الدوري المصري", "league_id": "egypt", "team1": "الأهلي", "team2": "الزمالك",
         "s1": "-", "s2": "-", "status": "upcoming", "ch": "ON TV", "date": today, "time": "19:00",
         "quality": "4K", "stream_id": "egypt_1"},
        {"league": "الدوري الإسباني", "league_id": "spain", "team1": "ريال مدريد", "team2": "برشلونة",
         "s1": "3", "s2": "2", "status": "finished", "ch": "beIN", "date": today, "time": "22:00",
         "quality": "4K", "stream_id": "spain_1"},
        {"league": "دوري أبطال أوروبا", "league_id": "ucl", "team1": "مان سيتي", "team2": "ريال مدريد",
         "s1": "1", "s2": "1", "status": "live", "ch": "beIN", "date": today, "time": "22:00",
         "quality": "4K", "stream_id": "ucl_1"},
        {"league": "الدوري الإنجليزي", "league_id": "england", "team1": "ليفربول", "team2": "أرسنال",
         "s1": "-", "s2": "-", "status": "upcoming", "ch": "beIN", "date": today, "time": "20:30",
         "quality": "4K", "stream_id": "england_1"},
        {"league": "الدوري الإيطالي", "league_id": "italy", "team1": "إنتر", "team2": "ميلان",
         "s1": "2", "s2": "0", "status": "finished", "ch": "beIN", "date": today, "time": "21:45",
         "quality": "4K", "stream_id": "italy_1"},
    ]
    if league:
        return [m for m in base_matches if m["league_id"] == league]
    return base_matches


# =========================================================
# ROUTES
# =========================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/player")
def player():
    return render_template("player.html", sources_json=SOURCES_JSON)


@app.route("/match")
def match_player():
    return render_template("player.html", sources_json=MATCH_SOURCES_JSON)


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
    matches = get_matches(league)
    return jsonify({"matches": matches, "count": len(matches)})


@app.route("/api/leagues")
def api_leagues():
    return jsonify({"leagues": FOOTBALL_LEAGUES})


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ONYX CINEMA v16.0",
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
