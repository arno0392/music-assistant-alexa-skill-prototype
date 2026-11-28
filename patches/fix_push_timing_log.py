"""PATCH: log the track timing MA sends on /ma/push-url (queueItemId, durationMs, elapsedMs).

Lets a test on a real Echo show what an MA with the track-info change sends; nothing
else uses these fields yet.

usage: python3 fix_push_timing_log.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "music_assistant_api", "ma_routes.py")
src = open(path, encoding="utf-8").read()
if "MA timing" in src:
    print("ma_routes (log timing): deja patche")
    sys.exit(0)
old = '''            _ma_log.info("push-url %s: pageLive=%s (%s)", player_id, live,'''
assert src.count(old) == 1, "push-url log not found"
src = src.replace(old, '''            if any(k in data for k in ('queueItemId', 'durationMs', 'elapsedMs')):
                _ma_log.info("push-url %s: MA timing item=%s duration=%sms elapsed=%sms", player_id,
                             data.get('queueItemId'), data.get('durationMs'), data.get('elapsedMs'))
            _ma_log.info("push-url %s: pageLive=%s (%s)", player_id, live,''')
open(path, "w", encoding="utf-8").write(src)
print("ma_routes (log timing): patch applique")
