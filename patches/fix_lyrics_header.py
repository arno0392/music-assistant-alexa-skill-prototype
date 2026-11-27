"""PATCH: title and artist above the lyrics.

While the lyrics are shown, the cover/title row is hidden: the lyrics panel
now starts with the track title and artist, small, top left, on one line
each (cut with an ellipsis when too long).

Requires fix_lyrics_scroll.py.
usage: python3 fix_lyrics_header.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
if "maLyricsTitle" in json.dumps(doc):
    print("apl_document (titre paroles): deja patche")
else:
    root = doc["layouts"]["AudioPlayer"]["item"][0]
    root["bind"] += [{"name": "lyricsTitle", "type": "string", "value": "${primaryText}"},
                     {"name": "lyricsArtist", "type": "string", "value": ""}]
    panels = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("id") == "maLyricsPanel":
                panels.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(doc)
    assert len(panels) == 1, "fix_apl_lyrics.py doit etre applique avant"
    panel = panels[0]
    panel["direction"] = "column"
    seq = panel["items"][0]
    assert seq.get("id") == "maLyrics"
    seq["height"] = "1dp"
    seq["grow"] = 1
    panel["items"].insert(0, {
        "type": "Container",
        "width": "100%",
        "paddingBottom": "8dp",
        "items": [
            {"type": "Text", "id": "maLyricsTitle", "text": "${lyricsTitle}", "width": "100%",
             "maxLines": 1, "fontSize": "20dp", "fontWeight": "bold", "textAlign": "left",
             "color": "#FFFFFF"},
            {"type": "Text", "id": "maLyricsArtist", "text": "${lyricsArtist}", "width": "100%",
             "maxLines": 1, "fontSize": "16dp", "textAlign": "left", "color": "#FFFFFFB3",
             "display": "${lyricsArtist ? 'normal' : 'none'}"},
        ],
    })
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (titre paroles): patch applique")

path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "def _lyrics_heading" in src:
    print("lambda_function (titre paroles): deja patche")
else:
    old = '''        commands += [_set_root("lyricsBuckets",'''
    assert src.count(old) == 1, "lambda_function (titre paroles): code inattendu"
    src = src.replace(old, '''        commands += _lyrics_heading()
''' + old)
    src = src.rstrip("\n") + '''


def _lyrics_heading():
    """Title and artist shown above the lyrics."""
    import shared_store
    store = shared_store._store or {}
    title = store.get("title") or ""
    artist = store.get("artist") or store.get("secondary") or ""
    return [_set_root("lyricsTitle", title), _set_root("lyricsArtist", artist)]
'''
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (titre paroles): patch applique")
