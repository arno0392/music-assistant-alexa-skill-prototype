"""PATCH: safety net for the screen's time: never show more than the track's duration.

The screen shows "position in the stream - start of the track in the stream". If that
start is ever lost (seen on an Echo Show after ~10 tracks of one flow stream: 50 min shown
on a 3 min track), the time stayed wrong until the next track, because the checks only
run in the first 45 s of a track. Now, at any time, a screen showing a position beyond the
track's duration (or before its start) is resynced from MA's elapsed time, at most every 20 s.

usage: python3 fix_time_sanity.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "def _time_out_of_track(" in src:
    print("lambda_function (temps hors morceau): deja patche")
    sys.exit(0)

old = '''    answered 0 at first), then whenever the screen is more than 3 s off."""
    if state.get("exact"):'''
assert src.count(old) == 1, "_time_needs_resend not found"
src = src.replace(old, '''    answered 0 at first), then whenever the screen is more than 3 s off."""
    if _time_out_of_track(player_id, state, info, now):
        return True
    if state.get("exact"):''')

old = "def _time_needs_resend("
src = src.replace(old, '''def _time_out_of_track(player_id, state, info, now):
    """The screen shows a time outside the track (its start in the stream was lost)."""
    pos = _screen_pos.get(player_id)
    duration = info.get("duration_ms") or 0
    if (not duration or not pos or not pos["playing"] or pos["offset"] is None
            or now - pos["t"] > 3 or now - state.get("sane_at", 0) < 20
            or now - state.get("since", 0) < 10):     # the screen may not report the new offset yet
        return False
    shown = pos["current"] - pos["offset"]
    if -5000 <= shown <= duration + 5000:
        return False
    state["sane_at"] = now
    state["exact"] = False
    logger.info("Time sync %s: screen shows %.0fs on a %.0fs track: resync from MA (%.0fs)", player_id,
                shown / 1000, duration / 1000, info.get("elapsed_ms", 0) / 1000)
    return True


def _time_needs_resend(''', 1)
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (temps hors morceau): patch applique")
