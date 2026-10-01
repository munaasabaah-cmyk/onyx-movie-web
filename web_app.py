"""
ONYX CINEMA v18.0 - Cinema Streaming Platform
Flask + TMDB + .env Configuration
"""

import os
import time
import json
import urllib.request
import urllib.parse
import urllib.error

from pathlib import Path
from collections import defaultdict
from datetime import datetime

from flask import Flask, jsonify, request, render_template, Response, redirect

try:
    from dotenv import load_dotenv
except ImportError:
    raise RuntimeError(
        "مكتبة python-dotenv غير مثبتة.\n"
        "ثبتها بالأمر التالي:\n"
        "pip install python-dotenv"
    )

# ════════════════════════════════════════════════════════════
# LOAD .ENV
# ════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

if not ENV_FILE.exists():
    raise RuntimeError(
        f"ملف .env غير موجود في هذا المسار:\n{ENV_FILE}\n\n"
        "أنشئ ملف .env بجانب app.py."
    )

load_dotenv(dotenv_path=ENV_FILE)

# ════════════════════════════════════════════════════════════
# APP
# ════════════════════════════════════════════════════════════

app = Flask(__name__, template_folder="templates")

# ════════════════════════════════════════════════════════════
# CONFIG FROM .ENV
# ════════════════════════════════════════════════════════════

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "").strip()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

RUN_BOT = os.getenv("RUN_BOT", "false").lower() in {
    "1", "true", "yes", "on"
}

CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))
PORT = int(os.getenv("PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() in {
    "1", "true", "yes", "on"
}

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()

if not SECRET_KEY:
    SECRET_KEY = "change-this-in-production"

app.config["SECRET_KEY"] = SECRET_KEY

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"
TMDB_LANG = os.getenv("TMDB_LANG", "ar").strip() or "ar"

# ════════════════════════════════════════════════════════════
# CACHE SYSTEM
# ════════════════════════════════════════════════════════════

_cache = {}


def cache_get(key):
    """Get an item from cache if it has not expired."""
    item = _cache.get(key)

    if item and time.time() - item["t"] < CACHE_TTL:
        return item["v"]

    return None


def cache_set(key, value):
    """Save an item to cache."""
    _cache[key] = {
        "v": value,
        "t": time.time()
    }
    return value


def cache_clear_old():
    """Delete all expired cache entries."""
    now = time.time()

    expired_keys = [
        key for key, value in _cache.items()
        if now - value["t"] > CACHE_TTL
    ]

    for key in expired_keys:
        del _cache[key]

# ════════════════════════════════════════════════════════════
# TMDB CORE FUNCTIONS
# ════════════════════════════════════════════════════════════


def tmdb(endpoint, params=None, lang=None):
    """Fetch data from TMDB API with cache."""

    if not TMDB_API_KEY:
        return {
            "error": "TMDB_API_KEY missing",
            "results": []
        }

    query_params = dict(params or {})
    query_params["api_key"] = TMDB_API_KEY
    query_params["language"] = lang or TMDB_LANG

    query_string = urllib.parse.urlencode(query_params)
    url = f"{TMDB_BASE}{endpoint}?{query_string}"
    cache_key = f"tmdb::{endpoint}::{query_string}"

    cached_data = cache_get(cache_key)

    if cached_data is not None:
        return cached_data

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ONYX-CINEMA/18.0"
            }
        )

        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
            return cache_set(cache_key, data)

    except urllib.error.HTTPError as error:
        print(f"[TMDB] HTTP {error.code}: {endpoint}")

        return {
            "error": f"TMDB HTTP {error.code}",
            "results": []
        }

    except Exception as error:
        print(f"[TMDB] Error: {error}")

        return {
            "error": str(error),
            "results": []
        }

# ════════════════════════════════════════════════════════════
# MOVIE API FUNCTIONS
# ════════════════════════════════════════════════════════════


def get_trending():
    return tmdb("/trending/all/week").get("results", [])


def get_popular(media_type="movie"):
    return tmdb(f"/{media_type}/popular").get("results", [])


def get_top_rated(media_type="movie"):
    return tmdb(f"/{media_type}/top_rated").get("results", [])


def get_now_playing():
    return tmdb("/movie/now_playing").get("results", [])


def get_upcoming():
    return tmdb("/movie/upcoming").get("results", [])


def search_multi(query):
    return tmdb(
        "/search/multi",
        {
            "query": query,
            "include_adult": "false"
        }
    ).get("results", [])


def search_person(query):
    return tmdb(
        "/search/person",
        {
            "query": query
        }
    ).get("results", [])


