"""PATCH: exact time after a seek made with the slider of the screen.

A seek restarts the flow stream at the requested position and the screen is
re-rendered: the Video starts again at 0. The time was then taken from MA,
which can still answer 0 (or the old position) at that moment, and the
second pass ~6 s later never applied if the user paused in between: the
slider stayed at 0 while the music had moved on.

When the new stream comes from our own seek, the track offset is now set
directly from the requested position (no MA round trip), and the "screen vs
MA" check waits 8 s after a new screen before correcting anything.

Requires fix_apl_followups.py.
usage: python3 fix_seek_offset.py SRC_DIR
"""
import os
import sys

base = sys.argv[1]
path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "def _seek_time_commands" in src:
    print("lambda_function (seek): deja patche")
    sys.exit(0)

edits = [
    ('''            logger.info("Live page %s: seek to %.1fs", player_id, seconds)
            ma_control.seek_player(player_id, seconds)
''', '''            logger.info("Live page %s: seek to %.1fs", player_id, seconds)
            _seek_hint[player_id] = (seconds, _time.time(), _shown_item_id(player_id))
            ma_control.seek_player(player_id, seconds)
'''),
    ("\n    return _apl_time_commands(info)\n",
     "\n    return _seek_time_commands(player_id, state, info, now) or _apl_time_commands(info)\n"),
    ('''    pos = _screen_pos.get(player_id)
    if not pos or not pos["playing"]''', '''    pos = _screen_pos.get(player_id)
    if age < 8 or not pos or not pos["playing"]'''),
]
for old, new in edits:
    assert src.count(old) == 1, f"lambda_function (seek): code inattendu, patch non applique ({old[:60]!r})"
    src = src.replace(old, new)

src = src.rstrip("\n") + '''


# PATCH: the stream restarted at the position asked with the slider.
_seek_hint = {}     # player_id -> (seconds, time, queue item shown when seeking)


def _seek_time_commands(player_id, state, info, now):
    hint = _seek_hint.pop(player_id, None)
    if not hint or now - hint[1] > 20 or hint[2] != info.get("queue_item_id"):
        return None
    state["resent"] = 1          # no second pass: this offset is exact
    total = info.get("duration_ms", 0)
    logger.info("Time sync %s: new stream starts at the seek position %.0fs", player_id, hint[0])
    return [
        {"type": "SetValue", "componentId": "MaTimeRoot", "property": "trackTotal", "value": total},
        {"type": "SetValue", "componentId": "MaTimeRoot", "property": "trackOffset",
         "value": -int(hint[0] * 1000)},
        {"type": "SetValue", "componentId": "MaTimeRoot", "property": "needsResync", "value": False},
        {"type": "SetValue", "componentId": "slider", "property": "totalValue", "value": total},
    ]
'''
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (seek): patch applique")
