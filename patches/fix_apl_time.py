"""PATCH: per-track elapsed / total time on the APL screen (flow mode).

In flow mode the hidden Video component plays one endless stream, so its
time is the time since the stream started and its duration is unknown.
This patch asks Music Assistant for the current track's elapsed time and
duration and makes the slider show them.

Requires fix_apl_refresh.py to be applied first.
usage: python3 fix_apl_time.py apl_document.json ma_control.py lambda_function.py
"""
import json, sys

doc_path, ma_path, lambda_path = sys.argv[1:4]

# ---------- 1. APL document ----------
doc = json.load(open(doc_path, encoding="utf-8"))
if "MaTimeRoot" in json.dumps(doc):
    print("apl_document (temps): deja patche")
else:
    root = doc["layouts"]["AudioPlayer"]["item"][0]
    names = [b["name"] for b in root.get("bind", [])]
    assert "videoProgressValue" in names, "bind introuvable, patch non applique"
    root["id"] = "MaTimeRoot"
    root["bind"] += [
        {"name": "trackOffset", "type": "number", "value": 0},
        {"name": "trackTotal", "type": "number", "value": 0},
        {"name": "pendingElapsed", "type": "number", "value": 0},
        {"name": "needsResync", "type": "boolean", "value": False},
    ]
    progress = "${Math.max(0, videoProgressValue - trackOffset)}"
    videos, sliders = [], []

    def walk(n):
        if isinstance(n, dict):
            if n.get("type") == "Video":
                videos.append(n)
            if n.get("type") == "AlexaSlider":
                sliders.append(n)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(doc)
    assert len(videos) == 1 and len(sliders) == 1, "Video/AlexaSlider introuvable"
    video, slider = videos[0], sliders[0]

    resync = {"type": "Sequential", "when": "${needsResync}", "commands": [
        {"type": "SetValue", "property": "trackOffset",
         "value": "${event.currentTime - pendingElapsed}"},
        {"type": "SetValue", "property": "needsResync", "value": False}]}
    new_tu = []
    for c in video["onTimeUpdate"]:
        if c.get("componentId") == "slider" and c.get("property") == "progressValue":
            new_tu.append(resync)
            c = dict(c, value=progress)
        new_tu.append(c)
    assert resync in new_tu, "onTimeUpdate inattendu, patch non applique"
    video["onTimeUpdate"] = new_tu

    slider["progressValue"] = progress
    slider["totalValue"] = "${trackTotal > 0 ? trackTotal : videoTotalValue}"
    for c in slider.get("onUpCommand", []):
        if c.get("command") == "seek":
            c["value"] = "${sliderThumbPosition - Math.max(0, videoProgressValue - trackOffset)}"
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (temps): patch applique")

# ---------- 2. ma_control.py: also return elapsed / duration ----------
src = open(ma_path, encoding="utf-8").read()
if "elapsed_ms" in src:
    print("ma_control (temps): deja patche")
else:
    old = '''            return {"queue_item_id": item.queue_item_id, "title": title,
                    "artist": artist, "album": album, "imageUrl": image}'''
    new = '''            import time as _time
            elapsed = float(getattr(queue, "elapsed_time", 0) or 0)
            updated = getattr(queue, "elapsed_time_last_updated", None)
            state = getattr(queue, "state", "")
            state = str(getattr(state, "value", state) or "").lower()
            if updated and state == "playing":
                elapsed += max(0.0, _time.time() - float(updated))
            duration = float(item.duration or 0)
            return {"queue_item_id": item.queue_item_id, "title": title,
                    "artist": artist, "album": album, "imageUrl": image,
                    "elapsed_ms": int(elapsed * 1000),
                    "duration_ms": int(duration * 1000)}'''
    assert src.count(old) == 1, "fix_apl_refresh.py doit etre applique avant"
    open(ma_path, "w", encoding="utf-8").write(src.replace(old, new))
    print("ma_control (temps): patch applique")

