"""PATCH: the play/pause button follows the player, whoever paused it.

The button only flipped when it was pressed: a pause or stop from the MA web app
(or the Echo's own pause) left it on "pause". The Video's onPlay/onPause/onEnd now
set its state, as Amazon documents for AlexaTransportControls.

usage: python3 fix_play_button_sync.py SRC_DIR
"""
import json
import os
import sys

doc_path = os.path.join(sys.argv[1], "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))


def find(node, pred):
    if isinstance(node, dict):
        if pred(node):
            return node
        node = list(node.values())
    if isinstance(node, list):
        for v in node:
            hit = find(v, pred)
            if hit:
                return hit
    return None


video = find(doc["layouts"], lambda n: n.get("id") == "videoPlayer")
button = lambda playing: {"type": "SetValue", "componentId": "playPauseToggleButtonId",
                          "property": "checked", "value": playing}
if any(c.get("componentId") == "playPauseToggleButtonId" for c in video.get("onPause", [])):
    print("apl_document (bouton lecture/pause): deja patche")
    sys.exit(0)
for event, playing in (("onPlay", True), ("onPause", False), ("onEnd", False)):
    video.setdefault(event, []).append(button(playing))
json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("apl_document (bouton lecture/pause): patch applique")
