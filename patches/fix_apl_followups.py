"""PATCH: follow-ups after the live-page work (Echo Show, flow mode).

1. Total time missing on the first track, slider back to 0 after a seek from
   the MA web UI: the time sync was sent once per track, right when the screen
   appeared, and MA can still report 0 (or nothing) at that moment. It is now
   sent again ~6 s later, then re-sent (a few times at most, during 45 s)
   whenever the position shown on the screen and MA's position differ by
   more than 3 s. The screen's track offset is added to the "maReport" text
   so the skill knows what the slider shows.
2. Pause/play pressed on the Echo screen is forwarded to MA (pause/resume),
   unless MA itself asked for it, or MA is already in that state.
3. "settings.idleTimeout" = 10 min on the APL document: the Echo Show no
   longer goes back home ~10 s after a pause.
4. Previous/start over: computed from the track shown on the screen instead
   of MA's current_index (which can be ahead in flow mode), and logged.

Requires every previous patch (fix_stream_key.py last).
usage: python3 fix_apl_followups.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
P = lambda *p: os.path.join(base, *p)


def patch_text(path, label, marker, edits, append=None):
    src = open(path, encoding="utf-8").read()
    if marker in src:
        print(f"{label}: deja patche")
        return
    for old, new, *count in edits:
        n = count[0] if count else 1
        assert src.count(old) == n, f"{label}: code inattendu, patch non applique ({old[:60]!r})"
        src = src.replace(old, new)
    if append:
        src = src.rstrip("\n") + "\n" + append
    open(path, "w", encoding="utf-8").write(src)
    print(f"{label}: patch applique")


# ---------------------------------------------------------------- apl_document.json
doc_path = P("skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
OLD_REPORT = "${event.currentTime}|${event.paused ? 'false' : 'true'}"
NEW_REPORT = OLD_REPORT + "|${trackOffset}"
if "idleTimeout" in json.dumps(doc):
    print("apl_document (suivi): deja patche")
else:
    assert OLD_REPORT in json.dumps(doc), "fix_live_report.py doit etre applique avant"
    count = 0

    def walk(x):
        global count
        if isinstance(x, dict):
            if x.get("componentId") == "maReport" and x.get("value") == OLD_REPORT:
                x["value"] = NEW_REPORT
                count += 1
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(doc)
    assert count >= 4, f"apl_document (suivi): {count} ecritures maReport trouvees"
    doc["settings"] = {"idleTimeout": 600000}
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (suivi): patch applique")


# ---------------------------------------------------------------- ma_control.py
patch_text(P("skill", "ma_control.py"), "ma_control (suivi)", "def get_queue_state", [
    ("async def _play_relative_index(client, player_id, offset):",
     "async def _play_relative_index(client, player_id, offset, ref_item_id=None):"),
    ("    target_index = max(queue.current_index + offset, 0)\n",
     "    base_index = queue.current_index\n"
     "    # PATCH: start from the track shown on the screen; in flow mode MA's\n"
     "    # current_index can already point at the next track.\n"
     "    if ref_item_id:\n"
     "        try:\n"
     "            first = max(0, base_index - 25)\n"
     "            items = await client.player_queues.get_queue_items(queue.queue_id, limit=50, offset=first)\n"
     "            for i, it in enumerate(items):\n"
     "                if it.queue_item_id == ref_item_id:\n"
     "                    base_index = first + i\n"
     "                    break\n"
     "        except Exception:\n"
     "            logger.debug(\"Could not read the queue items\", exc_info=True)\n"
     "    target_index = max(base_index + offset, 0)\n"
     "    logger.info(\"MA queue %s: shown track index %s (MA current_index %s, %s items) -> play index %s\",\n"
     "                queue.queue_id, base_index, queue.current_index, getattr(queue, 'items', '?'), target_index)\n"
     "    if base_index + offset < 0:\n"
     "        logger.info(\"Nothing before this track in the MA queue: restarting it\")\n"),
    ("async def _send_command(server_url, token, player_id, command):",
     "async def _send_command(server_url, token, player_id, command, ref_item_id=None):"),
    ("await _play_relative_index(client, player_id, -1)",
     "await _play_relative_index(client, player_id, -1, ref_item_id)"),
    ("await _play_relative_index(client, player_id, 0)",
     "await _play_relative_index(client, player_id, 0, ref_item_id)"),
    ("def send_player_command(player_id, command):",
     "def send_player_command(player_id, command, ref_item_id=None):"),
    ("asyncio.run(_send_command(server_url, token, player_id, command))",
     "asyncio.run(_send_command(server_url, token, player_id, command, ref_item_id))"),
], append='''

# PATCH: playback state of the active queue of a player ("playing", "paused", ...).
async def _get_queue_state(server_url, token, player_id):
    async with aiohttp.ClientSession() as session:
        async with MusicAssistantClient(server_url, session, token=token) as client:
            queue = await client.player_queues.get_active_queue(player_id)
            if queue is None:
                return None
            state = getattr(queue, "state", "")
            return str(getattr(state, "value", state) or "").lower()


def get_queue_state(player_id):
    server_url = get_env_secret("MA_API_URL")
    token = get_env_secret("MA_API_TOKEN")
    if not server_url or not player_id:
        return None
    try:
        return asyncio.run(_get_queue_state(server_url, token, player_id))
    except Exception:
        logger.debug("get_queue_state failed for %s", player_id, exc_info=True)
        return None
''')


# ---------------------------------------------------------------- lambda_function.py
patch_text(P("skill", "lambda_function.py"), "lambda_function (suivi)", "def _screen_report", [
    # shown track used as reference for previous / start over
    ("ma_control.send_player_command(player_id, command)",
     "ma_control.send_player_command(player_id, command, ref_item_id=_shown_item_id(player_id))", 4),
    ('ma_control.send_player_command(player_id, "start_over")',
     'ma_control.send_player_command(player_id, "start_over", ref_item_id=_shown_item_id(player_id))'),
    # report: "currentTime|playing|trackOffset"
    ("""    if isinstance(report, str) and '|' in report:
        try:
            position, playing = report.split('|', 1)
            shared_store.set_report(player_id,
                                    'PLAYING' if playing.strip().lower() == 'true' else 'PAUSED',
                                    float(position or 0),
                                    shared_store._rendered_stream.get(player_id))
        except (TypeError, ValueError):
            pass
