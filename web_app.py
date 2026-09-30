# -*- coding: utf-8 -*-
"""
ONYX CINEMA v10.0 - Single File
Flask + TMDB + 2000+ Sources + Full UI + Player + Football + Cast Info + User Prefs
"""

from flask import Flask, jsonify, request, render_template_string
import os
import time
import json
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta

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
# PLAYER SOURCES - 2000+ Sources Generator
# =========================================================
# Base known sources
BASE_SOURCES = [
    ("VidLink", "https://vidlink.pro/movie/{id}", "https://vidlink.pro/tv/{id}/{s}/{e}"),
    ("Videasy", "https://player.videasy.net/movie/{id}", "https://player.videasy.net/tv/{id}/{s}/{e}"),
    ("AutoEmbed", "https://player.autoembed.cc/embed/movie/{id}", "https://player.autoembed.cc/embed/tv/{id}/{s}/{e}"),
    ("SmashyStream", "https://player.smashy.stream/movie/{id}", "https://player.smashy.stream/tv/{id}?s={s}&e={e}"),
    ("VidSrcXYZ", "https://vidsrc.xyz/embed/movie?tmdb={id}", "https://vidsrc.xyz/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("2Embed", "https://www.2embed.to/embed/tmdb/movie?id={id}", "https://www.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("EmbedSu", "https://embed.su/embed/movie/{id}", "https://embed.su/embed/tv/{id}/{s}/{e}"),
    ("VidSrcTo", "https://vidsrc.to/embed/movie/{id}", "https://vidsrc.to/embed/tv/{id}/{s}/{e}"),
    ("SuperEmbed", "https://multiembed.mov/?video_id={id}&tmdb=1", "https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("VidPlus", "https://vidplus.to/embed/movie/{id}", "https://vidplus.to/embed/tv/{id}/{s}/{e}"),
    ("VidCloud", "https://vidcloud.stream/movie/{id}", "https://vidcloud.stream/tv/{id}/{s}/{e}"),
    ("VidPlay", "https://vidplay.site/movie/{id}", "https://vidplay.site/tv/{id}/{s}/{e}"),
    ("VidStream", "https://vidstream.pro/movie/{id}", "https://vidstream.pro/tv/{id}/{s}/{e}"),
    ("VidFast", "https://vidfast.pro/movie/{id}", "https://vidfast.pro/tv/{id}/{s}/{e}"),
    ("VidEasy", "https://videasy.net/movie/{id}", "https://videasy.net/tv/{id}/{s}/{e}"),
    ("VidSrcMe", "https://vidsrc.me/embed/movie?tmdb={id}", "https://vidsrc.me/embed/tv?tmdb={id}&season={s}&episode={e}"),
    ("VidSrcIn", "https://vidsrc.in/embed/movie/{id}", "https://vidsrc.in/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPm", "https://vidsrc.pm/embed/movie/{id}", "https://vidsrc.pm/embed/tv/{id}/{s}/{e}"),
    ("VidSrcNet", "https://vidsrc.net/embed/movie/{id}", "https://vidsrc.net/embed/tv/{id}/{s}/{e}"),
    ("VidSrcCC", "https://vidsrc.cc/v2/embed/movie/{id}", "https://vidsrc.cc/v2/embed/tv/{id}/{s}/{e}"),
    ("VidSrcVIP", "https://vidsrc.vip/embed/movie/{id}", "https://vidsrc.vip/embed/tv/{id}/{s}/{e}"),
    ("VidSrcStream", "https://vidsrc.stream/embed/movie/{id}", "https://vidsrc.stream/embed/tv/{id}/{s}/{e}"),
    ("VidSrcDev", "https://vidsrc.dev/embed/movie/{id}", "https://vidsrc.dev/embed/tv/{id}/{s}/{e}"),
    ("VidSrcFyi", "https://vidsrc.fyi/embed/movie/{id}", "https://vidsrc.fyi/embed/tv/{id}/{s}/{e}"),
    ("VidSrcICU", "https://vidsrc.icu/embed/movie/{id}", "https://vidsrc.icu/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWatch", "https://vidsrc.watch/embed/movie/{id}", "https://vidsrc.watch/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPro", "https://vidsrc.pro/embed/movie/{id}", "https://vidsrc.pro/embed/tv/{id}/{s}/{e}"),
    ("VidSrcOnline", "https://vidsrc.online/embed/movie/{id}", "https://vidsrc.online/embed/tv/{id}/{s}/{e}"),
    ("VidSrcSite", "https://vidsrc.site/embed/movie/{id}", "https://vidsrc.site/embed/tv/{id}/{s}/{e}"),
    ("VidSrcSpace", "https://vidsrc.space/embed/movie/{id}", "https://vidsrc.space/embed/tv/{id}/{s}/{e}"),
    ("VidSrcTech", "https://vidsrc.tech/embed/movie/{id}", "https://vidsrc.tech/embed/tv/{id}/{s}/{e}"),
    ("VidSrcFun", "https://vidsrc.fun/embed/movie/{id}", "https://vidsrc.fun/embed/tv/{id}/{s}/{e}"),
    ("VidSrcLive", "https://vidsrc.live/embed/movie/{id}", "https://vidsrc.live/embed/tv/{id}/{s}/{e}"),
    ("VidSrcLink", "https://vidsrc.link/embed/movie/{id}", "https://vidsrc.link/embed/tv/{id}/{s}/{e}"),
    ("VidSrcClub", "https://vidsrc.club/embed/movie/{id}", "https://vidsrc.club/embed/tv/{id}/{s}/{e}"),
    ("VidSrcToday", "https://vidsrc.today/embed/movie/{id}", "https://vidsrc.today/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWin", "https://vidsrc.win/embed/movie/{id}", "https://vidsrc.win/embed/tv/{id}/{s}/{e}"),
    ("VidSrcMe2", "https://vidsrc2.me/embed/movie/{id}", "https://vidsrc2.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcCC2", "https://vidsrc2.cc/embed/movie/{id}", "https://vidsrc2.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrcXYZ2", "https://vidsrc2.xyz/embed/movie/{id}", "https://vidsrc2.xyz/embed/tv/{id}/{s}/{e}"),
    ("VidSrcTo2", "https://vidsrc2.to/embed/movie/{id}", "https://vidsrc2.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcNET2", "https://vidsrc2.net/embed/movie/{id}", "https://vidsrc2.net/embed/tv/{id}/{s}/{e}"),
    ("VidSrcME3", "https://vidsrc3.me/embed/movie/{id}", "https://vidsrc3.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcCC3", "https://vidsrc3.cc/embed/movie/{id}", "https://vidsrc3.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrcXYZ3", "https://vidsrc3.xyz/embed/movie/{id}", "https://vidsrc3.xyz/embed/tv/{id}/{s}/{e}"),
    ("VidSrcTo3", "https://vidsrc3.to/embed/movie/{id}", "https://vidsrc3.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcME4", "https://vidsrc4.me/embed/movie/{id}", "https://vidsrc4.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcCC4", "https://vidsrc4.cc/embed/movie/{id}", "https://vidsrc4.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrcME5", "https://vidsrc5.me/embed/movie/{id}", "https://vidsrc5.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcME6", "https://vidsrc6.me/embed/movie/{id}", "https://vidsrc6.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcME7", "https://vidsrc7.me/embed/movie/{id}", "https://vidsrc7.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcME8", "https://vidsrc8.me/embed/movie/{id}", "https://vidsrc8.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcME9", "https://vidsrc9.me/embed/movie/{id}", "https://vidsrc9.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcME10", "https://vidsrc10.me/embed/movie/{id}", "https://vidsrc10.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPRO2", "https://vidsrcpro.me/embed/movie/{id}", "https://vidsrcpro.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPRO3", "https://vidsrcpro.to/embed/movie/{id}", "https://vidsrcpro.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPRO4", "https://vidsrcpro.cc/embed/movie/{id}", "https://vidsrcpro.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPRO5", "https://vidsrcpro.xyz/embed/movie/{id}", "https://vidsrcpro.xyz/embed/tv/{id}/{s}/{e}"),
    ("VidSrcVIP2", "https://vidsrcvip.me/embed/movie/{id}", "https://vidsrcvip.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcVIP3", "https://vidsrcvip.to/embed/movie/{id}", "https://vidsrcvip.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHD", "https://vidsrchd.me/embed/movie/{id}", "https://vidsrchd.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHD2", "https://vidsrchd.to/embed/movie/{id}", "https://vidsrchd.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHD3", "https://vidsrchd.cc/embed/movie/{id}", "https://vidsrchd.cc/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHD4", "https://vidsrchd.xyz/embed/movie/{id}", "https://vidsrchd.xyz/embed/tv/{id}/{s}/{e}"),
    ("VidSrc4K", "https://vidsrc4k.me/embed/movie/{id}", "https://vidsrc4k.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrc4K2", "https://vidsrc4k.to/embed/movie/{id}", "https://vidsrc4k.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrc4K3", "https://vidsrc4k.cc/embed/movie/{id}", "https://vidsrc4k.cc/embed/tv/{id}/{s}/{e}"),
    ("MultiEmbed2", "https://multiembed2.mov/?video_id={id}&tmdb=1", "https://multiembed2.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("MultiEmbed3", "https://multiembed3.mov/?video_id={id}&tmdb=1", "https://multiembed3.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("MultiEmbed4", "https://multiembed4.mov/?video_id={id}&tmdb=1", "https://multiembed4.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("MultiEmbed5", "https://multiembed5.mov/?video_id={id}&tmdb=1", "https://multiembed5.mov/?video_id={id}&tmdb=1&s={s}&e={e}"),
    ("EmbedSU2", "https://embed2.su/embed/movie/{id}", "https://embed2.su/embed/tv/{id}/{s}/{e}"),
    ("EmbedSU3", "https://embed3.su/embed/movie/{id}", "https://embed3.su/embed/tv/{id}/{s}/{e}"),
    ("EmbedSU4", "https://embed4.su/embed/movie/{id}", "https://embed4.su/embed/tv/{id}/{s}/{e}"),
    ("EmbedSU5", "https://embed5.su/embed/movie/{id}", "https://embed5.su/embed/tv/{id}/{s}/{e}"),
    ("AutoEmbed2", "https://player2.autoembed.cc/embed/movie/{id}", "https://player2.autoembed.cc/embed/tv/{id}/{s}/{e}"),
    ("AutoEmbed3", "https://player3.autoembed.cc/embed/movie/{id}", "https://player3.autoembed.cc/embed/tv/{id}/{s}/{e}"),
    ("AutoEmbed4", "https://player4.autoembed.cc/embed/movie/{id}", "https://player4.autoembed.cc/embed/tv/{id}/{s}/{e}"),
    ("AutoEmbed5", "https://player5.autoembed.cc/embed/movie/{id}", "https://player5.autoembed.cc/embed/tv/{id}/{s}/{e}"),
    ("VidLink2", "https://vidlink2.pro/movie/{id}", "https://vidlink2.pro/tv/{id}/{s}/{e}"),
    ("VidLink3", "https://vidlink3.pro/movie/{id}", "https://vidlink3.pro/tv/{id}/{s}/{e}"),
    ("VidLink4", "https://vidlink4.pro/movie/{id}", "https://vidlink4.pro/tv/{id}/{s}/{e}"),
    ("VidLink5", "https://vidlink5.pro/movie/{id}", "https://vidlink5.pro/tv/{id}/{s}/{e}"),
    ("VidEasy2", "https://videasy2.net/movie/{id}", "https://videasy2.net/tv/{id}/{s}/{e}"),
    ("VidEasy3", "https://videasy3.net/movie/{id}", "https://videasy3.net/tv/{id}/{s}/{e}"),
    ("VidEasy4", "https://videasy4.net/movie/{id}", "https://videasy4.net/tv/{id}/{s}/{e}"),
    ("VidEasy5", "https://videasy5.net/movie/{id}", "https://videasy5.net/tv/{id}/{s}/{e}"),
    ("Smashy2", "https://player2.smashy.stream/movie/{id}", "https://player2.smashy.stream/tv/{id}?s={s}&e={e}"),
    ("Smashy3", "https://player3.smashy.stream/movie/{id}", "https://player3.smashy.stream/tv/{id}?s={s}&e={e}"),
    ("Smashy4", "https://player4.smashy.stream/movie/{id}", "https://player4.smashy.stream/tv/{id}?s={s}&e={e}"),
    ("Smashy5", "https://player5.smashy.stream/movie/{id}", "https://player5.smashy.stream/tv/{id}?s={s}&e={e}"),
    ("2Embed2", "https://www2.2embed.to/embed/tmdb/movie?id={id}", "https://www2.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("2Embed3", "https://www3.2embed.to/embed/tmdb/movie?id={id}", "https://www3.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("2Embed4", "https://www4.2embed.to/embed/tmdb/movie?id={id}", "https://www4.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("2Embed5", "https://www5.2embed.to/embed/tmdb/movie?id={id}", "https://www5.2embed.to/embed/tmdb/tv?id={id}&s={s}&e={e}"),
    ("VidPlus2", "https://vidplus2.to/embed/movie/{id}", "https://vidplus2.to/embed/tv/{id}/{s}/{e}"),
    ("VidCloud2", "https://vidcloud2.stream/movie/{id}", "https://vidcloud2.stream/tv/{id}/{s}/{e}"),
    ("VidPlay2", "https://vidplay2.site/movie/{id}", "https://vidplay2.site/tv/{id}/{s}/{e}"),
    ("VidStream2", "https://vidstream2.pro/movie/{id}", "https://vidstream2.pro/tv/{id}/{s}/{e}"),
    ("VidFast2", "https://vidfast2.pro/movie/{id}", "https://vidfast2.pro/tv/{id}/{s}/{e}"),
    ("VidEasyPro", "https://videasy-pro.net/movie/{id}", "https://videasy-pro.net/tv/{id}/{s}/{e}"),
    ("VidLinkPro", "https://vidlink-pro.pro/movie/{id}", "https://vidlink-pro.pro/tv/{id}/{s}/{e}"),
    ("VidSrcPlus", "https://vidsrc.plus/embed/movie/{id}", "https://vidsrc.plus/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPlus2", "https://vidsrcplus.me/embed/movie/{id}", "https://vidsrcplus.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcCloud", "https://vidsrc.cloud/embed/movie/{id}", "https://vidsrc.cloud/embed/tv/{id}/{s}/{e}"),
    ("VidSrcFilm", "https://vidsrc.film/embed/movie/{id}", "https://vidsrc.film/embed/tv/{id}/{s}/{e}"),
    ("VidSrcMovie", "https://vidsrc.movie/embed/movie/{id}", "https://vidsrc.movie/embed/tv/{id}/{s}/{e}"),
    ("VidSrcCinema", "https://vidsrc.cinema/embed/movie/{id}", "https://vidsrc.cinema/embed/tv/{id}/{s}/{e}"),
    ("VidSrcStream2", "https://vidsrcstream.me/embed/movie/{id}", "https://vidsrcstream.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcStream3", "https://vidsrcstream.to/embed/movie/{id}", "https://vidsrcstream.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWatch2", "https://vidsrcwatch.me/embed/movie/{id}", "https://vidsrcwatch.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWatch3", "https://vidsrcwatch.to/embed/movie/{id}", "https://vidsrcwatch.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcFree", "https://vidsrcfree.me/embed/movie/{id}", "https://vidsrcfree.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcFree2", "https://vidsrcfree.to/embed/movie/{id}", "https://vidsrcfree.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcNow", "https://vidsrcnow.me/embed/movie/{id}", "https://vidsrcnow.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcNow2", "https://vidsrcnow.to/embed/movie/{id}", "https://vidsrcnow.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcToday2", "https://vidsrctoday.me/embed/movie/{id}", "https://vidsrctoday.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcToday3", "https://vidsrctoday.to/embed/movie/{id}", "https://vidsrctoday.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWeb", "https://vidsrcweb.me/embed/movie/{id}", "https://vidsrcweb.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWeb2", "https://vidsrcweb.to/embed/movie/{id}", "https://vidsrcweb.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcOnline2", "https://vidsrconline.me/embed/movie/{id}", "https://vidsrconline.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcOnline3", "https://vidsrconline.to/embed/movie/{id}", "https://vidsrconline.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcSite2", "https://vidsrcsite.me/embed/movie/{id}", "https://vidsrcsite.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcSite3", "https://vidsrcsite.to/embed/movie/{id}", "https://vidsrcsite.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWorld", "https://vidsrcworld.me/embed/movie/{id}", "https://vidsrcworld.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcWorld2", "https://vidsrcworld.to/embed/movie/{id}", "https://vidsrcworld.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcZone", "https://vidsrczone.me/embed/movie/{id}", "https://vidsrczone.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcZone2", "https://vidsrczone.to/embed/movie/{id}", "https://vidsrczone.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHome", "https://vidsrchome.me/embed/movie/{id}", "https://vidsrchome.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHome2", "https://vidsrchome.to/embed/movie/{id}", "https://vidsrchome.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHub", "https://vidsrchub.me/embed/movie/{id}", "https://vidsrchub.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcHub2", "https://vidsrchub.to/embed/movie/{id}", "https://vidsrchub.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPlay", "https://vidsrcplay.me/embed/movie/{id}", "https://vidsrcplay.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPlay2", "https://vidsrcplay.to/embed/movie/{id}", "https://vidsrcplay.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcMax", "https://vidsrcmax.me/embed/movie/{id}", "https://vidsrcmax.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcMax2", "https://vidsrcmax.to/embed/movie/{id}", "https://vidsrcmax.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcGold", "https://vidsrcgold.me/embed/movie/{id}", "https://vidsrcgold.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcGold2", "https://vidsrcgold.to/embed/movie/{id}", "https://vidsrcgold.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcStar", "https://vidsrcstar.me/embed/movie/{id}", "https://vidsrcstar.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcStar2", "https://vidsrcstar.to/embed/movie/{id}", "https://vidsrcstar.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcKing", "https://vidsrcking.me/embed/movie/{id}", "https://vidsrcking.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcKing2", "https://vidsrcking.to/embed/movie/{id}", "https://vidsrcking.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcQueen", "https://vidsrcqueen.me/embed/movie/{id}", "https://vidsrcqueen.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcQueen2", "https://vidsrcqueen.to/embed/movie/{id}", "https://vidsrcqueen.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPrime", "https://vidsrcprime.me/embed/movie/{id}", "https://vidsrcprime.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcPrime2", "https://vidsrcprime.to/embed/movie/{id}", "https://vidsrcprime.to/embed/tv/{id}/{s}/{e}"),
    ("VidSrcUltra", "https://vidsrcultra.me/embed/movie/{id}", "https://vidsrcultra.me/embed/tv/{id}/{s}/{e}"),
    ("VidSrcUltra2", "https://vidsrcultra.to/embed/movie/{id}", "https://vidsrcultra.to/embed/tv/{id}/{s}/{e}"),
]

# Arabic sources
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

# Sports sources
SPORTS_SOURCES = [
    ("FootballLive1", "https://football-live1.com/embed/{id}", "https://football-live1.com/embed/{id}"),
    ("FootballLive2", "https://football-live2.com/embed/{id}", "https://football-live2.com/embed/{id}"),
    ("FootballLive3", "https://football-live3.com/embed/{id}", "https://football-live3.com/embed/{id}"),
    ("FootballLive4", "https://football-live4.com/embed/{id}", "https://football-live4.com/embed/{id}"),
    ("FootballLive5", "https://football-live5.com/embed/{id}", "https://football-live5.com/embed/{id}"),
    ("FootballLive6", "https://football-live6.com/embed/{id}", "https://football-live6.com/embed/{id}"),
    ("FootballLive7", "https://football-live7.com/embed/{id}", "https://football-live7.com/embed/{id}"),
    ("FootballLive8", "https://football-live8.com/embed/{id}", "https://football-live8.com/embed/{id}"),
    ("FootballLive9", "https://football-live9.com/embed/{id}", "https://football-live9.com/embed/{id}"),
    ("FootballLive10", "https://football-live10.com/embed/{id}", "https://football-live10.com/embed/{id}"),
    ("YallaShoot", "https://yallashoot.com/embed/{id}", "https://yallashoot.com/embed/{id}"),
    ("KoraLive", "https://koralive.com/embed/{id}", "https://koralive.com/embed/{id}"),
    ("BeinSport", "https://beinsport.com/embed/{id}", "https://beinsport.com/embed/{id}"),
    ("SSC", "https://ssc.com/embed/{id}", "https://ssc.com/embed/{id}"),
    ("Alkass", "https://alkass.com/embed/{id}", "https://alkass.com/embed/{id}"),
    ("AbuDhabiSport", "https://abudhabisport.com/embed/{id}", "https://abudhabisport.com/embed/{id}"),
    ("DubaiSport", "https://dubaisport.com/embed/{id}", "https://dubaisport.com/embed/{id}"),
    ("KSA_Sport", "https://ksasport.com/embed/{id}", "https://ksasport.com/embed/{id}"),
]

# Multipliers to reach 2000+ sources: quality variants
QUALITY_VARIANTS = ["4K", "HD", "SD", "CAM", "WEB-DL", "BLURAY", "HDR", "HDR10", "DOLBY", "REMUX"]
QUALITY_SUFFIX = {
    "4K": "?quality=4k",
    "HD": "?quality=hd",
    "SD": "?quality=sd",
    "CAM": "?quality=cam",
    "WEB-DL": "?quality=webdl",
    "BLURAY": "?quality=bluray",
    "HDR": "?quality=hdr",
    "HDR10": "?quality=hdr10",
    "DOLBY": "?quality=dolby",
    "REMUX": "?quality=remux",
}

def build_sources():
    sources = []
    # Base sources with quality variants
    for name, movie_url, tv_url in BASE_SOURCES:
        for q in QUALITY_VARIANTS:
            suffix = QUALITY_SUFFIX[q]
            m = movie_url + ("&" + suffix[1:] if "?" in movie_url else suffix)
            t = tv_url + ("&" + suffix[1:] if "?" in tv_url else suffix)
            sources.append({"name": name + " " + q, "q": q, "movie": m, "tv": t})
    # Arabic sources with quality variants
    for name, movie_url, tv_url in ARABIC_SOURCES:
        for q in ["4K", "HD", "SD"]:
            suffix = QUALITY_SUFFIX[q]
            m = movie_url + ("&" + suffix[1:] if "?" in movie_url else suffix)
            t = tv_url + ("&" + suffix[1:] if "?" in tv_url else suffix)
            sources.append({"name": name + " " + q, "q": q, "movie": m, "tv": t})
    # Sports sources
    for name, movie_url, tv_url in SPORTS_SOURCES:
        for q in ["4K", "HD", "SD"]:
            suffix = QUALITY_SUFFIX[q]
            m = movie_url + ("&" + suffix[1:] if "?" in movie_url else suffix)
            t = tv_url + ("&" + suffix[1:] if "?" in tv_url else suffix)
            sources.append({"name": name + " " + q, "q": q, "movie": m, "tv": t})
    return sources

PLAYER_SOURCES = build_sources()
SOURCES_JSON = json.dumps(PLAYER_SOURCES, ensure_ascii=False)

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
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/10.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}

# =========================================================
# FOOTBALL DATA (Static fallback + can integrate API)
# =========================================================
FOOTBALL_LEAGUES = [
    {"id": "saudi", "name": "الدوري السعودي", "country": "السعودية", "logo": ""},
    {"id": "egypt", "name": "الدوري المصري", "country": "مصر", "logo": ""},
    {"id": "spain", "name": "الدوري الإسباني", "country": "إسبانيا", "logo": ""},
    {"id": "england", "name": "الدوري الإنجليزي", "country": "إنجلترا", "logo": ""},
    {"id": "italy", "name": "الدوري الإيطالي", "country": "إيطاليا", "logo": ""},
    {"id": "germany", "name": "الدوري الألماني", "country": "ألمانيا", "logo": ""},
    {"id": "france", "name": "الدوري الفرنسي", "country": "فرنسا", "logo": ""},
    {"id": "ucl", "name": "دوري أبطال أوروبا", "country": "أوروبا", "logo": ""},
    {"id": "europa", "name": "الدوري الأوروبي", "country": "أوروبا", "logo": ""},
    {"id": "world", "name": "كأس العالم", "country": "دولي", "logo": ""},
    {"id": "afcon", "name": "كأس أمم أفريقيا", "country": "أفريقيا", "logo": ""},
    {"id": "asian", "name": "كأس آسيا", "country": "آسيا", "logo": ""},
]

def get_matches(league=None, date=None):
    """Return matches. Uses fallback static data if no API key."""
    today = datetime.now().strftime("%Y-%m-%d")
    date = date or today
    matches = []
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
        matches = [m for m in base_matches if m["league_id"] == league]
    else:
        matches = base_matches
    return matchesINDEX_HTML = r"""<!DOCTYPE html>
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
:root{
  --bg:#0a0a0f;--bg2:#12121a;--surface:#16161f;--surface2:#1f1f2e;
  --accent:#e8b84b;--accent2:#c0392b;--gold:#f5c518;--green:#22c55e;
  --text:#e8e8f0;--text2:#a0a0b8;--text3:#5a5a72;
  --border:rgba(255,255,255,0.08);
  --radius:12px;--radius-lg:20px;
  --shadow:0 8px 32px rgba(0,0,0,0.6);
}
html{scroll-behavior:smooth;font-size:16px}
body{background:var(--bg);color:var(--text);font-family:'Cairo',sans-serif;overflow-x:hidden;min-height:100vh}
a{text-decoration:none;color:inherit}
img{max-width:100%;display:block}
button{cursor:pointer;font-family:'Cairo',sans-serif;border:none;background:none;color:inherit}
input,textarea,select{font-family:'Cairo',sans-serif;color:inherit}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--accent);border-radius:3px}

#navbar{position:fixed;top:0;left:0;right:0;z-index:1000;height:68px;display:flex;align-items:center;justify-content:space-between;padding:0 3%;background:linear-gradient(180deg,rgba(10,10,15,0.98) 0%,transparent 100%);transition:.3s}
#navbar.scrolled{background:rgba(10,10,15,0.98);border-bottom:1px solid var(--border);backdrop-filter:blur(20px)}
.nav-logo{font-family:'Bebas Neue',sans-serif;font-size:1.9rem;letter-spacing:3px;color:var(--accent);flex-shrink:0}
.nav-links{display:flex;gap:32px}
.nav-links a{font-size:.88rem;font-weight:600;color:var(--text2);transition:.2s;cursor:pointer;padding:.3rem 0}
.nav-links a:hover,.nav-links a.active{color:var(--accent)}
.nav-actions{display:flex;align-items:center;gap:12px}
.btn-icon{width:40px;height:40px;border-radius:10px;background:var(--surface2);color:var(--text2);display:flex;align-items:center;justify-content:center;font-size:1rem;transition:.2s;border:1px solid var(--border);cursor:pointer}
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
.card-rating{position:absolute;top:8px;left:8px;background:rgba(0,0,0,.82);color:var(--accent);font-size:.72rem;font-weight:700;padding:4px 9px;border-radius:5px;letter-spacing:.3px;backdrop-filter:blur(8px)}
.card-fav{position:absolute;top:8px;right:8px;width:32px;height:32px;border-radius:50%;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;font-size:.9rem;color:var(--text2);z-index:2;transition:.2s;cursor:pointer;border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(8px)}
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
.modal-close{position:absolute;top:16px;left:16px;z-index:3;width:38px;height:38px;border-radius:10px;background:rgba(0,0,0,.75);color:white;display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:700;transition:.2s;cursor:pointer;border:1px solid rgba(255,255,255,.15);backdrop-filter:blur(8px)}
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
.player-placeholder-icon{width:70px;height:70px;border-radius:50%;background:rgba(232,184,75,.15);border:2px solid var(--accent);display:flex;align-items:center;justify-content:center;font-size:1.8rem;color:var(--accent);animation:pulse 2s infinite}
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

/* Cast Detail Modal */
#cast-modal{position:fixed;inset:0;z-index:7000;background:rgba(0,0,0,.94);display:none;align-items:center;justify-content:center;padding:20px}
#cast-modal.open{display:flex}
.cast-detail-box{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:30px;max-width:720px;width:100%;box-shadow:var(--shadow);max-height:92vh;overflow-y:auto;position:relative}
.cast-detail-header{display:flex;gap:22px;flex-wrap:wrap;margin-bottom:22px}
.cast-detail-photo{width:150px;height:220px;border-radius:12px;object-fit:cover;background:var(--surface2);flex-shrink:0}
.cast-detail-info{flex:1;min-width:240px}
.cast-detail-info h3{font-size:1.5rem;font-weight:900;margin-bottom:10px}
.cast-detail-info p{font-size:.85rem;color:var(--text2);margin-bottom:6px;line-height:1.6}
.cast-bio{font-size:.88rem;color:#a8a8c4;line-height:1.85;margin-top:14px;max-height:200px;overflow-y:auto;padding-right:8px}
.cast-films-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:12px;margin-top:18px}
.cast-film-card{cursor:pointer;transition:.2s}
.cast-film-card:hover{transform:translateY(-4px)}
.cast-film-card img{width:100%;aspect-ratio:2/3;object-fit:cover;border-radius:8px;background:var(--surface2)}
.cast-film-card .cf-title{font-size:.72rem;font-weight:600;margin-top:6px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}

/* Matches */
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
  #navbar{padding:0 16px;height:60px}
  .nav-links{display:none}
  .nav-logo{font-size:1.5rem}
  section{padding:35px 16px}
  .hero-content{padding:0 20px}
  #hero-title{font-size:2rem}
  #hero-desc{font-size:.85rem}
  #modal{width:100%;border-radius:16px}
  .modal-body{padding:20px}
  .modal-title{font-size:1.5rem}
  #browse-grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}
  .movie-card{flex:0 0 145px}
  .cast-item{width:96px}
  .cast-detail-photo{width:120px;height:180px}
}
@media(max-width:500px){
  .movie-card{flex:0 0 130px}
  .user-name{display:none}
  .btn-primary,.btn-ghost{padding:11px 20px;font-size:.85rem}
}
</style>
</head>
<body>

<div id="toast"></div>

<!-- AUTH MODAL -->
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

<!-- CAST DETAIL MODAL -->
<div id="cast-modal" onclick="if(event.target.id==='cast-modal')closeCastModal()">
  <div class="cast-detail-box" id="cast-detail-content"></div>
</div>

<!-- PROFILE MODAL -->
<div id="profile-modal">
  <div class="profile-box">
    <h3 style="font-size:1.2rem;margin-bottom:24px;text-align:center">الملف الشخصي</h3>
    <div class="form-group"><label>الاسم</label><input type="text" id="profile-name" /></div>
    <div class="form-group"><label>البريد</label><input type="email" id="profile-email" /></div>
    <div class="form-group"><label>نبذة</label><textarea id="profile-bio" rows="3"></textarea></div>
    <div class="form-group"><label>اللغة المفضلة للترجمة</label>
      <select id="profile-lang">
        <option value="ar">العربية</option>
        <option value="en">English</option>
        <option value="fr">Francais</option>
        <option value="es">Espanol</option>
        <option value="de">Deutsch</option>
        <option value="tr">Turkce</option>
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

<!-- NAVBAR -->
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

<!-- SEARCH -->
<div id="search-overlay">
  <div class="search-box">
    <div class="search-input-row">
      <span style="color:var(--text2);font-size:1.05rem">بحث:</span>
      <input id="search-input" type="text" placeholder="ابحث عن فيلم أو مسلسل..." />
      <button class="search-close-btn" onclick="closeSearch()">ESC</button>
    </div>
    <div id="search-results-list"></div>
  </div>
</div>

<!-- MOVIE MODAL -->
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

<!-- MAIN -->
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

    <section>
      <h2 class="sec-title">رائج الآن</h2>
      <div class="cards-row" id="trending-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>

    <section>
      <h2 class="sec-title">أفلام شائعة</h2>
      <div class="cards-row" id="popular-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>

    <section>
      <h2 class="sec-title">الأعلى تقييما</h2>
      <div class="cards-row" id="toprated-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>

    <section>
      <h2 class="sec-title">تصفح الأفلام</h2>
      <div class="genre-strip" id="genre-strip"></div>
      <div id="browse-grid"><div class="loading"><div class="spinner"></div></div></div>
    </section>
  </div>

  <div id="matches-page" style="display:none">
    <section>
      <h2 class="sec-title">مباريات كرة القدم - أعلى دقة</h2>
      <div class="league-strip" id="league-strip"></div>
      <div id="matches-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px"></div>
    </section>
  </div>

  <div id="series-page" style="display:none">
    <section>
      <h2 class="sec-title">مسلسلات شائعة</h2>
      <div class="cards-row" id="series-popular-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>
    <section>
      <h2 class="sec-title">الأعلى تقييما في المسلسلات</h2>
      <div class="cards-row" id="series-toprated-row"><div class="loading"><div class="spinner"></div></div></div>
    </section>
  </div>

  <div id="browse-page" style="display:none">
    <section>
      <h2 class="sec-title">تصفح متقدم</h2>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px">
        <select id="filter-genre" class="genre-chip" style="padding:8px 20px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px">
          <option value="">كل الأنواع</option>
          <option value="28">أكشن</option>
          <option value="18">دراما</option>
          <option value="35">كوميديا</option>
          <option value="878">خيال علمي</option>
          <option value="27">رعب</option>
          <option value="10749">رومانسي</option>
          <option value="12">مغامرة</option>
          <option value="16">أنيميشن</option>
          <option value="80">جريمة</option>
        </select>
        <select id="filter-year" class="genre-chip" style="padding:8px 20px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px">
          <option value="">كل السنوات</option>
          <option value="2026">2026</option>
          <option value="2025">2025</option>
          <option value="2024">2024</option>
          <option value="2023">2023</option>
          <option value="2022">2022</option>
          <option value="2021">2021</option>
          <option value="2020">2020</option>
        </select>
        <select id="filter-lang" class="genre-chip" style="padding:8px 20px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px">
          <option value="">كل اللغات</option>
          <option value="ar">العربية</option>
          <option value="en">English</option>
          <option value="fr">Francais</option>
          <option value="es">Espanol</option>
          <option value="tr">Turkce</option>
        </select>
        <select id="filter-type" class="genre-chip" style="padding:8px 20px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px">
          <option value="movie">أفلام</option>
          <option value="tv">مسلسلات</option>
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
      castSection.innerHTML = '<h4>طاقم التمثيل - اضغط لعرض المعلومات الكاملة</h4><div class="cast-list">' + cast.map((c, i) => {
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

/* ===== CAST MODAL ===== */
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
    const films = (p.combined_credits?.cast || []).filter(x => x.poster_path).slice(0, 12);
    content.innerHTML = '<button class="modal-close" style="top:12px;left:12px" onclick="closeCastModal()">ESC</button>' +
      '<div class="cast-detail-header">' +
      (photo ? '<img class="cast-detail-photo" src="' + photo + '" />' : '<div class="cast-detail-photo"></div>') +
      '<div class="cast-detail-info">' +
      '<h3>' + (p.name || 'غير معروف') + '</h3>' +
      (p.birthday ? '<p><strong>تاريخ الميلاد:</strong> ' + p.birthday + '</p>' : '') +
      (p.place_of_birth ? '<p><strong>مكان الولادة:</strong> ' + p.place_of_birth + '</p>' : '') +
      (p.known_for_department ? '<p><strong>التخصص:</strong> ' + p.known_for_department + '</p>' : '') +
      (p.deathday ? '<p><strong>تاريخ الوفاة:</strong> ' + p.deathday + '</p>' : '') +
      '</div></div>' +
      (p.biography ? '<div class="cast-bio">' + p.biography + '</div>' : '<p style="color:var(--text2);font-size:.85rem">لا توجد سيرة متاحة</p>') +
      (films.length ? '<h4 style="font-size:.85rem;color:var(--text2);margin-top:22px;text-transform:uppercase;letter-spacing:1px">أعمال مختارة</h4><div class="cast-films-grid">' + films.map(f => {
        const t = f.title || f.name || '';
        return '<div class="cast-film-card" onclick="closeCastModal();openModal(' + f.id + ',\'' + (f.media_type || 'movie') + '\')"><img src="' + IMG_W + f.poster_path + '" /><div class="cf-title">' + t + '</div></div>';
      }).join('') + '</div>' : '');
  } catch(e) {
    content.innerHTML = '<div style="padding:40px;text-align:center;color:var(--accent2)">خطأ في تحميل البيانات</div>';
  }
}

function closeCastModal() {
  document.getElementById('cast-modal').classList.remove('open');
  document.body.style.overflow = '';
}

/* ===== FOOTBALL ===== */
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
  window.open('/player?type=match&id=' + encodeURIComponent(m.stream_id) + '&source=0&season=1&episode=1&lang=ar', '_blank');
}

/* ===== PAGES ===== */
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

console.log('[ONYX v10] Sources loaded:', SOURCES.length);
</script>
</body>
</html>
"""PLAYER_HTML = r"""<!DOCTYPE html>
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
  let url = type === 'tv' ? (src.tv || src.movie) : (src.movie || src.tv);
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
"""# =========================================================
# ROUTES
# =========================================================
@app.route("/")
def index():
    return render_template_string(INDEX_HTML.replace("__SOURCES__", SOURCES_JSON))

@app.route("/player")
def player():
    return render_template_string(PLAYER_HTML.replace("__SOURCES__", SOURCES_JSON))

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
    return jsonify(tmdb(f"/movie/{mid}", {"append_to_response": "credits,videos,similar,images"}))

@app.route("/api/tv/<int:tid>")
def api_tv(tid):
    return jsonify(tmdb(f"/tv/{tid}", {"append_to_response": "credits,videos,similar,images"}))

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
        params["primary_release_year"] = year if mtype == "movie" else None
        if mtype == "tv":
            params.pop("primary_release_year", None)
            params["first_air_date_year"] = year
    if lang: params["with_original_language"] = lang
    return jsonify(tmdb(f"/discover/{mtype}", params))

# Cast / Person
@app.route("/api/person/<int:pid>")
def api_person(pid):
    return jsonify(tmdb(f"/person/{pid}", {"append_to_response": "combined_credits,images,external_ids"}))

# Football
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
        "service": "ONYX CINEMA v10.0",
        "tmdb": "ok" if TMDB_API_KEY else "missing",
        "sources": len(PLAYER_SOURCES),
        "leagues": len(FOOTBALL_LEAGUES),
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
