# -*- coding: utf-8 -*-

import html as html_module
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen


CONFIG_URL = "https://raw.githubusercontent.com/TNB88/cobephim.kodi/main/config.json"
DEFAULT_CONFIG = {
    "version": 1,
    "site_base": "https://cobephim.icu",
    "api_base": "https://egluy2hhb21vaw5ndw9pbmhl.darkbytes.xyz/api/v1",
    "embed_base": "https://egluy2hhb21vaw5ndw9pbmhl.darkbytes.xyz",
    "image_base": "https://zcdn.darkbytes.xyz",
}
USER_AGENT = "Mozilla/5.0 (Linux; Android 12; Kodi CobePhim/1.0) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


class ApiError(RuntimeError):
    pass


def _clean(value):
    value = html_module.unescape(str(value or ""))
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _valid_https_base(value):
    try:
        parsed = urlparse(str(value or "").strip())
        return parsed.scheme == "https" and bool(parsed.hostname) and "." in parsed.hostname
    except (TypeError, ValueError):
        return False


def _json_string_decode(value):
    return json.loads('"' + value + '"')


def normalize_movie(item):
    item = item or {}
    media_type = "tvshow" if str(item.get("type") or "").lower() in ("series", "tvshows") else "movie"
    return {
        "id": str(item.get("id") or ""),
        "slug": _clean(item.get("slug")),
        "title": _clean(item.get("name")) or "Không rõ tên",
        "original_title": _clean(item.get("origin_name")),
        "plot": _clean(item.get("description")),
        "poster": _clean(item.get("thumbnail")) or _clean(item.get("poster")),
        "fanart": _clean(item.get("poster")) or _clean(item.get("thumbnail")),
        "year": int(item.get("publish_year") or 0),
        "quality": _clean(item.get("quality")),
        "language": _clean(item.get("language")),
        "status": _clean(item.get("status")),
        "episode_current": _clean(item.get("episode_current")),
        "episode_total": _clean(item.get("episode_total")),
        "duration": _clean(item.get("episode_time")),
        "rating": float(item.get("imdb_rating") or item.get("rating_star") or 0),
        "mediatype": media_type,
        "raw": item,
    }


