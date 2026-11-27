"""PATCH: move between the screen's buttons with a TV remote (after fix_tv_remote/fix_tv_diag).

A TV's Alexa app sends the remote's keys to the page but gives focus to none of its
buttons. The page now keeps its own selection: the first key focuses a hidden key
catcher and highlights play/pause; Left/Right move the highlight across previous,
play/pause, next and lyrics; OK presses the highlighted button; Up/Down show/hide the
lyrics; the media keys keep their direct action. Nothing changes on a touch screen:
without a remote key the highlight stays transparent.

usage: python3 fix_tv_nav.py SRC_DIR
"""
import json
import os
import sys

doc_path = os.path.join(sys.argv[1], "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
root = doc["layouts"]["AudioPlayer"]["item"]
root = root[0] if isinstance(root, list) else root
if any(b.get("name") == "remoteFocus" for b in root.get("bind", [])):
    print("apl_document (navigation TV): deja patche")
    sys.exit(0)


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


def keys(*names):
    return " || ".join(f"event.keyboard.code == '{n}' || event.keyboard.key == '{n}'" for n in names)


PREV = keys("MediaRewind", "MediaPreviousTrack", "MediaTrackPrevious")
NEXT = keys("MediaFastForward", "MediaNextTrack", "MediaTrackNext")
PLAY = keys("MediaPlayPause", "MediaPlay", "MediaPause")
diag = {"type": "SendEvent", "arguments": ["KeyDiag", "${event.keyboard.code}", "${event.keyboard.key}"]}
show_lyrics = [{"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "lyricsVisible", "value": True},
               {"type": "ScrollToIndex", "componentId": "maLyrics", "index": "${lyricsIndex}", "align": "center"}]
hide_lyrics = [{"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "lyricsVisible", "value": False}]

# undo the earlier attempts: native focus on the lyrics button never took on a TV
lyr = find(root, lambda n: n.get("id") == "maLyricsButton")
lyr.pop("handleKeyDown", None)
root["onMount"] = [c for c in root["onMount"] if c.get("type") != "SetFocus"]

root.setdefault("bind", []).append({"name": "remoteFocus", "type": "number", "value": -1})


def highlight(index, item, round_size=None):
    frame = {"type": "Frame", "item": item,
             "backgroundColor": "${remoteFocus == %d ? 'rgba(255,255,255,0.28)' : 'transparent'}" % index}
    if round_size:
        frame.update(width="100%", height="100%", borderRadius=round_size)
    else:
        frame["borderRadius"] = "1000dp"
    return frame


row = find(root, lambda n: n.get("id") == "MaSkipButtons")
items = row["items"]
for i, it in enumerate(items):
    if it.get("type") == "AlexaTransportControls":
        items[i] = highlight(1, it)
    elif it.get("type") == "TouchWrapper":
        src = it["item"].get("source")
        idx = {"maSkipPrevious": 0, "maSkipNext": 2, "maLyrics": 3}.get(src)
        if idx is not None:
            it["item"] = highlight(idx, it["item"], "@secondaryControlSize")

press = [
    {"type": "SendEvent", "arguments": ["Previous"], "when": "${remoteFocus == 0}"},
    {"type": "SendEvent", "arguments": ["PlayPause"], "when": "${remoteFocus == 1}"},
    {"type": "SendEvent", "arguments": ["Next"], "when": "${remoteFocus == 2}"},
    {"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "lyricsVisible",
     "value": "${!lyricsVisible}", "when": "${remoteFocus == 3}"},
    {"type": "ScrollToIndex", "componentId": "maLyrics", "index": "${lyricsIndex}", "align": "center",
     "when": "${remoteFocus == 3 && lyricsVisible}"},
]
move = lambda expr: [{"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "remoteFocus", "value": expr}]
fdiag = {"type": "SendEvent", "arguments": ["KeyDiag", "${event.keyboard.code}", "${event.keyboard.key}", "focused"]}
catcher = {
    "type": "TouchWrapper", "id": "maRemote", "position": "absolute", "top": 0, "left": 0,
    "width": "1dp", "height": "1dp",
    "item": {"type": "Frame", "width": "1dp", "height": "1dp"},
    "handleKeyDown": [
        {"when": "${%s}" % keys("ArrowLeft"), "commands": move("${Math.max(0, remoteFocus - 1)}")},
        {"when": "${%s}" % keys("ArrowRight"), "commands": move("${Math.min(lyricsAvailable ? 3 : 2, remoteFocus + 1)}")},
        {"when": "${%s}" % keys("Enter", "NumpadEnter"), "commands": press},
        {"when": "${%s}" % keys("ArrowUp"), "commands": show_lyrics},
        {"when": "${%s}" % keys("ArrowDown"), "commands": hide_lyrics},
        {"when": "${%s}" % PREV, "commands": [{"type": "SendEvent", "arguments": ["Previous"]}]},
        {"when": "${%s}" % NEXT, "commands": [{"type": "SendEvent", "arguments": ["Next"]}]},
        {"when": "${%s}" % PLAY, "commands": [{"type": "SendEvent", "arguments": ["PlayPause"]}]},
    ],
}
for h in catcher["handleKeyDown"]:
    h["commands"] = [fdiag] + h["commands"]
root["items"].append(catcher)

# Keys that reach the document mean nothing has focus yet: take it (and log it).
take_focus = [diag,
              {"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "remoteFocus", "value": 1},
              {"type": "SetFocus", "componentId": "maRemote"}]
# Keys that reach the document mean nothing has focus: keep the direct actions that work
# without it, and ask for the focus so that the next keys move the highlight instead.
take_focus = [{"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "remoteFocus", "value": 1},
              {"type": "SetFocus", "componentId": "maRemote"}]
doc["handleKeyDown"] = [
    {"when": "${%s}" % keys("ArrowLeft"), "commands": [diag, {"type": "SendEvent", "arguments": ["Previous"]}] + take_focus},
    {"when": "${%s}" % keys("ArrowRight"), "commands": [diag, {"type": "SendEvent", "arguments": ["Next"]}] + take_focus},
    {"when": "${%s}" % keys("Enter", "NumpadEnter"), "commands": [diag, {"type": "SendEvent", "arguments": ["PlayPause"]}] + take_focus},
    {"when": "${%s}" % keys("ArrowUp"), "commands": [diag] + show_lyrics[:1] + take_focus},
    {"when": "${%s}" % keys("ArrowDown"), "commands": [diag] + hide_lyrics + take_focus},
    {"when": "${%s}" % PREV, "commands": [diag, {"type": "SendEvent", "arguments": ["Previous"]}]},
    {"when": "${%s}" % NEXT, "commands": [diag, {"type": "SendEvent", "arguments": ["Next"]}]},
    {"when": "${%s}" % PLAY, "commands": [diag, {"type": "SendEvent", "arguments": ["PlayPause"]}]},
    {"commands": [diag]},
]
json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("apl_document (navigation TV): patch applique")
