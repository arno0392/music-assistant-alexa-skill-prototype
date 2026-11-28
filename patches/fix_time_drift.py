"""PATCH: no drift of the time (and lyrics) over many tracks of one flow stream.

On a natural track change the new track's start in the stream is "previous start +
previous duration". MA gives durations rounded to the second, so each change adds up
to ~1 s of error, and the result was trusted as exact: after ten tracks the time and
the lyrics were seconds early or late (Echo Show and TV). Now, 10 to 45 s into a track
reached that way, the screen and MA are compared at the same instant and the track's
start in the stream is moved by the difference (once per track, from 0.3 s). Moving the
start, not copying MA's position, is free of the delay before the screen applies it.

usage: python3 fix_time_drift.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "def _time_drift(" in src:
    print("lambda_function (derive du temps): deja patche")
    sys.exit(0)

edits = [
    ('''    state["resent"] = 1
    state["exact"] = True
    total = info.get("duration_ms", 0)''',
     '''    state["resent"] = 1
    state["exact"] = True
    state["drift_check"] = why == "right after the previous track"
    state["drift_done"] = 0
    total = info.get("duration_ms", 0)'''),
    ('''    if state.get("exact"):
        return False     # offset computed exactly: MA's (later) elapsed would only degrade it''',
     '''    if state.get("exact") and state.get("drift_check"):
        return _time_drift(player_id, state, info, now)
    if state.get("exact"):
        return False     # offset computed exactly: MA's (later) elapsed would only degrade it'''),
    ('''def _time_needs_resend(''',
     '''_DRIFT_TOLERANCE_MS = 300


def _time_drift(player_id, state, info, now):
    """A track reached by a natural change: its start adds rounded durations, check it on MA."""
    age = now - state.get("since", now)
    if age < 10 or age > _TIME_WINDOW or state.get("drift_done", 0) >= 1:
        return False
    pos = _screen_pos.get(player_id)
    elapsed = info.get("elapsed_ms")
    if not elapsed or not pos or not pos["playing"] or pos["offset"] is None or now - pos["t"] > 3:
        return False
    shown = pos["current"] - pos["offset"] + (now - pos["t"]) * 1000
    state["drift_done"] = 1              # one measure per track: a second one would chase noise
    if abs(shown - elapsed) <= _DRIFT_TOLERANCE_MS:
        logger.info("Time sync %s: drift check %.1fs after natural track changes: ok", player_id,
                    (shown - elapsed) / 1000)
        return False
    state["drift_offset"] = pos["offset"] + (shown - elapsed)
    logger.info("Time sync %s: drift of %.1fs after natural track changes (screen %.1fs, MA %.1fs): "
                "track start moved to %.1fs", player_id, (shown - elapsed) / 1000, shown / 1000,
                elapsed / 1000, state["drift_offset"] / 1000)
    return True


def _time_needs_resend('''),
    ('''    if info["queue_item_id"] == state["id"]:
        return _apl_time_commands(info) if _time_needs_resend(player_id, state, info, now) else None''',
     '''    if info["queue_item_id"] == state["id"]:
        if not _time_needs_resend(player_id, state, info, now):
            return None
        moved = state.pop("drift_offset", None)
        if moved is not None:     # move the track start, free of the screen's delay
            return [{"type": "SetValue", "componentId": "videoPlayer", "property": "trackOffset",
                     "value": int(moved)}]
        return _apl_time_commands(info)'''),
]
for old, new in edits:
    assert src.count(old) == 1, old[:60]
    src = src.replace(old, new, 1)
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (derive du temps): patch applique")
