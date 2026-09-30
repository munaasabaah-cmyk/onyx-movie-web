# -*- coding: utf-8 -*-
"""
ONYX CINEMA v17.0 - Flask + Discord Bot + movie_api Integration
Full integration with movie_api.py for cast, seasons, recommendations
"""

from flask import Flask, jsonify, request, render_template
import os
import time
import json
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

# Import movie_api
try:
    import movie_api
    HAS_MOVIE_API = True
    print("[ONYX] movie_api.py loaded successfully")
except ImportError as e:
    HAS_MOVIE_API = False
    print(f"[ONYX] movie_api.py not found: {e}")

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
# SOURCES - 4 PREMIUM 4K + FALLBACK
# =========================================================
REAL_SOURCES = [
    {
        "name": "VidLink 4K",
        "q": "4K",
        "movie": "https://vidlink.pro/movie/{id}?quality=4k&sub=ar",
        "tv": "https://vidlink.pro/tv/{id}/{s}/{e}?quality=4k&sub=ar",
    },
    {
        "name": "Videasy 4K",
        "q": "4K",
        "movie": "https://player.videasy.net/movie/{id}?quality=4k&sub=ar",
        "tv": "https://player.videasy.net/tv/{id}/{s}/{e}?quality=4k&sub=ar",
    },
    {
        "name": "VidSrc 4K",
        "q": "4K",
        "movie": "https://vidsrc.xyz/embed/movie?tmdb={id}&quality=4k&ds_lang=ar",
        "tv": "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}&quality=4k&ds_lang=ar",
    },
    {
        "name": "VidSrc ME",
        "q": "HD",
        "movie": "https://vidsrc.me/embed/movie?tmdb={id}",
        "tv": "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}",
    },
    {
        "name": "AutoEmbed",
        "q": "HD",
        "movie": "https://player.autoembed.cc/embed/movie/{id}",
        "tv": "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}",
    },
    {
        "name": "2Embed",
        "q": "HD",
        "movie": "https://www.2embed.to/embed/tmdb/movie?id={id}",
        "tv": "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}",
    },
    {
        "name": "SmashyStream",
        "q": "HD",
        "movie": "https://player.smashy.stream/movie/{id}",
        "tv": "https://player.smashy.stream/tv/{id}?s={s}&e={e}",
    },
    {
        "name": "Embed.su",
        "q": "HD",
        "movie": "https://embed.su/embed/movie/{id}",
        "tv": "https://embed.su/embed/tv/{id}/{s}/{e}",
    },
]

PLAYER_SOURCES = REAL_SOURCES
SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)


# =========================================================
# TMDB FALLBACK (if movie_api not available)
# =========================================================
def tmdb_fallback(ep, params=None):
    if not TMDB_API_KEY:
        return {"error": "no key", "results": []}
    p = params or {}
    p["api_key"] = TMDB_API_KEY
    p["language"] = "ar"
    url = f"{TMDB_BASE}{ep}?{urllib.parse.urlencode(p)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/17.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


# Import urllib for fallback
import urllib.request
import urllib.parse


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
    ]
    if league:
        return [m for m in base_matches if m["league_id"] == league]
    return base_matches


# =========================================================
# ROUTES - PAGES
# =========================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/player")
def player():
    return render_template("player.html")


@app.route("/match")
def match_player():
    return render_template("player.html")


# =========================================================
# ROUTES - API (using movie_api)
# =========================================================
@app.route("/api/trending")
def api_trending():
    if HAS_MOVIE_API:
        return jsonify({"results": movie_api.get_trending()})
    return jsonify(tmdb_fallback("/trending/all/week"))


@app.route("/api/popular/<mt>")
def api_popular(mt):
    if mt not in ("movie", "tv"):
        return jsonify({"error": "invalid"}), 400
    if HAS_MOVIE_API:
        return jsonify({"results": movie_api.get_popular(mt)})
    return jsonify(tmdb_fallback(f"/{mt}/popular"))


@app.route("/api/top_rated/<mt>")
def api_top_rated(mt):
    if mt not in ("movie", "tv"):
        return jsonify({"error": "invalid"}), 400
    if HAS_MOVIE_API:
        return jsonify({"results": movie_api.get_top_rated(mt)})
    return jsonify(tmdb_fallback(f"/{mt}/top_rated"))


@app.route("/api/now_playing")
def api_now_playing():
    if HAS_MOVIE_API:
        return jsonify({"results": movie_api.get_now_playing()})
    return jsonify(tmdb_fallback("/movie/now_playing"))


