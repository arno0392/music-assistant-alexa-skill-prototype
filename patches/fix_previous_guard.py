"""PATCH: no "voice previous" from the first seconds of a new screen.

A voice "previous" is detected when the screen restarts its stream on the same page.
When a new page replaces the old one, a TV can still send one last report from the
old page (position ~10 s) after the new page is registered; the new page then reports
~1 s, which looked like a restart: a "previous" was sent and the next track was undone
(seen on a Samsung TV: "next" played a quarter of a second, then went back).
Positions are now recorded only once the page is 5 s old.

usage: python3 fix_previous_guard.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "_PREVIOUS_GUARD_S" in src:
    print("lambda_function (garde precedent): deja patche")
    sys.exit(0)
old = '''    if status != "true":
        return              # paused (the Echo pauses while listening): keep the last position
    last = _last_playing.get(player_id)'''
assert src.count(old) == 1, "_detect_voice_previous not found"
src = src.replace(old, '''    if status != "true":
        return              # paused (the Echo pauses while listening): keep the last position
    if _time.time() - screen < _PREVIOUS_GUARD_S:
        _last_playing.pop(player_id, None)    # a late report of the old page may still arrive
        return
    last = _last_playing.get(player_id)''')
src = src.replace("_previous_handled = {}      # player_id", "_PREVIOUS_GUARD_S = 5\n_previous_handled = {}      # player_id", 1)
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (garde precedent): patch applique")
