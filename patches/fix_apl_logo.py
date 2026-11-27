"""PATCH: Music Assistant logo, white, top right of the screen.

A white outline version of the Music Assistant logo (house + "MA"), drawn as
vector graphics (AVG) so it stays sharp on every screen size and needs no
download. Placed top right, the usual place of the source logo on Alexa
screens, slightly transparent so it does not compete with the cover.

usage: python3 fix_apl_logo.py SRC_DIR
"""
import json
import os
import sys

SIZE = "44dp"
path = os.path.join(sys.argv[1], "skill", "apl_document.json")
doc = json.load(open(path, encoding="utf-8"))
if "maLogo" in doc.get("graphics", {}):
    print("apl_document (logo): deja patche")
    sys.exit(0)

doc["graphics"]["maLogo"] = {
    "type": "AVG", "version": "1.2", "width": 256, "height": 256,
    "items": [
        {"type": "path", "fill": "transparent", "stroke": "white", "strokeWidth": 14,
         "strokeLineJoin": "round",
         "pathData": "M128,16 L240,98 Q246,103 246,111 V232 Q246,242 236,242 H20 Q10,242 10,232 V111 "
                     "Q10,103 16,98 Z"},
        {"type": "path", "fill": "transparent", "stroke": "white", "strokeWidth": 17,
         "strokeLineCap": "round",
         "pathData": "M42,138 V212 M76,138 V212 M110,138 V212 M150,212 L174,138 M192,138 L216,212"},
    ],
}
root = doc["layouts"]["AudioPlayer"]["item"][0]
items = root["items"]
pos = next(i for i, c in enumerate(items) if c.get("type") == "AlexaHeader") + 1
items.insert(pos, {
    "type": "VectorGraphic", "id": "maLogo", "source": "maLogo",
    "position": "absolute", "top": "24dp", "right": "@marginHorizontal",
    "width": SIZE, "height": SIZE, "scale": "best-fit", "opacity": 0.85,
})
json.dump(doc, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("apl_document (logo): patch applique")