# ---------- 3. lambda_function.py ----------
src = open(lambda_path, encoding="utf-8").read()
if "_apl_time_commands" in src:
    print("lambda_function (temps): deja patche")
else:
    start = src.index("# PATCH: follow track changes inside the MA flow stream on the APL screen.")
    end = src.index("\nclass APLUserEventHandler(AbstractRequestHandler):")
    new_helper = '''# PATCH: follow track changes inside the MA flow stream on the APL screen.
_NOW_PLAYING_POLL_SECONDS = 4
_now_playing_state = {}


def _apl_time_commands(info):
    """SetValue commands giving the APL slider the per-track elapsed/total."""
    return [
        {"type": "SetValue", "componentId": "MaTimeRoot",
         "property": "trackTotal", "value": info.get("duration_ms", 0)},
        {"type": "SetValue", "componentId": "MaTimeRoot",
         "property": "pendingElapsed", "value": info.get("elapsed_ms", 0)},
        {"type": "SetValue", "componentId": "MaTimeRoot",
         "property": "needsResync", "value": True},
    ]


def _sync_now_playing_from_ma(handler_input):
    """Every few seconds, ask MA which queue item is playing on the mapped
    player. On a track change (or when the APL document was re-rendered),
    update the shared store metadata and return SetValue commands for the
    per-track time. The stream URL is left untouched."""
    import time
    import shared_store
    device_id = _device_id_from(handler_input)
    player_id = device_mapping.get_player_for_device(device_id)
    if not player_id:
        return None
    state = _now_playing_state.setdefault(player_id, {"t": 0.0, "id": None, "tick": -1})

    # refreshTick restarts from 0 when a new APL document is rendered.
    try:
        args = handler_input.request_envelope.request.arguments or []
        tick = int(float(args[1])) if len(args) > 1 else None
    except Exception:
        tick = None
    if tick is not None:
        if tick < state["tick"]:
            state["id"] = None
            state["t"] = 0.0
        state["tick"] = tick

    now = time.time()
    if now - state["t"] < _NOW_PLAYING_POLL_SECONDS:
        return None
    state["t"] = now
    info = ma_control.get_now_playing(player_id)
    if not info or info["queue_item_id"] == state["id"]:
        return None
    state["id"] = info["queue_item_id"]

    store = shared_store._store
    if store is not None and store.get("streamUrl") and store.get("title") != info["title"]:
        secondary = " - ".join(x for x in (info["artist"], info["album"]) if x)
        store.update({"title": info["title"], "artist": info["artist"],
                      "album": info["album"], "secondary": secondary})
        if info["imageUrl"]:
            store["imageUrl"] = info["imageUrl"]
        logger.info("Now playing changed on %s: %s", player_id, info["title"])
    return _apl_time_commands(info)

'''
    src = src[:start] + new_helper + src[end:]
    old_call = '''        try:
            _sync_now_playing_from_ma(handler_input)
        except Exception:
            logger.exception("Failed to sync now playing from MA")'''
    new_call = '''        time_commands = None
        try:
            time_commands = _sync_now_playing_from_ma(handler_input)
        except Exception:
            logger.exception("Failed to sync now playing from MA")'''
    old_ret = '''        # Always schedule the next refresh so polling continues.'''
    new_ret = '''        if time_commands:
            from ask_sdk_model.interfaces.alexa.presentation.apl import ExecuteCommandsDirective
            handler_input.response_builder.add_directive(
                ExecuteCommandsDirective(commands=time_commands, token="playbackToken"))

        # Always schedule the next refresh so polling continues.'''
    assert src.count(old_call) == 1 and src.count(old_ret) == 1, "code inattendu, patch non applique"
    src = src.replace(old_call, new_call).replace(old_ret, new_ret)
    open(lambda_path, "w", encoding="utf-8").write(src)
    print("lambda_function (temps): patch applique")
