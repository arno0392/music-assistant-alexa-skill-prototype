"""PATCH: a voice command no longer pauses Music Assistant.

When you speak to the Echo ("Alexa, suivant"), it pauses the screen's Video
while it listens. The skill took that for a pause pressed on the screen and
paused MA: right after, the "next" landed on a paused queue and playback
froze.

A pause/play seen on the screen is now forwarded to MA only after a short
delay, and dropped when a voice request reached the skill meanwhile (or just
before), when the screen went back to its previous state, or when a new
screen was rendered.

Requires fix_apl_followups.py.
usage: python3 fix_voice_pause.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "_last_intent_at" in src:
    print("lambda_function (pause vocale): deja patche")
    sys.exit(0)
edits = [
    ('''def _device_id_from(handler_input):
    try:
        return handler_input.request_envelope.context.system.device.device_id
    except Exception:
        return None
''', '''def _device_id_from(handler_input):
    try:
        device_id = handler_input.request_envelope.context.system.device.device_id
    except Exception:
        return None
    try:
        # voice requests: a pause seen on the screen meanwhile is the Echo listening
        if getattr(handler_input.request_envelope.request, "object_type", "") == "IntentRequest":
            import time as _t
            _last_intent_at[device_id] = _t.time()
    except Exception:
        pass
    return device_id
'''),
    ('''def _forward_screen_command(device_id, player_id, command):
    try:
        state = ma_control.get_queue_state(player_id)
''', '''def _forward_screen_command(device_id, player_id, command):
    try:
        seen_at = _time.time()
        screen = _screen_started.get(player_id, 0)
        if _SCREEN_FORWARD_DELAY:
            _time.sleep(_SCREEN_FORWARD_DELAY)
        if _last_intent_at.get(device_id, 0) > seen_at - 3:
            logger.info("Screen %s on %s: voice interaction, not forwarded", command, player_id)
            return
        pos = _screen_pos.get(player_id) or {}
        if _screen_started.get(player_id, 0) != screen or pos.get("playing") != (command == "resume"):
            logger.info("Screen %s on %s: screen changed meanwhile, not forwarded", command, player_id)
            return
        state = ma_control.get_queue_state(player_id)
'''),
]
for old, new in edits:
    assert src.count(old) == 1, f"lambda_function (pause vocale): code inattendu ({old[:50]!r})"
    src = src.replace(old, new)
src = src.rstrip("\n") + '''


_last_intent_at = {}        # device_id -> time of the last voice (intent) request
_SCREEN_FORWARD_DELAY = 6   # seconds before a pause/play seen on the screen goes to MA
'''
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (pause vocale): patch applique")
