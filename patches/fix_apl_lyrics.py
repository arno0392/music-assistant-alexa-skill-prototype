"""PATCH: synchronized lyrics on the Echo Show screen.

A lyrics button (microphone) next to the skip buttons, shown only when the
track has lyrics, swaps the cover/title for a lyrics panel. The current line
is white, the others dimmed; the panel scrolls to keep the current line in
view. Plain (unsynchronized) lyrics are shown as scrollable text.

- Lyrics come from Music Assistant ("metadata/get_track_lyrics": Deezer's
  synchronized lyrics, LRCLIB, Genius...), fetched in the background at each
  track change.
- The screen highlights the current line by itself, from its own position
  (bind trackPos on MaTimeRoot, updated by the Video at every time update).
- The skill scrolls the panel (ScrollToIndex) when the current line changes.

The Sequence has a fixed number of slots (MAX_LINES) whose text and display
follow the "lyricsLines" bind, so new lyrics need no re-render.

Requires fix_apl_background.py (applied last before this one).
usage: python3 fix_apl_lyrics.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
MAX_LINES = 200

# ---------------------------------------------------------------- apl_document.json
doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
if "maLyrics" in json.dumps(doc):
    print("apl_document (paroles): deja patche")
else:
    root = doc["layouts"]["AudioPlayer"]["item"][0]
    assert root.get("id") == "MaTimeRoot", "fix_apl_time.py doit etre applique avant"
    root["bind"] += [
        {"name": "lyricsLines", "type": "any", "value": []},
        {"name": "lyricsVisible", "type": "boolean", "value": False},
        {"name": "lyricsAvailable", "type": "boolean", "value": False},
        {"name": "lyricsSynced", "type": "boolean", "value": False},
        {"name": "lyricsIndex", "type": "number", "value": 0},
        {"name": "trackPos", "type": "number", "value": 0},
    ]

    found = {}

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "Video" and x.get("id") == "videoPlayer":
                found["video"] = x
            if x.get("id") == "MaSkipButtons":
                found["buttons"] = x
            if x.get("description") == "Cover image and track info":
                found["cover"] = x
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(doc)
    assert set(found) == {"video", "buttons", "cover"}, f"apl_document (paroles): trouve {sorted(found)}"

    # 1. the Video publishes the track position
    upd = found["video"]["onTimeUpdate"]
    pos = next(i for i, c in enumerate(upd) if c.get("when") == "${needsResync}") + 1
    upd.insert(pos, {"type": "SetValue", "componentId": "MaTimeRoot", "property": "trackPos",
                     "value": "${event.currentTime - trackOffset}"})

    # 2. cover row hidden while the lyrics are shown, lyrics panel right after it
    found["cover"]["display"] = "${lyricsVisible ? 'none' : 'normal'}"
    current = ("${data < lyricsLines.length && lyricsLines[data].s >= 0 && trackPos >= lyricsLines[data].s"
               " && trackPos < lyricsLines[data].e}")
    panel = {
        "type": "Container",
        "id": "maLyricsPanel",
        "description": "Lyrics",
        "width": "100%",
        "height": "46vh",
        "paddingLeft": "@marginHorizontal",
        "paddingRight": "@marginHorizontal",
        "display": "${lyricsVisible ? 'normal' : 'none'}",
        "items": [{
            "type": "Sequence",
            "id": "maLyrics",
            "width": "100%",
            "height": "100%",
            "scrollDirection": "vertical",
            "data": f"${{Array.range({MAX_LINES})}}",
            "item": {
                "type": "Text",
                "width": "100%",
                "paddingTop": "6dp",
                "paddingBottom": "6dp",
                "display": "${data < lyricsLines.length ? 'normal' : 'none'}",
                "text": "${data < lyricsLines.length ? lyricsLines[data].t : ''}",
                "textAlign": "center",
                "fontSize": "${lyricsSynced ? '30dp' : '24dp'}",
                "fontWeight": "${lyricsSynced ? 'bold' : 'normal'}",
                "color": "${" + current[2:-1] + " ? '#FFFFFF' : (lyricsSynced ? '#FFFFFF66' : '#FFFFFFDD')}",
            },
        }],
    }
    parent = None

    def find_parent(x):
        global parent
        if isinstance(x, dict):
            for key in ("items", "item"):
                lst = x.get(key)
                if isinstance(lst, list) and any(c is found["cover"] for c in lst):
                    parent = lst
            for v in x.values():
                find_parent(v)
        elif isinstance(x, list):
            for v in x:
                find_parent(v)

    find_parent(doc)
    assert parent is not None, "apl_document (paroles): parent de la pochette introuvable"
    parent.insert(parent.index(found["cover"]) + 1, panel)

    # 3. lyrics button after the "next" button
    found["buttons"]["items"].append({
        "type": "TouchWrapper",
        "id": "maLyricsButton",
        "width": "@secondaryControlSize",
        "height": "@secondaryControlSize",
        "spacing": "@spacingMedium",
        "display": "${lyricsAvailable ? 'normal' : 'invisible'}",
        "onPress": [
            {"type": "SetValue", "componentId": "MaTimeRoot", "property": "lyricsVisible",
             "value": "${!lyricsVisible}"},
            {"type": "ScrollToIndex", "componentId": "maLyrics", "index": "${lyricsIndex}",
             "align": "center", "when": "${lyricsVisible}"},
        ],
        "item": {"type": "VectorGraphic", "source": "maLyrics", "width": "100%", "height": "100%",
                 "scale": "best-fit", "opacity": "${lyricsVisible ? 1 : 0.6}"},
    })

    # 4. icon: microphone (Material Design "microphone-variant", as in Music Assistant)
    doc["graphics"]["maLyrics"] = {
        "type": "AVG", "version": "1.2", "width": 24, "height": 24,
        "items": [
            {"type": "path", "fill": "white",
             "pathData": "M9,3A4,4 0 0,1 13,7H5A4,4 0 0,1 9,3M11.84,9.82L11,18H10V19A2,2 0 0,0 12,21"
                         "A2,2 0 0,0 14,19V14A4,4 0 0,1 18,10H20L19,11L20,12H18A2,2 0 0,0 16,14V19"
                         "A4,4 0 0,1 12,23A4,4 0 0,1 8,19V18H7L6.16,9.82C5.67,9.32 5.31,8.7 5.13,8"
                         "H12.87C12.69,8.7 12.33,9.32 11.84,9.82Z"},
        ],
    }
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (paroles): patch applique")


def patch_text(path, label, marker, edits, append=None):
    src = open(path, encoding="utf-8").read()
    if marker in src:
        print(f"{label}: deja patche")
        return
    for old, new in edits:
        assert src.count(old) == 1, f"{label}: code inattendu, patch non applique ({old[:60]!r})"
        src = src.replace(old, new)
    if append:
        src = src.rstrip("\n") + "\n" + append
    open(path, "w", encoding="utf-8").write(src)
    print(f"{label}: patch applique")


# ---------------------------------------------------------------- ma_control.py
patch_text(os.path.join(base, "skill", "ma_control.py"), "ma_control (paroles)", "def get_lyrics", [], append='''

# Lyrics of the current track of a player: {"queue_item_id", "lyrics", "lrc"} or None.
async def _get_lyrics(server_url, token, player_id):
    async with aiohttp.ClientSession() as session:
        async with MusicAssistantClient(server_url, session, token=token) as client:
            queue = await client.player_queues.get_active_queue(player_id)
            item = queue.current_item if queue else None
            track = getattr(item, "media_item", None)
            if track is None:
                return None
            lyrics = lrc = None
            try:
                result = await client.send_command("metadata/get_track_lyrics", track=track)
                if result:
                    lyrics, lrc = result[0], result[1]
            except Exception:
                logger.debug("metadata/get_track_lyrics failed", exc_info=True)
            if not (lyrics or lrc):
                meta = getattr(track, "metadata", None)
                lyrics = getattr(meta, "lyrics", None)
                lrc = getattr(meta, "lrc_lyrics", None)
            return {"queue_item_id": item.queue_item_id, "lyrics": lyrics, "lrc": lrc}


def get_lyrics(player_id):
    server_url = get_env_secret("MA_API_URL")
    token = get_env_secret("MA_API_TOKEN")
    if not server_url or not player_id:
        return None
    try:
        return asyncio.run(_get_lyrics(server_url, token, player_id))
    except Exception:
        logger.debug("get_lyrics failed for %s", player_id, exc_info=True)
        return None
''')


# ---------------------------------------------------------------- lambda_function.py
patch_text(os.path.join(base, "skill", "lambda_function.py"), "lambda_function (paroles)", "def _lyrics_commands", [
    ('''        try:
            time_commands = _sync_now_playing_from_ma(handler_input)
        except Exception:
            logger.exception("Failed to sync now playing from MA")
''', '''        try:
            time_commands = _sync_now_playing_from_ma(handler_input)
        except Exception:
            logger.exception("Failed to sync now playing from MA")
        try:
            time_commands = (time_commands or []) + _lyrics_commands(handler_input)
        except Exception:
            logger.exception("Failed to update the lyrics")
'''),
    ('''def _screen_restarted(player_id):
''', '''def _screen_restarted(player_id):
    _lyrics_screen_reset(player_id)
'''),
], append='''

# Synchronized lyrics on the screen (see apl_document: maLyrics).
import os
import re as _re
_lyrics_state = {}      # player_id -> {"id", "lines", "synced", "ready", "sent", "idx"}
_LRC_TAG = _re.compile(r"\\[(\\d{1,3}):(\\d{1,2}(?:[.:]\\d{1,3})?)\\]")
_LYRICS_MAX_LINES = 200


def _parse_lyrics(lyrics, lrc):
    """-> (lines [{"s", "e", "t"}], synced). s/e in ms, -1 when not synchronized."""
    if lrc:
        timed = []
        for raw in lrc.splitlines():
            stamps = _LRC_TAG.findall(raw)
            text = _LRC_TAG.sub("", raw).strip()
            for minutes, seconds in stamps:
                ms = int(minutes) * 60000 + int(round(float(seconds.replace(":", ".")) * 1000))
                timed.append((ms, text))
        timed.sort(key=lambda x: x[0])
        if timed:
            # lines lit slightly early: what the Echo reports is decoded a bit before it is heard
            # and a reader needs the line a moment before it is sung (LYRICS_LEAD_MS, default 600)
            try:
                lead = int(os.environ.get("LYRICS_LEAD_MS", "600"))
            except ValueError:
                lead = 600
            lines = []
            for i, (start, text) in enumerate(timed[:_LYRICS_MAX_LINES]):
                end = timed[i + 1][0] if i + 1 < len(timed) else 10 ** 9
                s0 = max(0, start - lead)
                lines.append({"s": s0, "e": max(end - lead, s0 + 1), "t": text or "\\u266a"})
            return lines, True
    if lyrics:
        lines = [{"s": -1, "e": -1, "t": t.strip()} for t in lyrics.strip().splitlines()]
        return lines[:_LYRICS_MAX_LINES], False
    return [], False


def _lyrics_screen_reset(player_id):
    st = _lyrics_state.get(player_id)
    if st:
        st["sent"] = False
        st["idx"] = -2


def _fetch_lyrics(player_id, st):
    try:
        found = ma_control.get_lyrics(player_id)
        if found and found.get("queue_item_id") == st["id"]:
            st["lines"], st["synced"] = _parse_lyrics(found.get("lyrics"), found.get("lrc"))
        logger.info("Lyrics %s: %d lines (%s)", player_id, len(st["lines"]),
                    "synced" if st["synced"] else "plain" if st["lines"] else "none")
    except Exception:
        logger.exception("Failed to fetch lyrics for %s", player_id)
    st["ready"] = True


def _set_root(prop, value):
    return {"type": "SetValue", "componentId": "MaTimeRoot", "property": prop, "value": value}


def _lyrics_commands(handler_input):
    player_id = device_mapping.get_player_for_device(_device_id_from(handler_input))
    current = _shown_item_id(player_id) if player_id else None
    if not current:
        return []
    st = _lyrics_state.get(player_id)
    commands = []
    if st is None or st["id"] != current:
        st = {"id": current, "lines": [], "synced": False, "ready": False, "sent": False, "idx": -2}
        _lyrics_state[player_id] = st
        commands += [_set_root("lyricsAvailable", False), _set_root("lyricsLines", [])]
        _threading.Thread(target=_fetch_lyrics, args=(player_id, st), daemon=True).start()
    if not st["ready"]:
        return commands
    if not st["sent"]:
        st["sent"] = True
        st["idx"] = -2
        commands += [_set_root("lyricsLines", st["lines"]),
                     _set_root("lyricsSynced", st["synced"]),
                     _set_root("lyricsAvailable", bool(st["lines"])),
                     _set_root("lyricsIndex", 0)]
        if not st["lines"]:
            commands.append(_set_root("lyricsVisible", False))
        else:
            commands.append({"type": "ScrollToIndex", "componentId": "maLyrics", "index": 0, "align": "first"})
    if st["synced"] and st["lines"]:
        pos = _screen_pos.get(player_id)
        if pos and pos.get("offset") is not None:
            shown = pos["current"] - pos["offset"]
            idx = 0
            for i, line in enumerate(st["lines"]):
                if line["s"] <= shown:
                    idx = i
                else:
                    break
            if idx != st["idx"]:
                st["idx"] = idx
                commands += [_set_root("lyricsIndex", idx),
                             {"type": "ScrollToIndex", "componentId": "maLyrics", "index": idx,
                              "align": "center"}]
    return commands
''')
