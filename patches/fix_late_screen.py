"""PATCH: right time when the device opens the screen late (app or screen off).

MA starts the track and its clock at once; a device that first has to start the
skill (a TV with the Alexa app closed, an Echo waking up) starts the stream ~10-15 s
later, from the beginning of the track. The first sync took MA's elapsed time (15 s)
while the music had just begun. MA's push now records when each new stream was
pushed and with which title; on a new screen, if MA was at the start of the track
when that stream was pushed and the screen's player is clearly behind MA, the stream
starts with the track: offset 0, exact.

usage: python3 fix_late_screen.py SRC_DIR
"""
import os
import sys

base = sys.argv[1]
path = os.path.join(base, "music_assistant_api", "ma_routes.py")
src = open(path, encoding="utf-8").read()
if "'streamAt'" in src:
    print("ma_routes (ecran ouvert en retard): deja patche")
else:
    old = """        shared_store._version += 1
        shared_store._store = {"""
    assert src.count(old) == 1, "push-url store not found"
    src = src.replace(old, """        _prev = shared_store._store or {}
        _same_stream = bool(_prev.get('streamAt')) and shared_store.stream_key(
            _prev.get('streamUrl')) == shared_store.stream_key(stream_url)
        shared_store._version += 1
        shared_store._store = {""")
    old = """            'timestamp': time.time()
        }
"""
    assert src.count(old) == 1, "push-url timestamp not found"
    src = src.replace(old, """            'timestamp': time.time()
        }
        # when this stream was pushed, and its first title (a metadata upload keeps the stream)
        shared_store._store['streamAt'] = _prev['streamAt'] if _same_stream else time.time()
        shared_store._store['streamTitle'] = _prev.get('streamTitle') if _same_stream else data.get('title')
""")
    open(path, "w", encoding="utf-8").write(src)
    print("ma_routes (ecran ouvert en retard): patch applique")

path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "def _late_screen_on_fresh_stream(" in src:
    print("lambda_function (ecran ouvert en retard): deja patche")
    sys.exit(0)
old = '''    elif not prev_id and info.get("elapsed_ms", 10 ** 9) < 4000:
        offset, why = 0, "stream starts with the track"
    else:
        return None'''
assert src.count(old) == 1, "_flow_time_commands not found"
src = src.replace(old, '''    elif not prev_id and info.get("elapsed_ms", 10 ** 9) < 4000:
        offset, why = 0, "stream starts with the track"
    elif ((not prev_id or prev_id == info["queue_item_id"])
          and (late := _late_screen_on_fresh_stream(player_id, info)) is not False):
        if late is None:
            state["id"] = None   # ask again at the next refresh, once the screen reports
            return [{"type": "Idle", "delay": 0}]
        offset, why = 0, "stream starts with the track, opened %.0fs after MA started it" % (
            info.get("elapsed_ms", 0) / 1000)
    else:
        return None''')
old = "def _flow_time_commands("
src = src.replace(old, '''def _late_screen_on_fresh_stream(player_id, info):
    """The screen plays, from its start, a stream MA pushed at the start of this track."""
    import shared_store
    store = shared_store.store_for(player_id) or {}
    pushed = store.get("streamAt")
    rendered = shared_store._rendered_stream.get(player_id)
    if (not pushed or not store.get("streamUrl") or (store.get("streamTitle") or "") != (info.get("title") or "")
            or shared_store.stream_key(rendered) != shared_store.stream_key(store["streamUrl"])):
        return False
    elapsed = info.get("elapsed_ms", 0)
    if elapsed - (_time.time() - pushed) * 1000 > 4000:
        return False             # MA was already into the track when it pushed this stream
    pos = _screen_pos.get(player_id)
    if not pos or _time.time() - pos["t"] > 3:
        return None              # the screen has not reported yet: decide at the next refresh
    return pos["current"] < elapsed - 3000       # the screen's player is clearly behind MA


def _flow_time_commands(''', 1)
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (ecran ouvert en retard): patch applique")