def get_movie_details(movie_id, media_type="movie"):
    return tmdb(
        f"/{media_type}/{movie_id}",
        {
            "append_to_response": (
                "credits,videos,similar,recommendations,"
                "images,external_ids"
            )
        }
    )


def get_season_details(tv_id, season_number):
    return tmdb(f"/tv/{tv_id}/season/{season_number}")


def get_person_details(person_id):
    return tmdb(
        f"/person/{person_id}",
        {
            "append_to_response": "combined_credits,images,external_ids"
        }
    )


def get_genres(media_type="movie"):
    return tmdb(f"/genre/{media_type}/list").get("genres", [])


def get_by_genre(genre_id, media_type="movie"):
    return tmdb(
        f"/discover/{media_type}",
        {
            "with_genres": genre_id,
            "sort_by": "popularity.desc",
            "include_adult": "false"
        }
    ).get("results", [])


def discover_advanced(
    media_type="movie",
    genre=None,
    year=None,
    language=None,
    sort="popularity.desc"
):
    params = {
        "sort_by": sort,
        "include_adult": "false"
    }

    if genre:
        params["with_genres"] = genre

    if year:
        year_key = (
            "primary_release_year"
            if media_type == "movie"
            else "first_air_date_year"
        )
        params[year_key] = year

    if language:
        params["with_original_language"] = language

    return tmdb(
        f"/discover/{media_type}",
        params
    ).get("results", [])


def get_movie_videos(movie_id, media_type="movie"):
    return tmdb(
        f"/{media_type}/{movie_id}/videos",
        {
            "language": TMDB_LANG
        }
    ).get("results", [])

# ════════════════════════════════════════════════════════════
# STREAMING SOURCES
# ════════════════════════════════════════════════════════════

STREAMING_SOURCES = [
    {
        "id": "vidsrc",
        "name": "VidSrc",
        "quality": "1080p",
        "type": "embedded",
        "movie_url": "https://vidsrc.me/embed/{id}",
        "tv_url": "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}",
        "lang": "multi",
        "reliability": "high"
    },
    {
        "id": "hdrezka",
        "name": "HDRezka",
        "quality": "4K",
        "type": "embedded",
        "movie_url": "https://hdrezka.ag/search?q={title}",
        "tv_url": "https://hdrezka.ag/search?q={title}",
        "lang": "ar",
        "reliability": "medium"
    },
    {
        "id": "streamlare",
        "name": "Streamlare",
        "quality": "1080p",
        "type": "embedded",
        "movie_url": "https://streamlare.com/e/{id}",
        "tv_url": "https://streamlare.com/e/{id}",
        "lang": "multi",
        "reliability": "medium"
    },
    {
        "id": "rabbitstream",
        "name": "RabbitStream",
        "quality": "1080p",
        "type": "embedded",
        "movie_url": "https://rabbitstream.net/embed/tmdb?id={id}",
        "tv_url": "https://rabbitstream.net/embed/tmdb?id={id}&s={s}&e={e}",
        "lang": "multi",
        "reliability": "high"
    },
    {
        "id": "movie4k",
        "name": "Movie4K",
        "quality": "4K",
        "type": "embedded",
        "movie_url": "https://movie4k.is/search/{title}",
        "tv_url": "https://movie4k.is/search/{title}",
        "lang": "en",
        "reliability": "medium"
    }
]


def get_streaming_sources(
    media_id,
    media_type="movie",
    title="",
    season=None,
    episode=None
):
    """Return formatted external source URLs."""

    sources = []

    safe_title = urllib.parse.quote(title or "")

    for source in STREAMING_SOURCES:
        try:
            if media_type == "movie":
                url = source["movie_url"].format(
                    id=media_id,
                    title=safe_title
                )

            else:
                season_number = season or "1"
                episode_number = episode or "1"

                url = source["tv_url"].format(
                    id=media_id,
                    title=safe_title,
                    s=season_number,
                    e=episode_number
                )

            sources.append(
                {
                    "id": source["id"],
                    "name": source["name"],
                    "quality": source["quality"],
                    "url": url,
                    "type": source["type"],
                    "language": source["lang"],
                    "reliability": source["reliability"],
                    "playable": True
                }
            )

        except Exception as error:
            print(f"[SOURCE] Error with {source['name']}: {error}")

    return sources


def get_all_sources(
    media_id,
    media_type="movie",
    title="",
    season=None,
    episode=None
):
    sources = get_streaming_sources(
        media_id,
        media_type,
        title,
        season,
        episode
    )

    return {
        "id": media_id,
        "type": media_type,
        "title": title,
        "sources": sources,
        "count": len(sources),
        "working": len(
            [
                source for source in sources
                if source.get("playable")
            ]
        ),
        "timestamp": datetime.now().isoformat()
    }

