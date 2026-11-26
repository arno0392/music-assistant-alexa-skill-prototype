"""PATCH: refresh the APL screen when Music Assistant moves to the next track
inside the flow stream (no new Play request reaches the skill in that case).

usage: python3 fix_apl_refresh.py ma_control.py lambda_function.py
"""
import sys

ma_path, lambda_path = sys.argv[1], sys.argv[2]

# ---------- 1. ma_control.py: read the current queue item from MA ----------
src = open(ma_path, encoding="utf-8").read()
if "def get_now_playing" in src:
    print("ma_control: deja patche")
else:
    src += '''


# PATCH: current track of a player, read from Music Assistant.
async def _get_now_playing(server_url, token, player_id):
    async with aiohttp.ClientSession() as session:
        async with MusicAssistantClient(server_url, session, token=token) as client:
            queue = await client.player_queues.get_active_queue(player_id)
            item = queue.current_item if queue else None
            if item is None:
                return None
            media = item.media_item
            title = (getattr(media, "name", None) or item.name or "")
            artists = getattr(media, "artists", None) or []
            artist = "/".join(a.name for a in artists if getattr(a, "name", None))
            album_obj = getattr(media, "album", None)
            album = getattr(album_obj, "name", "") or ""
            image = ""
            try:
                image = client.get_media_item_image_url(item, size=512) or ""
            except Exception:
                image = ""
            return {"queue_item_id": item.queue_item_id, "title": title,
                    "artist": artist, "album": album, "imageUrl": image}


def get_now_playing(player_id):
    """Return {queue_item_id, title, artist, album, imageUrl} or None."""
    server_url = get_env_secret("MA_API_URL")
    token = get_env_secret("MA_API_TOKEN")
    if not server_url or not player_id:
        return None
    try:
        return asyncio.run(_get_now_playing(server_url, token, player_id))
    except Exception:
        logger.debug("get_now_playing failed for %s", player_id, exc_info=True)
        return None
'''
    open(ma_path, "w", encoding="utf-8").write(src)
    print("ma_control: patch applique")

# ---------- 2. lambda_function.py: use it during the APL refresh ----------
src = open(lambda_path, encoding="utf-8").read()
if "_sync_now_playing_from_ma" in src:
    print("lambda_function (refresh): deja patche")
else:
    helper = '''

# PATCH: follow track changes inside the MA flow stream on the APL screen.
_NOW_PLAYING_POLL_SECONDS = 4
_now_playing_state = {}


def _sync_now_playing_from_ma(handler_input):
    """Every few seconds, ask MA which queue item is playing on the mapped
    player and, if it changed, update the shared store metadata (title,
    artist, album, cover). The stream URL is left untouched."""
    import time
    import shared_store
    device_id = _device_id_from(handler_input)
    player_id = device_mapping.get_player_for_device(device_id)
    if not player_id:
        return
    state = _now_playing_state.setdefault(player_id, {"t": 0.0, "id": None})
    now = time.time()
    if now - state["t"] < _NOW_PLAYING_POLL_SECONDS:
        return
    state["t"] = now
    info = ma_control.get_now_playing(player_id)
    if not info or info["queue_item_id"] == state["id"]:
        return
    first = state["id"] is None
    state["id"] = info["queue_item_id"]
    store = shared_store._store
    if store is None or not store.get("streamUrl"):
        return
    secondary = " - ".join(x for x in (info["artist"], info["album"]) if x)
    if first and store.get("title") == info["title"]:
        return
    store.update({"title": info["title"], "artist": info["artist"],
                  "album": info["album"], "secondary": secondary})
    if info["imageUrl"]:
        store["imageUrl"] = info["imageUrl"]
    logger.info("Now playing changed on %s: %s", player_id, info["title"])

'''
    anchor = "\nclass APLUserEventHandler(AbstractRequestHandler):"
    call_anchor = '''        changed = False
        try:
            result = data.get_latest()'''
    call_new = '''        changed = False
        try:
            _sync_now_playing_from_ma(handler_input)
        except Exception:
            logger.exception("Failed to sync now playing from MA")
        try:
            result = data.get_latest()'''
    assert src.count(anchor) == 1 and src.count(call_anchor) == 1, "code inattendu, patch non applique"
    src = src.replace(anchor, helper + anchor, 1).replace(call_anchor, call_new, 1)
    open(lambda_path, "w", encoding="utf-8").write(src)
    print("lambda_function (refresh): patch applique")
