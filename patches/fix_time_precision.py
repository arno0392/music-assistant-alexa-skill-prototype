"""PATCH: exact track position on the screen (lyrics follow the voice).

The time shown (and the lyrics highlight) used MA's elapsed time, which lags:
MA corrects it from the screen's own reports, stamped when the skill received
them, i.e. up to ~1-2 s after the Video measured them. Lyrics were late.

1. Natural track change inside the flow stream: the new track starts exactly
   where the previous one ends, so its offset is the previous offset plus the
   previous duration (no MA round trip).
2. New screen whose stream starts at the beginning of a track (launch, next,
   previous): offset 0.
3. MA's elapsed is only used otherwise (stream started mid-track by MA itself).
4. The screen's report carries the device clock (utcTime), so the position
   given to MA (/alexa/playback-state observedAt) is stamped when measured.

Requires fix_root_id.py.
usage: python3 fix_time_precision.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]


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


# ---------------------------------------------------------------- apl_document.json
doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
OLD = "${event.currentTime}|${event.paused ? 'false' : 'true'}|${trackOffset}"
NEW = OLD + "|${utcTime}"
if NEW in json.dumps(doc):
    print("apl_document (horloge): deja patche")
else:
    count = 0

    def walk(x):
        global count
        if isinstance(x, dict):
            if x.get("componentId") == "maReport" and x.get("value") == OLD:
                x["value"] = NEW
                count += 1
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(doc)
    assert count >= 4, f"apl_document (horloge): {count} rapports trouves"
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (horloge): patch applique")

# ---------------------------------------------------------------- shared_store.py
patch_text(os.path.join(base, "shared_store.py"), "shared_store (horloge)", "observed_at=None", [(
    '''def set_report(player_id, activity, offset_ms, stream_url):
    with _live_lock:
        _reports[player_id] = {"activity": activity, "offsetMs": int(offset_ms),
                               "observedAt": _time.time(), "streamUrl": stream_url}''',
    '''def set_report(player_id, activity, offset_ms, stream_url, observed_at=None):
    with _live_lock:
        _reports[player_id] = {"activity": activity, "offsetMs": int(offset_ms),
                               "observedAt": observed_at or _time.time(), "streamUrl": stream_url}''')])

# ---------------------------------------------------------------- lambda_function.py
patch_text(os.path.join(base, "skill", "lambda_function.py"), "lambda_function (precision)", "def _flow_time_commands", [
    ('''            shared_store.set_report(player_id, 'PLAYING' if is_playing else 'PAUSED',
                                    float(parts[0] or 0),
                                    shared_store._rendered_stream.get(player_id))
''', '''            shared_store.set_report(player_id, 'PLAYING' if is_playing else 'PAUSED',
                                    float(parts[0] or 0),
                                    shared_store._rendered_stream.get(player_id),
                                    observed_at=_report_clock(parts))
'''),
    ('''    state["id"] = info["queue_item_id"]
    state["since"] = now
''', '''    prev_id, prev_duration = state.get("last_id"), state.get("last_duration")
    state["exact"] = False
    state["id"] = info["queue_item_id"]
    state["since"] = now
'''),
    ('''    if not info.get("duration_ms"):
        state["id"] = None   # MA does not know the duration yet: ask again
''', '''    if not info.get("duration_ms"):
        state["id"] = None   # MA does not know the duration yet: ask again
    else:
        state["last_id"], state["last_duration"] = info["queue_item_id"], info["duration_ms"]
'''),
    ('''    state["resent"] = 1          # no second pass: this offset is exact
''', '''    state["resent"] = 1          # no second pass: this offset is exact
    state["exact"] = True
'''),
    ('''    age = now - state.get("since", now)
''', '''    if state.get("exact"):
        return False     # offset computed exactly: MA's (later) elapsed would only degrade it
    age = now - state.get("since", now)
'''),
    ('''    return _seek_time_commands(player_id, state, info, now) or _apl_time_commands(info)
''', '''    return (_seek_time_commands(player_id, state, info, now)
            or _flow_time_commands(player_id, state, info, prev_id, prev_duration)
            or _apl_time_commands(info))
'''),
], append='''

# Exact offsets without MA's (late) elapsed time.
def _report_clock(parts):
    """Device clock of the screen's report, in seconds, if plausible."""
    try:
        stamp = float(parts[3]) / 1000.0
    except (IndexError, ValueError):
        return None
    return stamp if abs(_time.time() - stamp) < 10 else None


def _flow_time_commands(player_id, state, info, prev_id, prev_duration):
    pos = _screen_pos.get(player_id)
    if (prev_id and prev_duration and prev_id != info["queue_item_id"] and pos
            and pos.get("offset") is not None and _time.time() - pos["t"] < 5):
        offset, why = pos["offset"] + prev_duration, "right after the previous track"
    elif not prev_id and info.get("elapsed_ms", 10 ** 9) < 4000:
        offset, why = 0, "stream starts with the track"
    else:
        return None
    state["resent"] = 1
    state["exact"] = True
    total = info.get("duration_ms", 0)
    logger.info("Time sync %s: %s (offset %.1fs)", player_id, why, offset / 1000)
    return [
        {"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "trackTotal", "value": total},
        {"type": "SetValue", "componentId": "videoPlayer", "property": "trackOffset", "value": int(offset)},
        {"type": "SetValue", "componentId": "videoPlayer", "property": "needsResync", "value": False},
        {"type": "SetValue", "componentId": "slider", "property": "totalValue", "value": total},
    ]
''')
