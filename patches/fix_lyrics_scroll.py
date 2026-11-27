"""PATCH: lyrics scroll driven by the screen itself.

The panel was scrolled by the skill at each refresh (~1 s, plus network), on
the MAIN sequencer where every other command interrupted the scroll
animation: on fast songs the highlighted line ended at the bottom.

The skill now sends, with the lyrics, a lookup table "lyricsBuckets": the
line playing in each 250 ms slice of the track. At every time update the
Video reads the line for its own position and, when it changes, scrolls the
panel to center it, on its own sequencer "maScroll" (a named sequencer makes
the command run in normal mode from the fast-mode handler, and nothing else
interrupts it).

Requires fix_voice_next.py.
usage: python3 fix_lyrics_scroll.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
BUCKET_MS = 250

doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
if "maScroll" in json.dumps(doc):
    print("apl_document (defilement): deja patche")
else:
    root = doc["layouts"]["AudioPlayer"]["item"][0]
    root["bind"].append({"name": "lyricsBuckets", "type": "any", "value": []})
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
    assert len(videos) == 1, "apl_document (defilement): Video introuvable"
    upd = videos[0]["onTimeUpdate"]
    assert any(c.get("property") == "trackPos" for c in upd), "fix_apl_lyrics.py doit etre applique avant"
    b = f"Math.floor((event.currentTime - trackOffset) / {BUCKET_MS})"
    idx = f"(event.currentTime >= trackOffset && {b} < lyricsBuckets.length ? lyricsBuckets[{b}] : -1)"
    upd.append({
        "type": "Sequential",
        "sequencer": "maScroll",
        "when": "${lyricsSynced && " + idx + " >= 0 && " + idx + " != lyricsIndex}",
        "commands": [
            {"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "lyricsIndex",
             "value": "${" + idx + "}"},
            {"type": "ScrollToIndex", "componentId": "maLyrics", "index": "${" + idx + "}",
             "align": "center", "when": "${lyricsVisible}"},
        ],
    })
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (defilement): patch applique")

path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "def _lyrics_buckets" in src:
    print("lambda_function (defilement): deja patche")
else:
    edits = [
        ('''        commands += [_set_root("lyricsLines", st["lines"]),''',
         '''        commands += [_set_root("lyricsBuckets", _lyrics_buckets(st["lines"]) if st["synced"] else []),
                     _set_root("lyricsLines", st["lines"]),'''),
        ('''    if st["synced"] and st["lines"]:
        pos = _screen_pos.get(player_id)
        if pos and pos.get("offset") is not None:
            shown = pos["current"] - pos["offset"]
            idx = 0
            for i, line in enumerate(st["lines"]):
                if line["s"] <= shown:
                    idx = i
                else:
                    break
            if idx != st["idx"]:
                st["idx"] = idx
                commands += [_set_root("lyricsIndex", idx),
                             {"type": "ScrollToIndex", "componentId": "maLyrics", "index": idx,
                              "align": "center"}]
    return commands
''', '''    return commands      # the screen scrolls by itself (lyricsBuckets)
'''),
    ]
    for old, new in edits:
        assert src.count(old) == 1, f"lambda_function (defilement): code inattendu ({old[:50]!r})"
        src = src.replace(old, new)
    src = src.rstrip("\n") + f'''


_LYRICS_BUCKET_MS = {BUCKET_MS}


def _lyrics_buckets(lines):
    """Line playing in each {BUCKET_MS} ms slice, up to 10 s after the last line starts."""
    if not lines:
        return []
    count = min(lines[-1]["s"] // _LYRICS_BUCKET_MS + 40, 4 * 60 * 20)
    out, i = [], -1
    for b in range(int(count)):
        t = b * _LYRICS_BUCKET_MS
        while i + 1 < len(lines) and lines[i + 1]["s"] <= t:
            i += 1
        out.append(i)
    return out
'''
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (defilement): patch applique")
