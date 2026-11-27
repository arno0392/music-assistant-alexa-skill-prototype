"""PATCH: the flow stream ran out at the end of a track: play the next one.

When MA ends the flow stream before a track it cannot add (sample rate change
in "smart" mode), the Echo does not see an "end": its HTTP stream just runs
dry and the Video pauses at the end of the current track. The skill took
that for a pause (MA then showed paused) and playback stopped.

A pause seen on the screen within the last seconds of the track shown now
starts the next track instead of being forwarded as a pause.

Requires fix_voice_pause.py and fix_time_precision.py.
usage: python3 fix_stream_ran_out.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "_ran_out_at_track_end" in src:
    print("lambda_function (flux epuise): deja patche")
    sys.exit(0)
old = '''            logger.info("Screen %s on %s: screen changed meanwhile, not forwarded", command, player_id)
            return
        state = ma_control.get_queue_state(player_id)
'''
assert src.count(old) == 1, "lambda_function (flux epuise): code inattendu"
src = src.replace(old, '''            logger.info("Screen %s on %s: screen changed meanwhile, not forwarded", command, player_id)
            return
        if command == "pause" and _ran_out_at_track_end(player_id, pos):
            logger.info("Screen paused at the end of the track on %s: stream ran out, starting the next track",
                        player_id)
            ma_control.send_player_command(player_id, "advance", ref_item_id=_shown_item_id(player_id))
            return
        state = ma_control.get_queue_state(player_id)
''')
src = src.rstrip("\n") + '''


_RAN_OUT_MARGIN_MS = 4000


def _ran_out_at_track_end(player_id, pos):
    """The screen paused within the last seconds of the track it shows."""
    st = _now_playing_state.get(player_id) or {}
    duration = st.get("last_duration")
    if not duration or not pos or pos.get("offset") is None:
        return False
    shown = pos["current"] - pos["offset"]
    return shown >= duration - _RAN_OUT_MARGIN_MS
'''
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (flux epuise): patch applique")
