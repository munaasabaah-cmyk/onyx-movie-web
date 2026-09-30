# -*- coding: utf-8 -*-
"""
ONYX CINEMA v14.0 - Flask + Discord Bot + Templates Folder
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
    r.headers["Content-Security-Policy"] = (
        "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
        "frame-ancestors *;"
    )
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
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/14.0"})
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
        "service": "ONYX CINEMA v14.0",
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