@app.route("/api/upcoming")
def api_upcoming():
    if HAS_MOVIE_API:
        return jsonify({"results": movie_api.get_upcoming()})
    return jsonify(tmdb_fallback("/movie/upcoming"))


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()[:100]
    if not q:
        return jsonify({"results": []})
    if HAS_MOVIE_API:
        return jsonify({"results": movie_api.search_multi(q)})
    return jsonify(tmdb_fallback("/search/multi", {"query": q}))


@app.route("/api/movie/<int:mid>")
def api_movie(mid):
    if HAS_MOVIE_API:
        details = movie_api.get_movie_details(mid, "movie")
        return jsonify(details or {"error": "not found"})
    return jsonify(tmdb_fallback(f"/movie/{mid}", {
        "append_to_response": "credits,videos,similar,recommendations,images"
    }))


@app.route("/api/tv/<int:tid>")
def api_tv(tid):
    if HAS_MOVIE_API:
        details = movie_api.get_movie_details(tid, "tv")
        return jsonify(details or {"error": "not found"})
    return jsonify(tmdb_fallback(f"/tv/{tid}", {
        "append_to_response": "credits,videos,similar,recommendations,images"
    }))


@app.route("/api/tv/<int:tid>/season/<int:s>")
def api_tv_season(tid, s):
    if HAS_MOVIE_API:
        details = movie_api.get_season_details(tid, s)
        return jsonify(details or {"error": "not found"})
    return jsonify(tmdb_fallback(f"/tv/{tid}/season/{s}"))


# =========================================================
# ROUTES - PERSON (الجدبد!)
# =========================================================
@app.route("/api/person/<int:pid>")
def api_person(pid):
    """معلومات الممثل الكاملة"""
    if HAS_MOVIE_API:
        details = movie_api.get_person_details(pid)
        return jsonify(details or {"error": "not found"})
    return jsonify(tmdb_fallback(f"/person/{pid}", {
        "append_to_response": "combined_credits,images,external_ids"
    }))


@app.route("/api/person/search")
def api_person_search():
    """بحث عن ممثلين"""
    q = request.args.get("q", "").strip()[:100]
    if not q:
        return jsonify({"results": []})
    if HAS_MOVIE_API:
        return jsonify({"results": movie_api.search_person(q)})
    return jsonify(tmdb_fallback("/search/person", {"query": q}))


# =========================================================
# ROUTES - GENRES + DISCOVER
# =========================================================
@app.route("/api/genres/<mt>")
def api_genres(mt):
    """قائمة التصنيفات"""
    if HAS_MOVIE_API:
        return jsonify(movie_api.get_genres(mt))
    return jsonify({})


@app.route("/api/genre/<mt>/<int:gid>")
def api_genre(mt, gid):
    """أفلام حسب التصنيف"""
    if mt not in ("movie", "tv"):
        return jsonify({"error": "invalid"}), 400
    if HAS_MOVIE_API:
        return jsonify({"results": movie_api.get_by_genre(gid, mt)})
    return jsonify(tmdb_fallback(f"/discover/{mt}", {
        "with_genres": gid, "sort_by": "popularity.desc"
    }))


@app.route("/api/discover")
def api_discover():
    """تصفح متقدم"""
    genre = request.args.get("genre")
    year = request.args.get("year")
    lang = request.args.get("lang")
    mtype = request.args.get("type", "movie")
    if mtype not in ("movie", "tv"):
        mtype = "movie"

    if HAS_MOVIE_API:
        results = movie_api.discover_advanced(mtype, genre, year, lang)
        return jsonify({"results": results})

    params = {"sort_by": "popularity.desc"}
    if genre: params["with_genres"] = genre
    if year:
        if mtype == "movie":
            params["primary_release_year"] = year
        else:
            params["first_air_date_year"] = year
    if lang: params["with_original_language"] = lang
    return jsonify(tmdb_fallback(f"/discover/{mtype}", params))


# =========================================================
# ROUTES - MATCHES
# =========================================================
@app.route("/api/matches")
def api_matches():
    league = request.args.get("league")
    matches = get_matches(league)
    return jsonify({"matches": matches, "count": len(matches)})


@app.route("/api/leagues")
def api_leagues():
    return jsonify({"leagues": FOOTBALL_LEAGUES})


# =========================================================
# HEALTH
# =========================================================
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ONYX CINEMA v17.0",
        "tmdb": "ok" if TMDB_API_KEY else "missing",
        "movie_api": "loaded" if HAS_MOVIE_API else "fallback",
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
