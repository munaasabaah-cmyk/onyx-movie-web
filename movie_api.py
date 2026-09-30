# -*- coding: utf-8 -*-
"""
ONYX MOVIE API - TMDB Wrapper v10.0
محدث لدعم: الممثلين، المواسم، التصنيفات، والبحث المتقدم
"""

import os
import json
import urllib.parse
import urllib.request
from typing import Optional, List, Dict

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"

LANG = "ar"


def _tmdb_get(endpoint: str, params: dict = None) -> dict:
    """طلب GET إلى TMDB"""
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY missing", "results": []}
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    params["language"] = params.get("language", LANG)
    url = f"{TMDB_BASE}{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ONYX/10.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


# =========================================================
# دوال جلب الأفلام والمسلسلات
# =========================================================

def get_trending(media_type: str = "all", time_window: str = "week") -> List[Dict]:
    data = _tmdb_get(f"/trending/{media_type}/{time_window}")
    return _format_results(data.get("results", []))


def get_popular(media_type: str = "movie", page: int = 1) -> List[Dict]:
    data = _tmdb_get(f"/{media_type}/popular", {"page": page})
    return _format_results(data.get("results", []))


def get_top_rated(media_type: str = "movie", page: int = 1) -> List[Dict]:
    data = _tmdb_get(f"/{media_type}/top_rated", {"page": page})
    return _format_results(data.get("results", []))


def get_now_playing(page: int = 1) -> List[Dict]:
    data = _tmdb_get("/movie/now_playing", {"page": page})
    return _format_results(data.get("results", []))


def get_upcoming(page: int = 1) -> List[Dict]:
    data = _tmdb_get("/movie/upcoming", {"page": page})
    return _format_results(data.get("results", []))


def get_by_genre(genre_id: int, media_type: str = "movie", page: int = 1) -> List[Dict]:
    data = _tmdb_get(f"/discover/{media_type}", {
        "with_genres": genre_id,
        "page": page,
        "sort_by": "popularity.desc",
    })
    return _format_results(data.get("results", []))


def search_multi(query: str, page: int = 1) -> List[Dict]:
    data = _tmdb_get("/search/multi", {
        "query": query,
        "page": page,
        "include_adult": "false",
    })
    return _format_results(data.get("results", []))


def get_movie_details(movie_id: int, media_type: str = "movie") -> Optional[Dict]:
    data = _tmdb_get(f"/{media_type}/{movie_id}", {
        "append_to_response": "videos,credits,similar,recommendations,images,external_ids",
    })
    if "error" in data:
        return None
    return _format_details(data)


def get_season_details(tv_id: int, season_num: int) -> Optional[Dict]:
    data = _tmdb_get(f"/tv/{tv_id}/season/{season_num}")
    if "error" in data:
        return None
    return data


def get_person_details(person_id: int) -> Optional[Dict]:
    """جلب معلومات كاملة عن ممثل"""
    data = _tmdb_get(f"/person/{person_id}", {
        "append_to_response": "combined_credits,images,external_ids",
    })
    if "error" in data:
        return None
    return _format_person(data)


def get_person_movies(person_id: int) -> List[Dict]:
    """جلب أعمال الممثل"""
    data = _tmdb_get(f"/person/{person_id}/movie_credits")
    return _format_results(data.get("cast", []))


def get_person_tv(person_id: int) -> List[Dict]:
    """جلب مسلسلات الممثل"""
    data = _tmdb_get(f"/person/{person_id}/tv_credits")
    return _format_results(data.get("cast", []))


def discover_advanced(media_type: str = "movie", genre: str = None,
                      year: str = None, lang: str = None,
                      sort: str = "popularity.desc", page: int = 1) -> List[Dict]:
    """بحث متقدم بفلاتر متعددة"""
    params = {"sort_by": sort, "page": page}
    if genre:
        params["with_genres"] = genre
    if year:
        if media_type == "movie":
            params["primary_release_year"] = year
        else:
            params["first_air_date_year"] = year
    if lang:
        params["with_original_language"] = lang
    data = _tmdb_get(f"/discover/{media_type}", params)
    return _format_results(data.get("results", []))


# =========================================================
# تنسيق النتائج
# =========================================================

def _format_results(results: List[Dict]) -> List[Dict]:
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
            "release_date": date,
            "first_air_date": r.get("first_air_date", ""),
            "rating": round(r.get("vote_average", 0), 1),
            "vote_average": r.get("vote_average", 0),
            "vote_count": r.get("vote_count", 0),
            "poster": f"{TMDB_IMG}/w500{poster}" if poster else "",
            "poster_path": poster or "",
            "backdrop": f"{TMDB_IMG}/w1280{backdrop}" if backdrop else "",
            "backdrop_path": backdrop or "",
            "genre_ids": r.get("genre_ids", []),
            "popularity": r.get("popularity", 0),
            "name": r.get("name", ""),
            "title_raw": r.get("title", ""),
        })
    return formatted