""", """    if isinstance(report, str) and '|' in report:
        try:
            parts = report.split('|')
            is_playing = parts[1].strip().lower() == 'true'
            shared_store.set_report(player_id, 'PLAYING' if is_playing else 'PAUSED',
                                    float(parts[0] or 0),
                                    shared_store._rendered_stream.get(player_id))
            offset = float(parts[2]) if len(parts) > 2 and parts[2].strip() else None
            _screen_report(device_id, player_id, float(parts[0] or 0), is_playing, offset)
        except (TypeError, ValueError, IndexError):
            pass
"""),
    # pause/resume applied because MA asked: not to be sent back to MA
    ("""    if media:
        logger.info("Live page %s: %s", player_id, ", ".join(after))
""", """    if media:
        logger.info("Live page %s: %s", player_id, ", ".join(after))
        _expected_state[player_id] = (media[-1]["command"] == "play", _time.time())
"""),
    # new screen: restart the screen tracking
    ("""        shared_store._rendered_stream[player_id] = url
        _now_playing_state.pop(player_id, None)
""", """        shared_store._rendered_stream[player_id] = url
        _now_playing_state.pop(player_id, None)
        _screen_restarted(player_id)
"""),
    ("""            _now_playing_state.pop(player_id, None)
            shared_store._rendered_stream[player_id] = (shared_store._store or {}).get('streamUrl') or url
""", """            _now_playing_state.pop(player_id, None)
            _screen_restarted(player_id)
            shared_store._rendered_stream[player_id] = (shared_store._store or {}).get('streamUrl') or url
