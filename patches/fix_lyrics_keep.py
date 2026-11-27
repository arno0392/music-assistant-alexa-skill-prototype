"""PATCH: keep the lyrics panel open across new screens.

Skipping a track (or seeking) re-renders the screen, which reset the lyrics
panel to closed. The screen now reports whether the panel is open (5th field
of "maReport"), and the skill reopens it on the new screen once the lyrics of
the new track are there.

Requires fix_time_precision.py.
usage: python3 fix_lyrics_keep.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
OLD = "${event.currentTime}|${event.paused ? 'false' : 'true'}|${trackOffset}|${utcTime}"
NEW = OLD + "|${lyricsVisible ? 1 : 0}"
if NEW in json.dumps(doc):
    print("apl_document (paroles ouvertes): deja patche")
else:
    count = 0

    def walk(x):
        global count
        if isinstance(x, dict):
            if x.get("componentId") == "maReport" and x.get("value") == OLD:
                x["value"] = NEW
                count += 1
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(doc)
    assert count >= 4, f"apl_document (paroles ouvertes): {count} rapports trouves"
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (paroles ouvertes): patch applique")

path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "_lyrics_open" in src:
    print("lambda_function (paroles ouvertes): deja patche")
else:
    edits = [
        ("            _screen_report(device_id, player_id, float(parts[0] or 0), is_playing, offset)\n",
         "            _screen_report(device_id, player_id, float(parts[0] or 0), is_playing, offset)\n"
         "            if len(parts) > 4 and parts[4].strip() in ('0', '1'):\n"
         "                _lyrics_open[player_id] = parts[4].strip() == '1'\n"),
        ('''        if not st["lines"]:
            commands.append(_set_root("lyricsVisible", False))
''', '''        if st["lines"] and _lyrics_open.get(player_id):
            commands.append(_set_root("lyricsVisible", True))
        if not st["lines"]:
            commands.append(_set_root("lyricsVisible", False))
'''),
    ]
    for old, new in edits:
        assert src.count(old) == 1, f"lambda_function (paroles ouvertes): code inattendu ({old[:50]!r})"
        src = src.replace(old, new)
    src = src.rstrip("\n") + "\n\n\n_lyrics_open = {}     # player_id -> lyrics panel open on the screen\n"
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (paroles ouvertes): patch applique")
