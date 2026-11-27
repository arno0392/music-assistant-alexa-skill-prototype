"""PATCH: screen background and total time display.

1. The background showed the same cover as the artwork, sharp and stretched:
   it looked like the image twice. It is now the cover lightly blurred and
   darkened. AlexaBackground only has an on/off blur (too strong), so it is
   replaced by an Image with a Blur filter of BLUR_RADIUS dp; the container
   keeps the id "AlexaBackground" and a "backgroundImageSource" bind, so the
   skill's SetValue updates keep working.
2. Total time: until the skill sends the track duration, the slider fell back
   to the Video duration, which for a flow stream is just what is buffered
   (e.g. "00:00 / 00:13"). It now shows only the track duration.

usage: python3 fix_apl_background.py SRC_DIR
"""
import json
import os
import sys

BLUR_RADIUS = 8          # dp; higher = more blur
OVERLAY = "rgba(0, 0, 0, 0.35)"

path = os.path.join(sys.argv[1], "skill", "apl_document.json")
doc = json.load(open(path, encoding="utf-8"))
parents = []


def walk(x):
    if isinstance(x, dict):
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            if isinstance(v, dict) and v.get("id") == "AlexaBackground":
                parents.append((x, i))
            walk(v)


walk(doc)
assert len(parents) == 1, f"apl_document (fond): {len(parents)} fonds trouves"
lst, i = parents[0]
changed = False
if lst[i].get("type") == "AlexaBackground":
    lst[i] = {
        "type": "Container",
        "id": "AlexaBackground",
        "description": "Blurred cover background",
        "position": "absolute",
        "width": "100vw",
        "height": "100vh",
        "bind": [{"name": "backgroundImageSource", "type": "string",
                  "value": "${backgroundImageSource}"}],
        "items": [{
            "type": "Image",
            "source": "${backgroundImageSource}",
            "width": "100%",
            "height": "100%",
            "scale": "best-fill",
            "filters": [{"type": "Blur", "radius": BLUR_RADIUS}],
            "overlayColor": OVERLAY,
        }],
    }
    changed = True

OLD_TOTAL = "${trackTotal > 0 ? trackTotal : videoTotalValue}"


def fix_total(x):
    global changed
    if isinstance(x, dict):
        if x.get("totalValue") == OLD_TOTAL:
            x["totalValue"] = "${trackTotal}"
            changed = True
        for v in x.values():
            fix_total(v)
    elif isinstance(x, list):
        for v in x:
            fix_total(v)


fix_total(doc)
if changed:
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (fond): patch applique")
else:
    print("apl_document (fond): deja patche")
