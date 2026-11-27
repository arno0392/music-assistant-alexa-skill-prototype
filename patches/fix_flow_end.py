"""PATCH: keep playing when MA ends the flow stream between two tracks.

In "smart" sample-rate mode MA 2.11 ends the flow stream when the next track
needs a higher sample rate ("breaking out to restart flow stream") and waits
for the player to finish before starting a new flow. MA never learns that the
Echo finished (its Alexa provider maps every Echo state to PLAYING/PAUSED),
and denies the Echo's new request for the finished stream: playback stopped.

The Video's onEnd now reports "end". When the stream ends while MA still
says "playing", and MA has not pushed a new stream within a few seconds, the
skill starts the track after the one shown (play_index), which makes MA push
a new flow. The end is not forwarded to MA as a pause.

Requires fix_lyrics_keep.py.
usage: python3 fix_flow_end.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
REPORT = "${event.currentTime}|${event.paused ? 'false' : 'true'}|${trackOffset}|${utcTime}|${lyricsVisible ? 1 : 0}"
END = "${event.currentTime}|end|${trackOffset}|${utcTime}|${lyricsVisible ? 1 : 0}"

doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
videos = []


def walk(x):
    if isinstance(x, dict):
        if x.get("type") == "Video" and x.get("id") == "videoPlayer":
            videos.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)


walk(doc)
assert len(videos) == 1, "apl_document (fin de flux): Video introuvable"
on_end = videos[0]["onEnd"]
if any(c.get("value") == END for c in on_end):
    print("apl_document (fin de flux): deja patche")
else:
    hits = [c for c in on_end if c.get("componentId") == "maReport" and c.get("value") == REPORT]
    assert len(hits) == 1, "apl_document (fin de flux): rapport onEnd introuvable"
    hits[0]["value"] = END
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (fin de flux): patch applique")


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


patch_text(os.path.join(base, "skill", "ma_control.py"), "ma_control (fin de flux)", '"advance"', [
    ('SUPPORTED_COMMANDS = ("next", "previous", "start_over", "pause", "stop", "resume")',
     'SUPPORTED_COMMANDS = ("next", "previous", "start_over", "pause", "stop", "resume", "advance")'),
    ('            elif command == "start_over":\n',
     '            elif command == "advance":\n'
     '                # next track after the one shown (the flow stream ended)\n'
     '                await _play_relative_index(client, player_id, 1, ref_item_id)\n'
     '            elif command == "start_over":\n'),
])

patch_text(os.path.join(base, "skill", "lambda_function.py"), "lambda_function (fin de flux)", "def _stream_ended", [(
    "            _screen_report(device_id, player_id, float(parts[0] or 0), is_playing, offset)\n",
    "            if parts[1].strip() == 'end':\n"
    "                _expected_state[player_id] = (False, _time.time())   # not a pause\n"
    "                _stream_ended(player_id)\n"
    "            _screen_report(device_id, player_id, float(parts[0] or 0), is_playing, offset)\n")],
    append='''

# The flow stream ended on the screen (see fix_flow_end.py).
_END_GRACE = 3          # seconds left to MA to push a new stream by itself
_end_handled = {}       # player_id -> screen start time already handled


def _stream_ended(player_id):
    screen = _screen_started.get(player_id, 0)
    if _end_handled.get(player_id) == screen:
        return
    _end_handled[player_id] = screen
    _threading.Thread(target=_continue_after_end, args=(player_id, screen), daemon=True).start()


def _continue_after_end(player_id, screen):
    import shared_store
    try:
        _time.sleep(_END_GRACE)
        if _screen_started.get(player_id, 0) != screen or 'stream' in (shared_store._pending.get(player_id) or []):
            logger.info("Stream ended on %s: MA already sent a new stream", player_id)
            return
        state = ma_control.get_queue_state(player_id)
        if state != "playing":
            logger.info("Stream ended on %s: MA is %s, nothing to continue", player_id, state)
            return
        logger.info("Stream ended on %s while MA plays: starting the next track", player_id)
        ma_control.send_player_command(player_id, "advance", ref_item_id=_shown_item_id(player_id))
    except Exception:
        logger.exception("Failed to continue after the end of the stream on %s", player_id)
''')
