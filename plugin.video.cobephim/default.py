# -*- coding: utf-8 -*-

import os
import sys
from collections import defaultdict
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
if not xbmcvfs.exists(PROFILE):
    xbmcvfs.mkdirs(PROFILE)

LIB = xbmcvfs.translatePath(os.path.join(ADDON.getAddonInfo("path"), "resources", "lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from cobephim_api import ApiError, CobePhimApi  # noqa: E402

API = CobePhimApi(os.path.join(PROFILE, "remote_config.json"))


def plugin_url(action, **params):
    values = {"action": action}
    values.update({key: value for key, value in params.items() if value is not None})
    return BASE_URL + "?" + urlencode(values)


def notify(message, title="Cô Bé Phim"):
    xbmcgui.Dialog().notification(title, str(message), xbmcgui.NOTIFICATION_INFO, 6000)


def set_info(item, movie):
    info = {
        "title": movie.get("title") or "Không rõ tên",
        "originaltitle": movie.get("original_title") or "",
        "plot": movie.get("plot") or "",
        "year": int(movie.get("year") or 0),
        "rating": float(movie.get("rating") or 0),
        "duration": movie.get("duration") or "",
        "mediatype": movie.get("mediatype") or "movie",
    }
    try:
        tag = item.getVideoInfoTag()
        tag.setTitle(info["title"])
        tag.setOriginalTitle(info["originaltitle"])
        tag.setPlot(info["plot"])
        tag.setYear(info["year"])
        tag.setRating(info["rating"])
        tag.setMediaType(info["mediatype"])
    except Exception:
        item.setInfo("video", info)


def movie_label(movie):
    bits = []
    if movie.get("quality"):
        bits.append(movie["quality"])
    if movie.get("language"):
        bits.append(movie["language"])
    if movie.get("mediatype") == "tvshow" and movie.get("episode_current"):
        bits.append("Tập %s" % movie["episode_current"])
    suffix = "  [COLOR gold]%s[/COLOR]" % " • ".join(bits) if bits else ""
    return (movie.get("title") or "Không rõ tên") + suffix


def add_folder(label, action, art=None, **params):
    item = xbmcgui.ListItem(label=label)
    if art:
        item.setArt(art)
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url(action, **params), item, isFolder=True)


def add_movie(movie):
    item = xbmcgui.ListItem(label=movie_label(movie))
    item.setArt({"thumb": movie.get("poster") or "", "poster": movie.get("poster") or "", "fanart": movie.get("fanart") or ""})
    set_info(item, movie)
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url("movie", slug=movie.get("slug"), movie_id=movie.get("id")), item, isFolder=True)


def add_episode(movie, episode):
    label = "Tập %s" % episode["name"] if episode["name"].lower() != "full" else "Full"
    item = xbmcgui.ListItem(label=label)
    poster = episode.get("poster") or movie.get("poster") or ""
    item.setArt({"thumb": poster, "poster": poster, "fanart": movie.get("fanart") or ""})
    set_info(item, dict(movie, title="%s - %s" % (movie["title"], label), mediatype="episode"))
    item.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url("play", slug=movie["slug"], episode_id=episode["id"], title=movie["title"]), item, isFolder=False)


def finish(content="movies"):
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, cacheToDisc=False)


def home():
    xbmcplugin.setPluginCategory(HANDLE, "Cô Bé Phim")
    add_folder("[B]Phim hot[/B]", "hot")
    add_folder("[B]Phim bộ[/B]", "list", kind="series", page=1)
    add_folder("[B]Phim lẻ[/B]", "list", kind="movie", page=1)
    add_folder("[B]Bộ sưu tập[/B]", "collections")
    add_folder("[B]Tìm kiếm[/B]", "search")
    finish("videos")


def show_hot():
    xbmcplugin.setPluginCategory(HANDLE, "Phim hot")
    for movie in API.hot():
        add_movie(movie)
    finish()


def show_list(kind, page):
    title = "Phim bộ" if kind == "series" else "Phim lẻ"
    xbmcplugin.setPluginCategory(HANDLE, "%s - Trang %d" % (title, page))
    movies, total_pages = API.list_page(kind, page)
    for movie in movies:
        add_movie(movie)
    if page < total_pages:
        add_folder("[B]Trang tiếp theo ›[/B]", "list", kind=kind, page=page + 1)
    finish()


def show_collections():
    xbmcplugin.setPluginCategory(HANDLE, "Bộ sưu tập")
    for collection in API.homepage_collections():
        label = collection.get("name") or "Bộ sưu tập"
        add_folder(label, "collection", collection_id=collection.get("id"))
    finish("videos")


