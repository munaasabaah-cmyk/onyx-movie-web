ONYX CINEMA v17.3 - All-in-One (Flask + Discord Bot + movie_api + TMDB Proxy)
افلام ومسلسلات كاملة - دقة عالية 4K
"""
import os
import sys
import time
import json
import threading
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from flask import Flask, jsonify, request, render_template, Response
try:
from dotenv import load_dotenv
load_dotenv()
except ImportError:
pass
app = Flask(name, template_folder="templates")
=========================================================
CONFIG
=========================================================
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"
RUN_BOT = os.getenv("RUN_BOT", "false").lower() == "true"
TMDB_LANG = "ar"
CACHE_TTL = 600
=========================================================
CACHE
=========================================================
_cache = {}
def cache_get(key):
item = _cache.get(key)
if item and time.time() - item["t"] < CACHE_TTL:
return item["v"]
return None
def cache_set(key, value):
_cache[key] = {"v": value, "t": time.time()}
return value
=========================================================
TMDB CORE
=========================================================
def tmdb(ep, params=None, lang=None):
if not TMDB_API_KEY:
return {"error": "TMDB_API_KEY missing", "results": []}
p = dict(params or {})
p["api_key"] = TMDB_API_KEY
p["language"] = lang or TMDB_LANG
qs = urllib.parse.urlencode(p)
url = f"{TMDB_BASE}{ep}?{qs}"
ck = f"tmdb::{ep}::{qs}"
hit = cache_get(ck)
if hit is not None:
return hit
try:
req = urllib.request.Request(url, headers={"User-Agent": "ONYX/17.3"})
with urllib.request.urlopen(req, timeout=25) as r:
data = json.loads(r.read().decode("utf-8"))
return cache_set(ck, data)
except urllib.error.HTTPError as e:
return {"error": f"TMDB HTTP {e.code}", "results": []}
except Exception as e:
return {"error": str(e), "results": []}
=========================================================
MOVIE API (مدمج بالكامل)
=========================================================
def get_trending():
return tmdb("/trending/all/week").get("results", [])
def get_popular(mt="movie"):
return tmdb(f"/{mt}/popular").get("results", [])
def get_top_rated(mt="movie"):
return tmdb(f"/{mt}/top_rated").get("results", [])
def get_now_playing():
return tmdb("/movie/now_playing").get("results", [])
def get_upcoming():
return tmdb("/movie/upcoming").get("results", [])
def search_multi(q):
return tmdb("/search/multi", {"query": q, "include_adult": "false"}).get("results", [])
def search_person(q):
return tmdb("/search/person", {"query": q}).get("results", [])
def get_movie_details(mid, mt="movie"):
return tmdb(f"/{mt}/{mid}", {
"append_to_response": "credits,videos,similar,recommendations,images,external_ids"
})
def get_season_details(tid, s):
return tmdb(f"/tv/{tid}/season/{s}")
def get_person_details(pid):
return tmdb(f"/person/{pid}", {
"append_to_response": "combined_credits,images,external_ids"
})
def get_genres(mt="movie"):
return tmdb(f"/genre/{mt}/list").get("genres", [])
def get_by_genre(gid, mt="movie"):
return tmdb(f"/discover/{mt}", {
"with_genres": gid, "sort_by": "popularity.desc"
}).get("results", [])
def discover_advanced(mt="movie", genre=None, year=None, lang=None, sort="popularity.desc"):
params = {"sort_by": sort, "include_adult": "false"}
if genre: params["with_genres"] = genre
if year:
params["primary_release_year" if mt == "movie" else "first_air_date_year"] = year
if lang: params["with_original_language"] = lang
return tmdb(f"/discover/{mt}", params).get("results", [])
def get_movie_videos(mid, mt="movie"):
return tmdb(f"/{mt}/{mid}/videos", {"language": "ar"}).get("results", [])
=========================================================
SOURCES — مصادر بث دقة عالية
=========================================================
REAL_SOURCES = [
{
"name": "CinemaBox 4K",
"q": "4K",
"movie": "https://smart.albox.co/movie/{id}",
"tv": "https://smart.albox.co/tv/{id}/{s}/{e}",
"lang": "ar",
},
{
"name": "OnYx Direct 1080p",
"q": "1080p",
"movie": "https://onyx.stream/m/{id}",
"tv": "https://onyx.stream/t/{id}/{s}/{e}",
"lang": "multi",
},
{
"name": "CinemaHD 4K",
"q": "4K",
"movie": "https://cinemahd.io/movie/{id}",
"tv": "https://cinemahd.io/series/{id}/{s}/{e}",
"lang": "en",
},
]
PLAYER_SOURCES = REAL_SOURCES
SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)
=========================================================
SECURITY
=========================================================
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
if (request.path.startswith("/api/")
or request.path.startswith("/img/")
or request.path in ("/health",)):
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
=========================================================
FOOTBALL
=========================================================
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
def get_matches(league=None):
today = datetime.now().strftime("%Y-%m-%d")
base = [
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
return [m for m in base if m["league_id"] == league]
return base
=========================================================
ROUTES — PAGES
=========================================================
@app.route("/")
def index():
return render_template("index.html", tmdb_key=TMDB_API_KEY, sources=SOURCES_JSON)
@app.route("/player")
def player():
return render_template("player.html", tmdb_key=TMDB_API_KEY, sources=SOURCES_JSON)
@app.route("/match")
def match_player():
return render_template("player.html", tmdb_key=TMDB_API_KEY, sources=SOURCES_JSON)
=========================================================
ROUTES — API
=========================================================
@app.route("/api/trending")
def api_trending():
return jsonify({"results": get_trending()})
@app.route("/api/popular/<mt>")
def api_popular(mt):
if mt not in ("movie", "tv"):
return jsonify({"error": "invalid"}), 400
return jsonify({"results": get_popular(mt)})
@app.route("/api/top_rated/<mt>")
def api_top_rated(mt):
if mt not in ("movie", "tv"):
return jsonify({"error": "invalid"}), 400
return jsonify({"results": get_top_rated(mt)})
@app.route("/api/now_playing")
def api_now_playing():
return jsonify({"results": get_now_playing()})
@app.route("/api/upcoming")
def api_upcoming():
return jsonify({"results": get_upcoming()})
@app.route("/api/search")
def api_search():
q = request.args.get("q", "").strip()[:100]
if not q:
return jsonify({"results": []})
return jsonify({"results": search_multi(q)})
@app.route("/api/movie/int:mid")
def api_movie(mid):
return jsonify(get_movie_details(mid, "movie"))
@app.route("/api/tv/int:tid")
def api_tv(tid):
return jsonify(get_movie_details(tid, "tv"))
@app.route("/api/tv/int:tid/season/int:s")
def api_tv_season(tid, s):
return jsonify(get_season_details(tid, s))
@app.route("/api/person/int:pid")
def api_person(pid):
return jsonify(get_person_details(pid))
@app.route("/api/person/search")
def api_person_search():
q = request.args.get("q", "").strip()[:100]
if not q:
return jsonify({"results": []})
return jsonify({"results": search_person(q)})
@app.route("/api/genres/<mt>")
def api_genres(mt):
return jsonify({"genres": get_genres(mt)})
@app.route("/api/genre/<mt>/int:gid")
def api_genre(mt, gid):
if mt not in ("movie", "tv"):
return jsonify({"error": "invalid"}), 400
return jsonify({"results": get_by_genre(gid, mt)})
@app.route("/api/discover")
def api_discover():
genre = request.args.get("genre")
year = request.args.get("year")
lang = request.args.get("lang")
mtype = request.args.get("type", "movie")
if mtype not in ("movie", "tv"):
mtype = "movie"
return jsonify({"results": discover_advanced(mtype, genre, year, lang)})
@app.route("/api/videos/<mt>/int:mid")
def api_videos(mt, mid):
if mt not in ("movie", "tv"):
return jsonify({"error": "invalid"}), 400
return jsonify({"results": get_movie_videos(mid, mt)})
@app.route("/api/matches")
def api_matches():
league = request.args.get("league")
matches = get_matches(league)
return jsonify({"matches": matches, "count": len(matches)})
@app.route("/api/leagues")
def api_leagues():
return jsonify({"leagues": FOOTBALL_LEAGUES})
@app.route("/api/sources")
def api_sources():
return jsonify({"sources": PLAYER_SOURCES})
@app.route("/api/stream/<mt>/int:mid")
def api_stream(mt, mid):
"""يرجّع روابط البث لكل المصادر"""
if mt not in ("movie", "tv"):
return jsonify({"error": "invalid"}), 400
s = request.args.get("s", "1")
e = request.args.get("e", "1")
out = []
for src in PLAYER_SOURCES:
if mt == "movie":
url = src["movie"].format(id=mid)
else:
url = src["tv"].format(id=mid, s=s, e=e)
out.append({"name": src["name"], "quality": src["q"], "url": url, "lang": src.get("lang", "ar")})
return jsonify({"streams": out, "id": mid, "type": mt, "season": s, "episode": e})
=========================================================
TMDB PROXY
=========================================================
@app.route("/api/3/path:subpath")
def tmdb_proxy(subpath):
if not TMDB_API_KEY:
return jsonify({"error": "no api key"}), 500
params = dict(request.args)
params["api_key"] = TMDB_API_KEY
if "language" not in params:
params["language"] = TMDB_LANG
qs = urllib.parse.urlencode(params)
url = f"{TMDB_BASE}/{subpath}?{qs}"
try:
req = urllib.request.Request(url, headers={"User-Agent": "ONYX/17.3"})
with urllib.request.urlopen(req, timeout=25) as r:
data = json.loads(r.read().decode("utf-8"))
return jsonify(data)
except urllib.error.HTTPError as e:
return jsonify({"error": f"TMDB HTTP {e.code}"}), e.code
except Exception as e:
return jsonify({"error": str(e)}), 500
=========================================================
OMDb PROXY
=========================================================
@app.route("/api/omdb")
def omdb_proxy():
if not OMDB_API_KEY:
return jsonify({"error": "no omdb key"}), 500
params = dict(request.args)
params["apikey"] = OMDB_API_KEY
qs = urllib.parse.urlencode(params)
url = f"http://www.omdbapi.com/?{qs}"
try:
req = urllib.request.Request(url, headers={"User-Agent": "ONYX/17.3"})
with urllib.request.urlopen(req, timeout=10) as r:
data = json.loads(r.read().decode("utf-8"))
return jsonify(data)
except Exception as e:
return jsonify({"error": str(e)}), 500
=========================================================
IMAGE PROXY
=========================================================
@app.route("/img/t/p/<size>/path:filename")
def img_proxy(size, filename):
url = f"{TMDB_IMG}/{size}/{filename}"
try:
req = urllib.request.Request(url, headers={"User-Agent": "ONYX/17.3"})
with urllib.request.urlopen(req, timeout=15) as r:
data = r.read()
content_type = r.headers.get("Content-Type", "image/jpeg")
return Response(data, status=200, mimetype=content_type, headers={
"Cache-Control": "public, max-age=86400",
})
except Exception:
return Response(b"", status=404)
=========================================================
HEALTH
=========================================================
@app.route("/health")
def health():
return jsonify({
"status": "ok",
"service": "ONYX CINEMA v17.3",
"tmdb": "ok" if TMDB_API_KEY else "missing",
"omdb": "ok" if OMDB_API_KEY else "missing",
"discord": "ok" if DISCORD_TOKEN else "missing",
"sources": len(PLAYER_SOURCES),
"cache_size": len(_cache),
"time": datetime.now().isoformat(),
})
=========================================================
DISCORD BOT (in-process)
=========================================================
_bot_thread = None
_bot_client = None
def start_discord_bot():
"""يشغّل بوت ديسكورد داخل نفس العملية"""
global _bot_client
if not DISCORD_TOKEN:
print("[BOT] DISCORD_TOKEN missing - skip")
return
try:
import discord
from discord.ext import commands
from discord import app_commands
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
_bot_client = bot
@bot.event
async def on_ready():
print(f"[BOT] Logged in as {bot.user}")
try:
synced = await bot.tree.sync()
print(f"[BOT] Synced {len(synced)} commands")
except Exception as e:
print(f"[BOT] Sync error: {e}")
@bot.tree.command(name="search", description="ابحث عن فيلم أو مسلسل")
@app_commands.describe(query="اسم الفيلم أو المسلسل")
async def search_cmd(interaction: discord.Interaction, query: str):
await interaction.response.defer()
results = search_multi(query)[:5]
if not results:
await interaction.followup.send("❌ لا توجد نتائج")
return
embeds = []
for r in results:
title = r.get("title") or r.get("name") or "?"
year = (r.get("release_date") or r.get("first_air_date") or "")[:4]
poster = r.get("poster_path")
img = f"https://image.tmdb.org/t/p/w500{poster}" if poster else None
emb = discord.Embed(
title=f"{title} ({year})",
description=(r.get("overview") or "")[:400],
color=0x9b59b6,
)
if img:
emb.set_thumbnail(url=img)
emb.add_field(name="النوع", value=r.get("media_type", "?"))
emb.add_field(name="التقييم", value=str(r.get("vote_average", "?")))
embeds.append(emb)
await interaction.followup.send(embeds=embeds)
@bot.tree.command(name="trending", description="الأكثر رواجاً هذا الأسبوع")
async def trending_cmd(interaction: discord.Interaction):
await interaction.response.defer()
results = get_trending()[:6]
embeds = []
for r in results:
title = r.get("title") or r.get("name") or "?"
poster = r.get("poster_path")
img = f"https://image.tmdb.org/t/p/w500{poster}" if poster else None
emb = discord.Embed(title=title, color=0xe74c3c)
if img:
emb.set_thumbnail(url=img)
embeds.append(emb)
await interaction.followup.send(embeds=embeds)
@bot.tree.command(name="movie", description="تفاصيل فيلم")
@app_commands.describe(movie_id="ID الفيلم على TMDB")
async def movie_cmd(interaction: discord.Interaction, movie_id: int):
await interaction.response.defer()
d = get_movie_details(movie_id, "movie")
if not d or d.get("error"):
await interaction.followup.send("❌ لم يتم العثور على الفيلم")
return
emb = discord.Embed(
title=d.get("title", "?"),
description=(d.get("overview") or "")[:800],
color=0x3498db,
)
if d.get("poster_path"):
emb.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{d['poster_path']}")
emb.add_field(name="التقييم", value=str(d.get("vote_average", "?")))
emb.add_field(name="المدة", value=f"{d.get('runtime', '?')} دقيقة")
await interaction.followup.send(embed=emb)
@bot.tree.command(name="tv", description="تفاصيل مسلسل")
@app_commands.describe(tv_id="ID المسلسل على TMDB")
async def tv_cmd(interaction: discord.Interaction, tv_id: int):
await interaction.response.defer()
d = get_movie_details(tv_id, "tv")
if not d or d.get("error"):
await interaction.followup.send("❌ لم يتم العثور على المسلسل")
return
emb = discord.Embed(
title=d.get("name", "?"),
description=(d.get("overview") or "")[:800],
color=0x2ecc71,
)
if d.get("poster_path"):
emb.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{d['poster_path']}")
emb.add_field(name="التقييم", value=str(d.get("vote_average", "?")))
emb.add_field(name="المواسم", value=str(d.get("number_of_seasons", "?")))
await interaction.followup.send(embed=emb)
bot.run(DISCORD_TOKEN, log_handler=None)
except ImportError:
print("[BOT] discord.py not installed. Run: pip install discord.py")
except Exception as e:
print(f"[BOT] Failed: {e}")
def _bot_launcher():
global _bot_thread
if _bot_thread and _bot_thread.is_alive():
return
_bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
_bot_thread.start()
if RUN_BOT and os.getenv("WERKZEUG_RUN_MAIN") != "true":
_bot_launcher()
=========================================================
MAIN
=========================================================
if name == "main":
port = int(os.getenv("PORT", 5000))
print(f"""
╔══════════════════════════════════════════════════════════════╗
║ ONYX CINEMA v17.3 - ALL-IN-ONE ║
║ 🎬 أفلام ومسلسلات كاملة - دقة عالية 4K ║
║ TMDB: {'✅' if TMDB_API_KEY else '❌'} OMDb: {'✅' if OMDB_API_KEY else '❌'} Discord: {'✅' if DISCORD_TOKEN else '❌'} ║
║ Port: {port} ║
╚══════════════════════════════════════════════════════════════╝
""")
app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
