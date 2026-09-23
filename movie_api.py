# -*- coding: utf-8 -*-
"""🎬 ONYX MOVIE API — TMDB Wrapper"""

import os
import json
import urllib.parse
import urllib.request
from typing import Optional, List, Dict

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"

LANG = "ar"  # اللغة العربية


def _tmdb_get(endpoint: str, params: dict = None) -> dict:
    """طلب GET إلى TMDB"""
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY missing"}
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    params["language"] = params.get("language", LANG)
    url = f"{TMDB_BASE}{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════
# 🎬 دوال جلب الأفلام
# ══════════════════════════════════════════════════════════

def get_trending(media_type: str = "all", time_window: str = "week") -> List[Dict]:
    """الأكثر رواجاً"""
    data = _tmdb_get(f"/trending/{media_type}/{time_window}")
    return _format_results(data.get("results", []))


def get_popular(media_type: str = "movie", page: int = 1) -> List[Dict]:
    """الأكثر شعبية"""
    data = _tmdb_get(f"/{media_type}/popular", {"page": page})
    return _format_results(data.get("results", []))


def get_top_rated(media_type: str = "movie", page: int = 1) -> List[Dict]:
    """الأعلى تقييماً"""
    data = _tmdb_get(f"/{media_type}/top_rated", {"page": page})
    return _format_results(data.get("results", []))


def get_now_playing(page: int = 1) -> List[Dict]:
    """في السينما الآن"""
    data = _tmdb_get("/movie/now_playing", {"page": page})
    return _format_results(data.get("results", []))


def get_upcoming(page: int = 1) -> List[Dict]:
    """قادم قريباً"""
    data = _tmdb_get("/movie/upcoming", {"page": page})
    return _format_results(data.get("results", []))


def get_by_genre(genre_id: int, media_type: str = "movie", page: int = 1) -> List[Dict]:
    """حسب التصنيف"""
    data = _tmdb_get(f"/discover/{media_type}", {
        "with_genres": genre_id,
        "page": page,
        "sort_by": "popularity.desc",
    })
    return _format_results(data.get("results", []))


def search_multi(query: str, page: int = 1) -> List[Dict]:
    """بحث"""
    data = _tmdb_get("/search/multi", {
        "query": query,
        "page": page,
        "include_adult": "false",
    })
    return _format_results(data.get("results", []))


def get_movie_details(movie_id: int, media_type: str = "movie") -> Optional[Dict]:
    """تفاصيل فيلم/مسلسل"""
    data = _tmdb_get(f"/{media_type}/{movie_id}", {
        "append_to_response": "videos,credits,similar,recommendations",
    })
    if "error" in data:
        return None
    return _format_details(data)


def get_season_details(tv_id: int, season_num: int) -> Optional[Dict]:
    """تفاصيل موسم مسلسل"""
    data = _tmdb_get(f"/tv/{tv_id}/season/{season_num}")
    if "error" in data:
        return None
    return data


# ══════════════════════════════════════════════════════════
# 🎨 تنسيق النتائج
# ══════════════════════════════════════════════════════════

def _format_results(results: List[Dict]) -> List[Dict]:
    """تنسيق نتائج TMDB"""
    formatted = []
    for r in results:
        if not r.get("id"):
            continue
        media_type = r.get("media_type", "movie")
        title = r.get("title") or r.get("name", "?")
        date = r.get("release_date") or r.get("first_air_date") or ""
        poster = r.get("poster_path")
        backdrop = r.get("backdrop_path")
        
        formatted.append({
            "id": r["id"],
            "media_type": media_type,
            "title": title,
            "original_title": r.get("original_title") or r.get("original_name", ""),
            "overview": r.get("overview", ""),
            "year": date[:4] if date else "",
            "rating": round(r.get("vote_average", 0), 1),
            "vote_count": r.get("vote_count", 0),
            "poster": f"{TMDB_IMG}/w500{poster}" if poster else "",
            "backdrop": f"{TMDB_IMG}/w1280{backdrop}" if backdrop else "",
            "genre_ids": r.get("genre_ids", []),
            "popularity": r.get("popularity", 0),
        })
    return formatted


def _format_details(data: Dict) -> Dict:
    """تنسيق تفاصيل فيلم"""
    media_type = "movie" if data.get("title") else "tv"
    title = data.get("title") or data.get("name", "?")
    date = data.get("release_date") or data.get("first_air_date") or ""
    poster = data.get("poster_path")
    backdrop = data.get("backdrop_path")
    
    # الفيديوهات (تريلر)
    trailer = None
    for v in data.get("videos", {}).get("results", []):
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            trailer = f"https://www.youtube.com/embed/{v['key']}"
            break
    
    # الطاقم
    cast = []
    for c in data.get("credits", {}).get("cast", [])[:10]:
        cast.append({
            "name": c.get("name"),
            "character": c.get("character"),
            "photo": f"{TMDB_IMG}/w200{c['profile_path']}" if c.get("profile_path") else "",
        })
    
    # المواسم للمسلسلات
    seasons = []
    if media_type == "tv":
        for s in data.get("seasons", []):
            seasons.append({
                "season_number": s.get("season_number"),
                "name": s.get("name"),
                "episode_count": s.get("episode_count"),
                "poster": f"{TMDB_IMG}/w300{s['poster_path']}" if s.get("poster_path") else "",
            })
    
    # مشابه
    similar = _format_results(data.get("similar", {}).get("results", [])[:12])
    
    return {
        "id": data["id"],
        "media_type": media_type,
        "title": title,
        "original_title": data.get("original_title") or data.get("original_name", ""),
        "overview": data.get("overview", ""),
        "tagline": data.get("tagline", ""),
        "year": date[:4] if date else "",
        "release_date": date,
        "rating": round(data.get("vote_average", 0), 1),
        "vote_count": data.get("vote_count", 0),
        "runtime": data.get("runtime") or (data.get("episode_run_time", [0])[0] if data.get("episode_run_time") else 0),
        "poster": f"{TMDB_IMG}/w500{poster}" if poster else "",
        "backdrop": f"{TMDB_IMG}/w1280{backdrop}" if backdrop else "",
        "genres": [{"id": g["id"], "name": g["name"]} for g in data.get("genres", [])],
        "status": data.get("status", ""),
        "trailer": trailer,
        "cast": cast,
        "seasons": seasons,
        "similar": similar,
    }


# ══════════════════════════════════════════════════════════
# 🎭 التصنيفات
# ══════════════════════════════════════════════════════════

GENRES_MOVIE = {
    28: "أكشن", 12: "مغامرة", 16: "رسوم متحركة",
    35: "كوميدي", 80: "جريمة", 99: "وثائقي",
    18: "دراما", 10751: "عائلي", 14: "فانتازيا",
    36: "تاريخي", 27: "رعب", 10402: "موسيقي",
    9648: "غموض", 10749: "رومانسي", 878: "خيال علمي",
    10770: "تلفزيوني", 53: "إثارة", 10752: "حربي",
    37: "غربي",
}

GENRES_TV = {
    10759: "أكشن ومغامرة", 16: "رسوم متحركة", 35: "كوميدي",
    80: "جريمة", 99: "وثائقي", 18: "دراما",
    10751: "عائلي", 10762: "أطفال", 9648: "غموض",
    10763: "أخبار", 10764: "واقعي", 10765: "خيال علمي",
    10766: "مسلسل درامي", 10767: "حوار", 10768: "حرب وسياسة",
    37: "غربي",
}


def get_genres(media_type: str = "movie") -> Dict:
    """جلب التصنيفات"""
    if media_type == "movie":
        return GENRES_MOVIE
    return GENRES_TV