"""),
    # time sync: resend when needed
    ("""    info = ma_control.get_now_playing(player_id)
    if not info or info["queue_item_id"] == state["id"]:
        return None
    state["id"] = info["queue_item_id"]
""", """    info = ma_control.get_now_playing(player_id)
    if not info:
        return None
    if info["queue_item_id"] == state["id"]:
        return _apl_time_commands(info) if _time_needs_resend(player_id, state, info, now) else None
    state["id"] = info["queue_item_id"]
    state["since"] = now
    state["resent"] = 0
    if not info.get("duration_ms"):
        state["id"] = None   # MA does not know the duration yet: ask again
"""),
], append='''

# PATCH (follow-ups): what the screen shows, and what it changes by itself.
import threading as _threading
import time as _time

_screen_pos = {}        # player_id -> {"current", "offset", "playing", "t"}
_screen_started = {}    # player_id -> time the screen (re)started a stream
_expected_state = {}    # player_id -> (playing, time): change asked by MA
_TIME_WINDOW = 45       # seconds after a new track/screen during which the time is checked
_TIME_TOLERANCE_MS = 3000


def _shown_item_id(player_id):
    return (_now_playing_state.get(player_id) or {}).get("id")


def _screen_restarted(player_id):
    _screen_pos.pop(player_id, None)
    _expected_state.pop(player_id, None)
    _screen_started[player_id] = _time.time()


def _time_needs_resend(player_id, state, info, now):
    """Same track as already synced: send the time again ~6 s later (MA may have
    answered 0 at first), then whenever the screen is more than 3 s off."""
    age = now - state.get("since", now)
    if age > _TIME_WINDOW:
        return False
    if state.get("resent", 0) == 0:
        if age < 6:
            return False
        state["resent"] = 1
        logger.info("Time sync %s: second pass (%.0fs/%.0fs)", player_id,
                    info.get("elapsed_ms", 0) / 1000, info.get("duration_ms", 0) / 1000)
        return True
    pos = _screen_pos.get(player_id)
    if not pos or not pos["playing"] or pos["offset"] is None or now - pos["t"] > 3:
        return False
    shown = pos["current"] - pos["offset"]
    if abs(shown - info.get("elapsed_ms", 0)) <= _TIME_TOLERANCE_MS or state["resent"] >= 4:
        return False
    state["resent"] += 1
    logger.info("Time sync %s: screen shows %.0fs, MA says %.0fs: resync", player_id,
                shown / 1000, info.get("elapsed_ms", 0) / 1000)
    return True


def _screen_report(device_id, player_id, current_ms, playing, offset):
    """Called on every refresh with the state written by the Video events."""
    now = _time.time()
    prev = _screen_pos.get(player_id)
    _screen_pos[player_id] = {"current": current_ms, "offset": offset, "playing": playing, "t": now}
    if prev is None or prev["playing"] == playing:
        return
    if now - _screen_started.get(player_id, 0) < 5:
        return      # the stream is starting
    expected = _expected_state.pop(player_id, None)
    if expected and expected[0] == playing and now - expected[1] < 15:
        return      # MA asked for it
    command = "resume" if playing else "pause"
    _threading.Thread(target=_forward_screen_command, args=(device_id, player_id, command),
                      daemon=True).start()


def _forward_screen_command(device_id, player_id, command):
    try:
        state = ma_control.get_queue_state(player_id)
        if (command == "pause" and state != "playing") or (command == "resume" and state != "paused"):
            logger.info("Screen %s on %s: MA already %s", command, player_id, state)
            return
        logger.info("Screen %s on %s: forwarding to MA", command, player_id)
        ma_control.mark_ma_triggered(device_id, command)
        if not ma_control.send_player_command(player_id, command):
            logger.warning("Failed to forward screen %s to MA player %s", command, player_id)
    except Exception:
        logger.exception("Failed to forward screen %s to MA", command)
''')