# ════════════════════════════════════════════════════════════
# SECURITY & RATE LIMITING
# ════════════════════════════════════════════════════════════

_rate = defaultdict(list)
_banned = {}
_log = defaultdict(int)


def get_ip():
    """Get client IP address."""

    for header in (
        "CF-Connecting-IP",
        "X-Forwarded-For",
        "X-Real-IP"
    ):
        value = request.headers.get(header)

        if value:
            return value.split(",")[0].strip()

    return request.remote_addr or "unknown"


@app.before_request
def rate_limit():
    """Simple rate-limit middleware."""

    ignored_paths = (
        request.path.startswith("/api/")
        or request.path.startswith("/img/")
        or request.path == "/health"
    )

    if ignored_paths:
        return None

    ip = get_ip()
    now = time.time()

    if ip in _banned and now < _banned[ip]:
        return jsonify({"error": "banned"}), 429

    _rate[ip] = [
        timestamp
        for timestamp in _rate[ip]
        if now - timestamp < 60
    ]

    _rate[ip].append(now)
    _log[ip] += 1

    if _log[ip] > 5000:
        _banned[ip] = now + 1800
        return jsonify({"error": "rate limit"}), 429

    if len(_rate[ip]) > 500:
        return jsonify({"error": "rate limit"}), 429

    return None


@app.after_request
def security_headers(response):
    """Add basic HTTP security headers."""

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # السماح بعرض iframe من المصادر المستخدمة إن احتجت ذلك
    response.headers.pop("X-Frame-Options", None)
    response.headers.pop("Content-Security-Policy", None)

    return response

# ════════════════════════════════════════════════════════════
# PAGE ROUTES
# ════════════════════════════════════════════════════════════


@app.route("/")
def index():
    """Home page."""

    # لا تمرر TMDB_API_KEY إلى HTML أو JavaScript.
    return render_template("index.html")


@app.route("/player")
def player():
    """Video player page."""
    return render_template("player.html")


@app.route("/match")
def match_player():
    """Sports player page."""
    return render_template("player.html")

# ════════════════════════════════════════════════════════════
# MOVIES & TV API ROUTES
# ════════════════════════════════════════════════════════════


@app.route("/api/trending")
def api_trending():
    return jsonify({"results": get_trending()})


@app.route("/api/popular/<media_type>")
def api_popular(media_type):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400

    return jsonify({"results": get_popular(media_type)})


@app.route("/api/top_rated/<media_type>")
def api_top_rated(media_type):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400

    return jsonify({"results": get_top_rated(media_type)})


@app.route("/api/now_playing")
def api_now_playing():
    return jsonify({"results": get_now_playing()})


@app.route("/api/upcoming")
def api_upcoming():
    return jsonify({"results": get_upcoming()})


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()[:100]

    if not query:
        return jsonify({"results": []})

    return jsonify({"results": search_multi(query)})


@app.route("/api/movie/<int:movie_id>")
def api_movie(movie_id):
    return jsonify(get_movie_details(movie_id, "movie"))


@app.route("/api/tv/<int:tv_id>")
def api_tv(tv_id):
    return jsonify(get_movie_details(tv_id, "tv"))


@app.route("/api/tv/<int:tv_id>/season/<int:season_number>")
def api_tv_season(tv_id, season_number):
    return jsonify(get_season_details(tv_id, season_number))


@app.route("/api/person/<int:person_id>")
def api_person(person_id):
    return jsonify(get_person_details(person_id))


@app.route("/api/person/search")
def api_person_search():
    query = request.args.get("q", "").strip()[:100]

    if not query:
        return jsonify({"results": []})

    return jsonify({"results": search_person(query)})


@app.route("/api/genres/<media_type>")
def api_genres(media_type):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400

    return jsonify({"genres": get_genres(media_type)})


@app.route("/api/genre/<media_type>/<int:genre_id>")
def api_genre(media_type, genre_id):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400

    return jsonify({
        "results": get_by_genre(
            genre_id,
            media_type
        )
    })


@app.route("/api/discover")
def api_discover():
    genre = request.args.get("genre")
    year = request.args.get("year")
    language = request.args.get("lang")
    media_type = request.args.get("type", "movie")
    sort = request.args.get("sort", "popularity.desc")

    if media_type not in ("movie", "tv"):
        media_type = "movie"

    return jsonify(
        {
            "results": discover_advanced(
                media_type=media_type,
                genre=genre,
                year=year,
                language=language,
                sort=sort
            )
        }
    )


