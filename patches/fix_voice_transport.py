"""PATCH: "Alexa, suivant / précédent" handled by the screen's Video.

These voice commands never reach the skill: the Echo applies them itself to
the APL Video. With one flow stream as source, "previous" restarted it (MA
then restarted the current track) and "next" did the same: playback froze,
then MA relaunched it ~15 s later.

- "next": the Video now has a second, dummy source. Moving to it (voice
  "next", or the stream ending) sends UserEvent ["VoiceNext"]: the skill
  plays the track after the one shown. The dummy URL points to the skill's
  own host (fails fast, never touches MA).
- "previous": the Video restarts its stream, so its position jumps back while
  the same screen keeps playing: the skill then plays the previous track.

Requires fix_voice_pause.py.
usage: python3 fix_voice_transport.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]

# ---------------------------------------------------------------- apl_document.json
doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
if "VoiceNext" in json.dumps(doc):
    print("apl_document (commandes vocales): deja patche")
else:
    layout = doc["layouts"]["AudioPlayer"]
    layout["parameters"].append({"name": "audioNextSource", "type": "string",
                                 "description": "Dummy second source: moving to it means 'next'."})
    doc["mainTemplate"]["items"][0]["audioNextSource"] = "${audioNextSource}"
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
    assert len(videos) == 1 and videos[0]["source"] == "${audioSources}", "apl_document (commandes vocales): Video inattendue"
    video = videos[0]
    video["source"] = ["${audioSources}", "${audioNextSource}"]
    video.setdefault("onTrackUpdate", []).append({
        "type": "Sequential", "sequencer": "maVoice", "when": "${event.trackIndex == 1}",
        "commands": [{"type": "SendEvent", "arguments": ["VoiceNext"]}],
    })
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (commandes vocales): patch applique")


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


# ---------------------------------------------------------------- apl.py
patch_text(os.path.join(base, "skill", "apl.py"), "apl (commandes vocales)", "def _voice_next_url", [(
    '''            "secondaryText": metadata.get("secondaryText", "")
        })''',
    '''            "secondaryText": metadata.get("secondaryText", ""),
            "audioNextSource": _voice_next_url(audio_src)
        })''')], append='''

def _voice_next_url(audio_src):
    """Dummy second source of the Video (see the "VoiceNext" event)."""
    import os
    host = (os.environ.get("SKILL_HOSTNAME") or "").strip().rstrip("/")
    if host:
        if not host.startswith("http"):
            host = "https://" + host
        return host + "/ma-voice-next.mp3"
    return (audio_src or "") + "?ma_voice_next=1"
''')

# ---------------------------------------------------------------- lambda_function.py
patch_text(os.path.join(base, "skill", "lambda_function.py"), "lambda_function (commandes vocales)",
           "def _detect_voice_previous", [
    ('''        return bool(args) and args[0] in ("Next", "Previous")''',
     '''        return bool(args) and args[0] in ("Next", "Previous", "VoiceNext")'''),
    ('''        command = "next" if args[0] == "Next" else "previous"''',
     '''        # VoiceNext: the Video moved to its dummy second source ("Alexa, next", or stream end)
        command = {"Next": "next", "Previous": "previous", "VoiceNext": "advance"}[args[0]]'''),
    ("            if parts[1].strip() == 'end':\n",
     "            _detect_voice_previous(player_id, float(parts[0] or 0), parts[1].strip())\n"
     "            if parts[1].strip() == 'end':\n"),
], append='''

# "Alexa, précédent": the Echo restarts the Video's stream by itself.
_previous_handled = {}      # player_id -> screen start time already handled
_last_playing = {}          # player_id -> (position while playing, screen)


def _detect_voice_previous(player_id, current_ms, status):
    """status: 'true' playing, 'false' paused, 'end' stream ended."""
    screen = _screen_started.get(player_id, 0)
    if status == "end":
        _last_playing.pop(player_id, None)
        return
    if status != "true":
        return              # paused (the Echo pauses while listening): keep the last position
    last = _last_playing.get(player_id)
    _last_playing[player_id] = (current_ms, screen)
    if (not last or last[1] != screen or last[0] < 6000 or current_ms > last[0] - 4000
            or _previous_handled.get(player_id) == screen):
        return
    _previous_handled[player_id] = screen
    logger.info("Voice previous on %s: the screen restarted its stream (%.0fs -> %.0fs)",
                player_id, last[0] / 1000, current_ms / 1000)
    ref = _shown_item_id(player_id)
    _threading.Thread(target=lambda: ma_control.send_player_command(player_id, "previous", ref_item_id=ref),
                      daemon=True).start()
''')
