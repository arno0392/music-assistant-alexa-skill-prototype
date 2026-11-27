"""PATCH: address the screen's root container by its real id.

The per-track values (track total, lyrics, trackPos...) are binds of the root
container of the "AudioPlayer" layout, declared there with id "MaTimeRoot".
But the layout instance in mainTemplate has "id": "AudioPlayerRoot", and the
instance's properties replace those of the layout's top component: at runtime
the container is "AudioPlayerRoot" and "MaTimeRoot" does not exist. Every
SetValue on "MaTimeRoot" was silently ignored (lyrics button never shown,
trackTotal never set).

All SetValue commands now target "AudioPlayerRoot".

Requires fix_apl_lyrics.py.
usage: python3 fix_root_id.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
OLD, NEW = '"componentId": "MaTimeRoot"', '"componentId": "AudioPlayerRoot"'

doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
assert doc["mainTemplate"]["items"][0].get("id") == "AudioPlayerRoot", "id d'instance inattendu"
count = 0


def walk(x):
    global count
    if isinstance(x, dict):
        if x.get("componentId") == "MaTimeRoot":
            x["componentId"] = "AudioPlayerRoot"
            count += 1
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)


walk(doc)
if count:
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"apl_document (id racine): patch applique ({count})")
else:
    print("apl_document (id racine): deja patche")

path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
n = src.count(OLD)
if n:
    open(path, "w", encoding="utf-8").write(src.replace(OLD, NEW))
    print(f"lambda_function (id racine): patch applique ({n})")
else:
    assert NEW in src, "lambda_function (id racine): code inattendu"
    print("lambda_function (id racine): deja patche")