def _format_details(data: Dict) -> Dict:
    media_type = "movie" if data.get("title") else "tv"
    title = data.get("title") or data.get("name", "?")
    date = data.get("release_date") or data.get("first_air_date") or ""
    poster = data.get("poster_path")
    backdrop = data.get("backdrop_path")

    trailer = None
    for v in data.get("videos", {}).get("results", []):
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            trailer = f"https://www.youtube.com/embed/{v['key']}"
            break

    cast = []
    for c in data.get("credits", {}).get("cast", [])[:15]:
        cast.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "character": c.get("character"),
            "photo": f"{TMDB_IMG}/w200{c['profile_path']}" if c.get("profile_path") else "",
            "profile_path": c.get("profile_path", ""),
            "order": c.get("order", 0),
        })

    crew = []
    for c in data.get("credits", {}).get("crew", [])[:10]:
        crew.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "job": c.get("job"),
            "department": c.get("department"),
        })

    seasons = []
    if media_type == "tv":
        for s in data.get("seasons", []):
            seasons.append({
                "season_number": s.get("season_number"),
                "name": s.get("name"),
                "episode_count": s.get("episode_count"),
                "air_date": s.get("air_date"),
                "overview": s.get("overview", ""),
                "poster": f"{TMDB_IMG}/w300{s['poster_path']}" if s.get("poster_path") else "",
            })

    similar = _format_results(data.get("similar", {}).get("results", [])[:12])
    recommendations = _format_results(data.get("recommendations", {}).get("results", [])[:12])

    return {
        "id": data["id"],
        "media_type": media_type,
        "title": title,
        "original_title": data.get("original_title") or data.get("original_name", ""),
        "overview": data.get("overview", ""),
        "tagline": data.get("tagline", ""),
        "year": date[:4] if date else "",
        "release_date": date,
        "first_air_date": data.get("first_air_date", ""),
        "rating": round(data.get("vote_average", 0), 1),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "runtime": data.get("runtime") or (data.get("episode_run_time", [0])[0] if data.get("episode_run_time") else 0),
        "poster": f"{TMDB_IMG}/w500{poster}" if poster else "",
        "backdrop": f"{TMDB_IMG}/w1280{backdrop}" if backdrop else "",
        "genres": [{"id": g["id"], "name": g["name"]} for g in data.get("genres", [])],
        "status": data.get("status", ""),
        "trailer": trailer,
        "cast": cast,
        "crew": crew,
        "seasons": seasons,
        "similar": similar,
        "recommendations": recommendations,
        "number_of_seasons": data.get("number_of_seasons", 0),
        "number_of_episodes": data.get("number_of_episodes", 0),
        "networks": [n.get("name") for n in data.get("networks", [])],
        "production_companies": [c.get("name") for c in data.get("production_companies", [])],
        "budget": data.get("budget", 0),
        "revenue": data.get("revenue", 0),
        "homepage": data.get("homepage", ""),
    }


def _format_person(data: Dict) -> Dict:
    """تنسيق بيانات الممثل الكاملة"""
    cast_films = []
    cast_tv = []
    if "combined_credits" in data:
        for c in data["combined_credits"].get("cast", []):
            item = {
                "id": c.get("id"),
                "title": c.get("title") or c.get("name", ""),
                "character": c.get("character", ""),
                "media_type": c.get("media_type", "movie"),
                "year": (c.get("release_date") or c.get("first_air_date") or "")[:4],
                "poster": f"{TMDB_IMG}/w300{c['poster_path']}" if c.get("poster_path") else "",
                "rating": round(c.get("vote_average", 0), 1),
                "popularity": c.get("popularity", 0),
            }
            if item["media_type"] == "movie":
                cast_films.append(item)
            else:
                cast_tv.append(item)
    cast_films.sort(key=lambda x: x["popularity"], reverse=True)
    cast_tv.sort(key=lambda x: x["popularity"], reverse=True)

    return {
        "id": data["id"],
        "name": data.get("name", ""),
        "biography": data.get("biography", ""),
        "birthday": data.get("birthday", ""),
        "deathday": data.get("deathday", ""),
        "place_of_birth": data.get("place_of_birth", ""),
        "known_for_department": data.get("known_for_department", ""),
        "popularity": data.get("popularity", 0),
        "gender": data.get("gender", 0),
        "profile": f"{TMDB_IMG}/w500{data['profile_path']}" if data.get("profile_path") else "",
        "profile_path": data.get("profile_path", ""),
        "homepage": data.get("homepage", ""),
        "also_known_as": data.get("also_known_as", []),
        "movies": cast_films[:20],
        "tv_shows": cast_tv[:20],
    }


# =========================================================
# التصنيفات
# =========================================================

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
    if media_type == "movie":
        return GENRES_MOVIE
    return GENRES_TV


def search_person(query: str, page: int = 1) -> List[Dict]:
    """البحث عن ممثل"""
    data = _tmdb_get("/search/person", {"query": query, "page": page})
    results = []
    for p in data.get("results", []):
        results.append({
            "id": p.get("id"),
            "name": p.get("name", ""),
            "profile": f"{TMDB_IMG}/w200{p['profile_path']}" if p.get("profile_path") else "",
            "known_for_department": p.get("known_for_department", ""),
            "popularity": p.get("popularity", 0),
        })
    return results
