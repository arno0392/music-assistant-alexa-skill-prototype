"""PATCH: no drift of the time (and lyrics) over many tracks of one flow stream.

On a natural track change the new track's start in the stream is "previous start +
previous duration". MA gives durations rounded to the second, so each change adds up
to ~1 s of error, and the result was trusted as exact: after ten tracks the time and
the lyrics were seconds early or late (Echo Show and TV). Now, 10 to 45 s into a track
reached that way, the screen and MA are compared at each poll (MA's position alone varies
by 1-2 s), and the track's start in the stream is moved by the median of six differences
(once per track, from 0.3 s). Moving the start, not copying MA's position, is free of the
delay before the screen applies it.

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
    state["drift_samples"] = []
    total = info.get("duration_ms", 0)'''),
    ('''    if state.get("exact"):
        return False     # offset computed exactly: MA's (later) elapsed would only degrade it''',
     '''    if state.get("exact") and state.get("drift_check"):
        return _time_drift(player_id, state, info, now)
    if state.get("exact"):
        return False     # offset computed exactly: MA's (later) elapsed would only degrade it'''),
    ('''def _time_needs_resend(''',
     '''_DRIFT_TOLERANCE_MS = 300
_DRIFT_SAMPLES = 6


def _time_drift(player_id, state, info, now):
    """A track reached by a natural change: its start adds rounded durations, check it on MA."""
    age = now - state.get("since", now)
    if age < 8 or state.get("drift_done", 0) >= 1:
        return False
    samples = state.setdefault("drift_samples", [])
    pos = _screen_pos.get(player_id)
    elapsed = info.get("elapsed_ms")
    if age <= _TIME_WINDOW and elapsed and pos and pos["playing"] and pos["offset"] is not None \
            and now - pos["t"] <= 3:
        samples.append(pos["current"] - pos["offset"] + (now - pos["t"]) * 1000 - elapsed)
    if len(samples) < _DRIFT_SAMPLES and age <= _TIME_WINDOW:
        return False                     # MA's position varies by ~1-2 s: take several
    state["drift_done"] = 1
    if len(samples) < 3 or not pos or pos["offset"] is None:
        return False
    ordered = sorted(samples)
    median = ordered[len(ordered) // 2]
    if abs(median) <= _DRIFT_TOLERANCE_MS:
        logger.info("Time sync %s: drift check %.1fs after natural track changes (%d samples, %.1f to %.1fs): ok",
                    player_id, median / 1000, len(ordered), ordered[0] / 1000, ordered[-1] / 1000)
        return False
    state["drift_offset"] = pos["offset"] + median
    logger.info("Time sync %s: drift of %.1fs after natural track changes (%d samples, %.1f to %.1fs): "
                "track start moved to %.1fs", player_id, median / 1000, len(ordered), ordered[0] / 1000,
                ordered[-1] / 1000, state["drift_offset"] / 1000)
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