def show_collection(collection_id):
    collections = API.homepage_collections()
    selected = next((item for item in collections if str(item.get("id")) == str(collection_id)), None)
    if not selected:
        raise ApiError("Không tìm thấy bộ sưu tập")
    xbmcplugin.setPluginCategory(HANDLE, selected.get("name") or "Bộ sưu tập")
    from cobephim_api import normalize_movie
    for raw in selected.get("movies") or []:
        add_movie(normalize_movie(raw))
    finish()


def do_search(keyword="", page=1):
    if not keyword:
        keyword = xbmcgui.Dialog().input("Tìm phim", type=xbmcgui.INPUT_ALPHANUM).strip()
        if not keyword:
            finish()
            return
    xbmcplugin.setPluginCategory(HANDLE, "Kết quả: %s" % keyword)
    movies, meta = API.search(keyword, page)
    for movie in movies:
        add_movie(movie)
    total_pages = int(meta.get("totalPages") or meta.get("totalPage") or page)
    if page < total_pages:
        add_folder("[B]Trang tiếp theo ›[/B]", "search", keyword=keyword, page=page + 1)
    finish()


def show_movie(slug, movie_id=""):
    movie = API.details(slug)
    episodes = API.episodes(movie.get("id") or movie_id)
    if not episodes:
        raise ApiError("Phim chưa có tập để phát")
    groups = defaultdict(list)
    for episode in episodes:
        groups[episode["server"]].append(episode)
    xbmcplugin.setPluginCategory(HANDLE, movie["title"])
    if len(groups) == 1:
        for episode in sorted(episodes, key=lambda value: (value["season"], episode_sort(value["name"]))):
            add_episode(movie, episode)
    else:
        for server in sorted(groups.keys(), key=server_sort):
            add_folder("[B]%s[/B]  (%d tập)" % (server, len(groups[server])), "episodes", slug=slug, movie_id=movie.get("id"), server=server)
    finish("episodes")


def episode_sort(value):
    match = __import__("re").search(r"\d+", str(value))
    return int(match.group(0)) if match else 999999


def server_sort(value):
    text = str(value).lower()
    return (0 if "vietsub" in text or "phụ đề" in text else 1, text)


def show_episodes(slug, movie_id, server):
    movie = API.details(slug)
    episodes = [item for item in API.episodes(movie_id or movie["id"]) if item["server"] == server]
    xbmcplugin.setPluginCategory(HANDLE, "%s - %s" % (movie["title"], server))
    for episode in sorted(episodes, key=lambda value: (value["season"], episode_sort(value["name"]))):
        add_episode(movie, episode)
    finish("episodes")


def kodi_headers(headers):
    return urlencode(headers)


def play(slug, episode_id, title=""):
    try:
        progress = xbmcgui.DialogProgress()
        progress.create("Cô Bé Phim", "Đang lấy link phát...")
        try:
            stream_url, headers = API.resolve(slug, episode_id)
        finally:
            progress.close()
        item = xbmcgui.ListItem(label=title or "Cô Bé Phim", path=stream_url + "|" + kodi_headers(headers))
        item.setProperty("IsPlayable", "true")
        item.setMimeType("application/vnd.apple.mpegurl" if ".m3u8" in stream_url.lower() else "video/mp4")
        item.setContentLookup(False)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)
    except ApiError as exc:
        notify(exc)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def dispatch():
    params = dict(parse_qsl(sys.argv[2][1:] if len(sys.argv) > 2 else ""))
    action = params.get("action", "home")
    try:
        if action == "home":
            home()
        elif action == "hot":
            show_hot()
        elif action == "list":
            show_list(params.get("kind", "series"), int(params.get("page", "1")))
        elif action == "collections":
            show_collections()
        elif action == "collection":
            show_collection(params.get("collection_id", ""))
        elif action == "search":
            do_search(params.get("keyword", ""), int(params.get("page", "1")))
        elif action == "movie":
            show_movie(params.get("slug", ""), params.get("movie_id", ""))
        elif action == "episodes":
            show_episodes(params.get("slug", ""), params.get("movie_id", ""), params.get("server", ""))
        elif action == "play":
            play(params.get("slug", ""), params.get("episode_id", ""), params.get("title", ""))
        else:
            home()
    except ApiError as exc:
        notify(exc)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
    except Exception as exc:
        xbmc.log("[plugin.video.cobephim] %s" % exc, xbmc.LOGERROR)
        notify("Lỗi plugin: %s" % exc)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)


if __name__ == "__main__":
    dispatch()
