"""PATCH: blurred, darkened cover as background of the Echo Show screen.

The background showed the same cover as the artwork, sharp and stretched
(pixelated): it looked like the image twice. AlexaBackground now blurs it and
adds the standard colour overlay, so the cover stands out and the text stays
readable.

usage: python3 fix_apl_background.py SRC_DIR
"""
import json
import os
import sys

path = os.path.join(sys.argv[1], "skill", "apl_document.json")
doc = json.load(open(path, encoding="utf-8"))
found = []


def walk(x):
    if isinstance(x, dict):
        if x.get("type") == "AlexaBackground":
            found.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)


walk(doc)
assert len(found) == 1, f"apl_document (fond): {len(found)} AlexaBackground trouves"
bg = found[0]
if bg.get("backgroundBlur") is True:
    print("apl_document (fond): deja patche")
else:
    bg["backgroundBlur"] = True
    bg["colorOverlay"] = True
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (fond): patch applique")
