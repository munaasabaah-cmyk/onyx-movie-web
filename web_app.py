# -*- coding: utf-8 -*-
"""
ONYX CINEMA v12.0 - Flask + Discord Bot + TMDB + Multi Sources
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
SECRET_SALT = os.getenv("SECRET_SALT", "onyx_cinema_2026_secret")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1212admin")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
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
    r.headers["X-Frame-Options"] = "SAMEORIGIN"
    r.headers["X-XSS-Protection"] = "1; mode=block"
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return r

# =========================================================
# SOURCES - Real Working Sources
# =========================================================
REAL_SOURCES = [
    ("VidLink", "https://vidlink.pro/movie/{id}", "https://vidlink.pro/tv/{id}/{s}/{e}"),
    ("Videasy", "https://player.videasy.net/movie/{id}", "https://player.videasy.net/tv/{id}/{s}/{e}"),
    ("AutoEmbed", "https://player.autoembed.cc/embed/movie/{id}", "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}"),
    ("SmashyStream", "https://player.smashy.stream/movie/{id}", "https://player.smashy.stream/tv/{id}?s={s}&e={e}"),
    ("VidSrc XYZ", "https://vidsrc.xyz/embed/movie?tmdb={id}", "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrc ME", "https://vidsrc.me/embed/movie?tmdb={id}", "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrc CC", "https://vidsrc.cc/v2/embed/movie/{id}", "https://vidsrc.cc/v2/embed/tv/{id}/{s}/{e}"),
    ("2Embed", "https://www.2embed.to/embed/tmdb/movie?id={id}", "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("Embed SU", "https://embed.su/embed/movie/{id}", "https://embed.su/embed/tv/{id}/{s}/{e}"),
    ("MultiEmbed", "https://multiembed.mov/?video_id={id}&tmdb=1", "https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("VidPlus", "https://vidplus.to/embed/movie/{id}", "https://vidplus.to/embed/tv/{id}/{s}/{e}"),
    ("VidCloud", "https://vidcloud.stream/movie/{id}", "https://vidcloud.stream/tv/{id}/{s}/{e}"),
    ("VidPlay", "https://vidplay.site/movie/{id}", "https://vidplay.site/tv/{id}/{s}/{e}"),
    ("VidFast", "https://vidfast.pro/movie/{id}", "https://vidfast.pro/tv/{id}/{s}/{e}"),
    ("VidEasy", "https://videasy.net/movie/{id}", "https://videasy.net/tv/{id}/{s}/{e}"),
]

ARABIC_SOURCES = [
    ("ArabSeed", "https://arabseed.com/embed/movie/{id}", "https://arabseed.com/embed/tv/{id}/{s}/{e}"),
    ("CimaNow", "https://cimanow.com/embed/movie/{id}", "https://cimanow.com/embed/tv/{id}/{s}/{e}"),
    ("Shahid", "https://shahid.net/embed/movie/{id}", "https://shahid.net/embed/tv/{id}/{s}/{e}"),
]

SPORTS_SOURCES = [
    ("YallaShoot 1", "https://yallashoot.com/embed/{id}", "https://yallashoot.com/embed/{id}"),
    ("YallaShoot 2", "https://yallashoot2.com/embed/{id}", "https://yallashoot2.com/embed/{id}"),
    ("KoraLive 1", "https://koralive.com/embed/{id}", "https://koralive.com/embed/{id}"),
    ("BeinSport 1", "https://beinsport.com/embed/{id}", "https://beinsport.com/embed/{id}"),
    ("SSC 1", "https://ssc.com/embed/{id}", "https://ssc.com/embed/{id}"),
    ("HesGoal", "https://hesgoal.com/embed/{id}", "https://hesgoal.com/embed/{id}"),
    ("FootyBite", "https://footybite.com/embed/{id}", "https://footybite.com/embed/{id}"),
    ("Sportsurge", "https://sportsurge.com/embed/{id}", "https://sportsurge.com/embed/{id}"),
]

QUALITY_VARIANTS = ["4K", "HD", "SD"]
QUALITY_SUFFIX = {
    "4K": "?quality=4k",
    "HD": "?quality=hd",
    "SD": "?quality=sd",
}

def build_sources():
    sources = []
    for name, movie_url, tv_url in REAL_SOURCES + ARABIC_SOURCES:
        for q in QUALITY_VARIANTS:
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
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/12.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
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
    return base_matches# =========================================================
# DISCORD BOT - Running in background thread
# =========================================================
_bot_started = False

def start_discord_bot():
    """تشغيل bot.py في thread منفصل"""
    global _bot_started
    if _bot_started:
        return
    _bot_started = True
    try:
        print("[ONYX] Starting Discord bot in background...")
        subprocess.Popen([sys.executable, "bot.py"])
    except Exception as e:
        print(f"[ONYX] Bot failed to start: {e}")


# تشغيل البوت عند بدء الخدمة (فقط عند التشغيل الحقيقي)
if RUN_BOT and os.getenv("WERKZEUG_RUN_MAIN") != "true":
    _bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
    _bot_thread.start()


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
        "service": "ONYX CINEMA v12.0",
        "tmdb": "ok" if TMDB_API_KEY else "missing",
        "sources": len(PLAYER_SOURCES),
        "match_sources": len(SPORTS_SOURCES),
        "leagues": len(FOOTBALL_LEAGUES),
        "bot_running": _bot_started,
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