@app.route("/api/videos/<media_type>/<int:media_id>")
def api_videos(media_type, media_id):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400

    return jsonify(
        {
            "results": get_movie_videos(
                media_id,
                media_type
            )
        }
    )

# ════════════════════════════════════════════════════════════
# STREAMING SOURCE ROUTES
# ════════════════════════════════════════════════════════════


@app.route("/api/sources")
def api_sources():
    """Return configured source names and information."""

    return jsonify(
        {
            "sources": STREAMING_SOURCES,
            "count": len(STREAMING_SOURCES),
            "update": datetime.now().isoformat()
        }
    )


@app.route("/api/stream/<media_type>/<int:media_id>")
def api_stream(media_type, media_id):
    """Return formatted streaming-source URLs."""

    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400

    season = request.args.get("s")
    episode = request.args.get("e")
    title = request.args.get("title", "").strip()[:300]

    result = get_all_sources(
        media_id=media_id,
        media_type=media_type,
        title=title,
        season=season,
        episode=episode
    )

    return jsonify(result)


@app.route("/api/play/<media_type>/<int:media_id>")
def api_play(media_type, media_id):
    """
    Redirect to the first configured external source.
    Prefer a licensed playback integration for production use.
    """

    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400

    season = request.args.get("s", "1")
    episode = request.args.get("e", "1")

    details = get_movie_details(media_id, media_type)

    title = (
        details.get("title")
        or details.get("name")
        or ""
    )

    sources = get_streaming_sources(
        media_id=media_id,
        media_type=media_type,
        title=title,
        season=season,
        episode=episode
    )

    if not sources:
        return jsonify({"error": "no sources found"}), 404

    return redirect(sources[0]["url"])

# ════════════════════════════════════════════════════════════
# TMDB PROXY
# ════════════════════════════════════════════════════════════


@app.route("/api/3/<path:subpath>")
def tmdb_proxy(subpath):
    """Proxy TMDB API requests without exposing the key to users."""

    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY missing"}), 500

    params = dict(request.args)
    params["api_key"] = TMDB_API_KEY

    if "language" not in params:
        params["language"] = TMDB_LANG

    query_string = urllib.parse.urlencode(params)
    url = f"{TMDB_BASE}/{subpath}?{query_string}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ONYX-CINEMA/18.0"
            }
        )

        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
            return jsonify(data)

    except urllib.error.HTTPError as error:
        return jsonify(
            {
                "error": f"TMDB HTTP {error.code}"
            }
        ), error.code

    except Exception as error:
        return jsonify(
            {
                "error": str(error)
            }
        ), 500

# ════════════════════════════════════════════════════════════
# TMDB IMAGE PROXY
# ════════════════════════════════════════════════════════════


@app.route("/img/t/p/<size>/<path:filename>")
def img_proxy(size, filename):
    """Proxy TMDB image files."""

    allowed_sizes = {
        "w92",
        "w154",
        "w185",
        "w342",
        "w500",
        "w780",
        "original"
    }

    if size not in allowed_sizes:
        return Response(b"", status=400)

    url = f"{TMDB_IMG}/{size}/{filename}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ONYX-CINEMA/18.0"
            }
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            content_type = response.headers.get(
                "Content-Type",
                "image/jpeg"
            )

            return Response(
                data,
                status=200,
                mimetype=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400"
                }
            )

    except Exception as error:
        print(f"[IMG] Error: {error}")
        return Response(b"", status=404)

# ════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════


@app.route("/health")
def health():
    """Application status endpoint."""

    cache_clear_old()

    return jsonify(
        {
            "status": "ok",
            "service": "ONYX CINEMA v18.0",
            "tmdb": "connected" if TMDB_API_KEY else "missing",
            "sources": len(STREAMING_SOURCES),
            "cache_size": len(_cache),
            "time": datetime.now().isoformat(),
            "version": "18.0"
        }
    )

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════


if __name__ == "__main__":
    print(
        f"""
╔══════════════════════════════════════════════════════════════╗
║ ONYX CINEMA v18.0 - Streaming Platform                       ║
║──────────────────────────────────────────────────────────────║
║ TMDB API: {"✅ Connected" if TMDB_API_KEY else "❌ Missing"}                                     
║ Streaming Sources: {len(STREAMING_SOURCES)}                                        
║ Server Port: {PORT}                                                 
║──────────────────────────────────────────────────────────────║
║ Ready at: http://localhost:{PORT}                            
╚══════════════════════════════════════════════════════════════╝
"""
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=FLASK_DEBUG,
        threaded=True
    )