class CobePhimApi(object):
    def __init__(self, cache_path="", timeout=20):
        self.timeout = int(timeout)
        self.cache_path = cache_path
        self.config = dict(DEFAULT_CONFIG)
        self._load_config()

    @property
    def site_base(self):
        return self.config["site_base"].rstrip("/")

    @property
    def api_base(self):
        return self.config["api_base"].rstrip("/")

    @property
    def embed_base(self):
        return self.config["embed_base"].rstrip("/")

    def _headers(self, referer="", origin=""):
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "vi,en-US;q=0.8,en;q=0.6",
        }
        if referer:
            headers["Referer"] = referer
        if origin:
            headers["Origin"] = origin
        return headers

    def _request(self, url, referer="", origin=""):
        request = Request(url, headers=self._headers(referer, origin))
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8", "replace")
        except HTTPError as exc:
            raise ApiError("Máy chủ báo lỗi HTTP %s" % getattr(exc, "code", ""))
        except URLError as exc:
            raise ApiError("Không kết nối được máy chủ: %s" % getattr(exc, "reason", exc))
        except Exception as exc:
            raise ApiError("Lỗi mạng: %s" % exc)

    def _json(self, path, query=None):
        url = path if str(path).startswith("http") else self.api_base + "/" + str(path).lstrip("/")
        if query:
            url += ("&" if "?" in url else "?") + urlencode(query)
        payload = self._request(url, self.site_base + "/", self.site_base)
        try:
            return json.loads(payload)
        except ValueError:
            raise ApiError("API trả dữ liệu không hợp lệ")

    def _read_cache(self):
        if not self.cache_path or not os.path.isfile(self.cache_path):
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as stream:
                root = json.load(stream)
            if time.time() - float(root.get("saved_at") or 0) > 30 * 86400:
                return None
            return root.get("config")
        except (OSError, ValueError, TypeError):
            return None

    def _write_cache(self):
        if not self.cache_path:
            return
        try:
            folder = os.path.dirname(self.cache_path)
            if folder and not os.path.isdir(folder):
                os.makedirs(folder)
            with open(self.cache_path, "w", encoding="utf-8") as stream:
                json.dump({"saved_at": time.time(), "config": self.config}, stream, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @staticmethod
    def _validate_config(root):
        if not isinstance(root, dict):
            return None
        result = dict(DEFAULT_CONFIG)
        for key in ("site_base", "api_base", "embed_base", "image_base"):
            value = str(root.get(key) or "").strip().rstrip("/")
            if value:
                if not _valid_https_base(value):
                    return None
                result[key] = value
        result["version"] = int(root.get("version") or 1)
        return result

    def _load_config(self):
        try:
            remote = json.loads(self._request(CONFIG_URL, "https://github.com/TNB88/cobephim.kodi"))
            valid = self._validate_config(remote)
            if valid:
                self.config = valid
                self._write_cache()
                return
        except (ApiError, ValueError, TypeError):
            pass
        cached = self._validate_config(self._read_cache())
        if cached:
            self.config = cached

    def hot(self):
        root = self._json("/movies/hot")
        return [normalize_movie(item) for item in (root.get("result") or [])]

    def homepage_collections(self):
        root = self._json("/lists/homepageLists")
        data = root.get("result") or {}
        return data.get("collections") or []

    def search(self, keyword, page=1):
        root = self._json("/movies/search", {"keyword": keyword, "page": int(page), "limit": 32})
        return [normalize_movie(item) for item in (root.get("result") or [])], root.get("meta") or {}

    def list_page(self, kind, page=1):
        route = "/phim-bo" if kind == "series" else "/phim-le"
        url = "%s%s?page=%d" % (self.site_base, route, int(page))
        payload = self._request(url, self.site_base + "/")
        pattern = re.compile(r'\\"item\\":(\{.*?\}),\\"className\\":\\"sw-item\\"', re.S)
        movies = []
        seen = set()
        for raw in pattern.findall(payload):
            try:
                item = json.loads(_json_string_decode(raw))
            except (ValueError, TypeError):
                continue
            movie = normalize_movie(item)
            if movie["slug"] and movie["slug"] not in seen:
                seen.add(movie["slug"])
                movies.append(movie)
        pages = re.findall(r'\\"totalPages\\":(\d+),\\"currentPage\\":(\d+)', payload)
        total_pages = int(pages[-1][0]) if pages else int(page)
        if not movies:
            raise ApiError("Không đọc được danh sách %s" % ("phim bộ" if kind == "series" else "phim lẻ"))
        return movies, total_pages

    def details(self, slug):
        root = self._json("/movies/by-slug/%s" % quote(slug, safe="-"))
        movie = root.get("movie") or root.get("result") or root
        return normalize_movie(movie)

    def episodes(self, movie_id):
        root = self._json("/episodes/by-idMovie/%s" % quote(str(movie_id), safe=""))
        items = root if isinstance(root, list) else root.get("result") or root.get("data") or []
        result = []
        for item in items:
            result.append({
                "id": str(item.get("id") or ""),
                "name": _clean(item.get("name")) or "Full",
                "server": _clean(item.get("server")) or "Mặc định",
                "season": int(item.get("season_number") or 1),
                "poster": _clean(item.get("poster")),
            })
        return result

    def episode_playback(self, slug, episode_id):
        watch_url = "%s/phim/%s/tap-%s" % (self.site_base, quote(slug, safe="-"), quote(str(episode_id), safe=""))
        payload = self._request(watch_url, self.site_base + "/")
        match = re.search(r'\\"episode\\":(\{.*?\}),\\"id\\":\\"', payload, re.S)
        if not match:
            raise ApiError("Không tìm thấy dữ liệu phát của tập này")
        try:
            episode = json.loads(_json_string_decode(match.group(1)))
        except (ValueError, TypeError):
            raise ApiError("Dữ liệu phát không hợp lệ")
        link = str(episode.get("link") or "").strip()
        if not link:
            episode_type = str(episode.get("type") or "").lower()
            if episode_type in ("embed", "m3u8"):
                link = "%s/embed/%s" % (self.embed_base, quote(str(episode.get("id") or episode_id), safe=""))
        if not link:
            raise ApiError("Tập phim chưa có link phát")
        return episode, link, watch_url

    def resolve(self, slug, episode_id):
        episode, link, watch_url = self.episode_playback(slug, episode_id)
        episode_type = str(episode.get("type") or "").lower()
        if re.search(r"\.(?:m3u8|mp4)(?:\?|$)", link, re.I) or episode_type == "m3u8":
            return link, {"User-Agent": USER_AGENT, "Referer": watch_url, "Origin": self.site_base}

        embed_url = urljoin(watch_url, link)
        embed_origin = "%s://%s" % (urlparse(embed_url).scheme, urlparse(embed_url).netloc)
        page = self._request(embed_url, watch_url, self.site_base)

        candidates = []
        for pattern in (
            r'"signedMasterUrl"\s*:\s*"([^"]+)',
            r"window\.videoSrc\s*=\s*['\"]([^'\"]+)",
            r"(?:file|source|src)\s*[:=]\s*['\"]([^'\"]+\.(?:m3u8|mp4)[^'\"]*)",
            r"(https?://[^\s'\"<>]+\.(?:m3u8|mp4)[^\s'\"<>]*)",
        ):
            candidates.extend(re.findall(pattern, page, re.I))

        base_match = re.search(r'const\s+baseUrl\s*=\s*["\']([^"\']+)', page, re.I)
        hash_match = re.search(r'const\s+videoHash\s*=\s*["\']([^"\']+)', page, re.I)
        if base_match and hash_match:
            candidates.append("%s/stream/%s/master.m3u8" % (base_match.group(1).rstrip("/"), hash_match.group(1)))

        for candidate in candidates:
            candidate = html_module.unescape(candidate).replace("\\/", "/").strip()
            candidate = urljoin(embed_url, candidate)
            if _valid_https_base(candidate) and re.search(r"\.(?:m3u8|mp4)(?:\?|$)", candidate, re.I):
                return candidate, {"User-Agent": USER_AGENT, "Referer": embed_url, "Origin": embed_origin}
        raise ApiError("Chưa tách được link video từ máy chủ phát")

