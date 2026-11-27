"""PATCH: Music Assistant logo in the header of the screen.

The AlexaHeader attribution image (small, top right, the standard place for
a source logo on Alexa screens) now shows the Music Assistant icon when no
other attribution image is given. Icon served by Home Assistant's brand
images CDN (brands.home-assistant.io, integration "music_assistant").

usage: python3 fix_apl_logo.py SRC_DIR
"""
import json
import os
import sys

LOGO = "https://brands.home-assistant.io/music_assistant/icon.png"
path = os.path.join(sys.argv[1], "skill", "apl_document.json")
doc = json.load(open(path, encoding="utf-8"))
headers = []


def walk(x):
    if isinstance(x, dict):
        if x.get("type") == "AlexaHeader":
            headers.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)


walk(doc)
assert len(headers) == 1, f"apl_document (logo): {len(headers)} AlexaHeader trouves"
value = "${headerAttributionImage ? headerAttributionImage : '" + LOGO + "'}"
if headers[0].get("headerAttributionImage") == value:
    print("apl_document (logo): deja patche")
else:
    headers[0]["headerAttributionImage"] = value
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (logo): patch applique")
