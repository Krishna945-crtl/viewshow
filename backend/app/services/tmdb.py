"""Import any real movie from TMDB (The Movie Database).

Optional - only active when CV_TMDB_API_KEY or CV_TMDB_READ_TOKEN is set.
We pull metadata (title, genres, overview, keywords, cast, trailer, certificate)
and the poster's *colours*. Posters are only displayed when
CV_TMDB_SHOW_POSTERS is on, which TMDB's API terms allow with attribution.

This product uses the TMDB API but is not endorsed or certified by TMDB.
"""

from __future__ import annotations

from datetime import date

import httpx

from app.core.config import get_settings
from app.core.errors import AppError

API = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p"

# ISO 639-1 -> the language names our filters use
LANGS = {"en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil", "kn": "Kannada", "ml": "Malayalam",
         "bn": "Bengali", "mr": "Marathi", "pa": "Punjabi", "gu": "Gujarati", "ja": "Japanese", "ko": "Korean",
         "zh": "Chinese", "cn": "Cantonese", "fr": "French", "es": "Spanish", "de": "German", "it": "Italian",
         "pt": "Portuguese", "ru": "Russian", "tr": "Turkish", "th": "Thai", "id": "Indonesian"}


class TMDBError(AppError):
    def __init__(self, message: str, status: int = 502):
        super().__init__(status, "tmdb_error", message)


class TMDBClient:
    def __init__(self, api_key: str = "", read_token: str = "", language: str = "en-US",
                 transport: httpx.AsyncBaseTransport | None = None):
        headers = {"Accept": "application/json"}
        self._params = {"language": language}
        if read_token:
            headers["Authorization"] = f"Bearer {read_token}"
        else:
            self._params["api_key"] = api_key
        self._http = httpx.AsyncClient(headers=headers, timeout=10.0, transport=transport)

    async def aclose(self):
        await self._http.aclose()

    async def _get(self, path: str, **params) -> dict:
        try:
            r = await self._http.get(f"{API}{path}", params={**self._params, **params})
        except httpx.HTTPError as exc:
            raise TMDBError("TMDB is not reachable right now") from exc
        if r.status_code == 401:
            raise TMDBError("TMDB rejected the API key - check CV_TMDB_* settings")
        if r.status_code == 404:
            raise TMDBError("No such movie on TMDB", 404)
        if r.status_code >= 400:
            raise TMDBError(f"TMDB error {r.status_code}")
        return r.json()

    async def search(self, query: str, year: int | None = None) -> list[dict]:
        params = {"query": query, "include_adult": "false", "page": 1}
        if year:
            params["year"] = year
        data = await self._get("/search/movie", **params)
        return data.get("results") or []

    async def movie(self, tmdb_id: int) -> dict:
        return await self._get(f"/movie/{tmdb_id}", append_to_response="keywords,credits,videos,release_dates")

    async def image(self, path: str | None, size: str = "w342") -> bytes | None:
        """Poster bytes for palette extraction. Failing here is never fatal."""
        if not path:
            return None
        try:
            r = await self._http.get(f"{IMG}/{size}{path}")
            return r.content if r.status_code == 200 else None
        except httpx.HTTPError:
            return None


def image_url(path: str | None, size: str = "w500") -> str | None:
    return f"{IMG}/{size}{path}" if path else None


def _year(d: str | None) -> int | None:
    try:
        return date.fromisoformat(d).year if d else None
    except ValueError:
        return None


def _certificate(d: dict, region: str) -> str:
    for block in (d.get("release_dates") or {}).get("results") or []:
        if block.get("iso_3166_1") == region:
            for rel in block.get("release_dates") or []:
                cert = (rel.get("certification") or "").strip()
                if cert:
                    return cert[:8]
    return "UA"


def _trailer(d: dict) -> str | None:
    vids = [v for v in (d.get("videos") or {}).get("results") or []
            if v.get("site") == "YouTube" and v.get("type") == "Trailer" and v.get("key")]
    vids.sort(key=lambda v: (not v.get("official"), v.get("published_at") or ""))
    return f"https://www.youtube.com/watch?v={vids[0]['key']}" if vids else None


def search_result(r: dict, show_posters: bool) -> dict:
    return {
        "tmdb_id": r.get("id"),
        "title": r.get("title") or r.get("original_title") or "Untitled",
        "year": _year(r.get("release_date")),
        "language": LANGS.get(r.get("original_language") or "", (r.get("original_language") or "").upper()),
        "overview": (r.get("overview") or "")[:220],
        "rating": round(r["vote_average"], 1) if r.get("vote_average") else None,
        "poster_thumb": image_url(r.get("poster_path"), "w185") if show_posters else None,
    }


def to_movie_fields(d: dict, region: str = "IN", show_posters: bool = True) -> dict:
    """TMDB /movie/{id} payload -> kwargs for our Movie model. Pure, easy to test."""
    keywords = [k["name"] for k in (d.get("keywords") or {}).get("keywords") or [] if k.get("name")]
    cast = [c["name"] for c in ((d.get("credits") or {}).get("cast") or [])[:8] if c.get("name")]
    lang = d.get("original_language") or "en"
    release = None
    if d.get("release_date"):
        try:
            release = date.fromisoformat(d["release_date"])
        except ValueError:
            release = None
    return {
        "tmdb_id": d["id"],
        "title": (d.get("title") or d.get("original_title") or "Untitled")[:200],
        "tagline": (d.get("tagline") or None) and d["tagline"][:300],
        "synopsis": (d.get("overview") or "")[:5000],
        "genres": [g["name"] for g in d.get("genres") or [] if g.get("name")][:8],
        "keywords": keywords[:40],
        "language": LANGS.get(lang, lang.upper()),
        "certificate": _certificate(d, region),
        "runtime_minutes": d.get("runtime") or 120,
        "release_date": release,
        "rating": round(d["vote_average"], 1) if d.get("vote_average") else None,
        "poster_url": image_url(d.get("poster_path")) if show_posters else None,
        "backdrop_url": image_url(d.get("backdrop_path"), "w1280") if show_posters else None,
        "trailer_url": _trailer(d),
        "cast": cast,
    }


async def get_tmdb():
    """FastAPI dependency. Tests override this with a client on a mock transport."""
    s = get_settings()
    if not s.tmdb_enabled:
        raise AppError(503, "tmdb_disabled", "TMDB import is off - set CV_TMDB_API_KEY or CV_TMDB_READ_TOKEN")
    client = TMDBClient(s.tmdb_api_key, s.tmdb_read_token, s.tmdb_language)
    try:
        yield client
    finally:
        await client.aclose()
