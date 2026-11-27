"""PATCH: move between the screen's buttons with a TV remote (after fix_tv_remote/fix_tv_diag).

A TV's Alexa app sends the remote's keys to the page but gives focus to none of its
buttons. The page now keeps its own selection, like the buttons of a TV app: the first
key focuses a hidden key catcher and highlights play/pause. Left/Right move across
previous, play/pause, next and lyrics; Up goes to the progress bar, where Left/Right
seek 10 s back/forward, and Down comes back to the buttons; OK presses the highlighted
button. The arrows never act by themselves; the remote's media keys keep their own
action. Nothing changes on a touch screen: without a remote key nothing is dimmed.

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

# undo the earlier attempts: native focus on the lyrics button never took on a TV
lyr = find(root, lambda n: n.get("id") == "maLyricsButton")
lyr.pop("handleKeyDown", None)
root["onMount"] = [c for c in root["onMount"] if c.get("type") != "SetFocus"]

root.setdefault("bind", []).append({"name": "remoteFocus", "type": "number", "value": -1})


def highlight(index, item, round_size=None):
    # With the remote, the selected control stays bright and the others dim: a grey
    # halo cannot be told apart from the play/pause button's own grey disc.
    frame = {"type": "Frame", "item": item,
             "opacity": "${remoteFocus < 0 || remoteFocus == %d ? 1 : 0.35}" % index}
    if round_size:
        frame.update(width="100%", height="100%")
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

SLIDER = 10
bar = find(root, lambda n: n.get("id") == "slider")
holder = find(root, lambda n: isinstance(n.get("item"), list) and bar in n["item"])
holder["item"][holder["item"].index(bar)] = {
    "type": "Frame", "width": "100%", "item": bar,
    "opacity": "${remoteFocus < 0 || remoteFocus == %d ? 1 : 0.35}" % SLIDER}

pos = "(videoProgressValue > trackOffset ? videoProgressValue - trackOffset : 0)"
root["bind"].append({"name": "seekTarget", "type": "number", "value": -1})
video = find(root, lambda n: n.get("id") == "videoPlayer")
for c in video.get("onTimeUpdate", []):
    if c.get("componentId") == "slider" and c.get("property") == "progressValue":
        c["value"] = "${seekTarget >= 0 ? seekTarget : %s}" % pos   # the thumb shows the target meanwhile


def seek(delta):
    """Each press moves the target by delta at once; MA seeks once the presses stop."""
    target = "${Math.max(0, Math.min(trackTotal - 2000, (seekTarget >= 0 ? seekTarget : %s) %+d))}" % (pos, delta)
    return [
        {"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "seekTarget", "value": target},
        {"type": "SetValue", "componentId": "slider", "property": "progressValue", "value": "${seekTarget}"},
        {"type": "Sequential", "sequencer": "maSeekKeys", "commands": [
            {"type": "Idle", "delay": 1200},
            {"type": "SetValue", "componentId": "maSeek", "property": "text", "value": "${seekTarget}@${utcTime}"},
            {"type": "Idle", "delay": 8000},
            {"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "seekTarget", "value": -1}]},
    ]


press = [
    {"type": "SendEvent", "arguments": ["Previous"], "when": "${remoteFocus == 0}"},
    {"type": "SetValue", "componentId": "playPauseToggleButtonId", "property": "checked",
     "value": "${!videoPlaying}", "when": "${remoteFocus == 1}"},
    {"type": "ControlMedia", "componentId": "videoPlayer", "command": "${videoPlaying ? 'pause' : 'play'}",
     "when": "${remoteFocus == 1}"},
    {"type": "SendEvent", "arguments": ["Next"], "when": "${remoteFocus == 2}"},
    {"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "lyricsVisible",
     "value": "${!lyricsVisible}", "when": "${remoteFocus == 3}"},
    {"type": "Sequential", "sequencer": "maLyricsOpen", "when": "${remoteFocus == 3 && lyricsVisible}",
     "commands": [{"type": "Idle", "delay": 150},
                  {"type": "ScrollToIndex", "componentId": "maLyrics", "index": "${lyricsIndex}", "align": "center"}]},
]
move = lambda expr: [{"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "remoteFocus", "value": expr}]
fdiag = {"type": "SendEvent", "arguments": ["KeyDiag", "${event.keyboard.code}", "${event.keyboard.key}", "focused"]}
on_bar = "remoteFocus == %d" % SLIDER
catcher = {
    "type": "TouchWrapper", "id": "maRemote", "position": "absolute", "top": 0, "left": 0,
    "width": "1dp", "height": "1dp",
    "item": {"type": "Frame", "width": "1dp", "height": "1dp"},
    "handleKeyDown": [
        {"when": "${(%s) && %s}" % (keys("ArrowLeft"), on_bar), "commands": seek(-10000)},
        {"when": "${(%s) && %s}" % (keys("ArrowRight"), on_bar), "commands": seek(10000)},
        {"when": "${%s}" % keys("ArrowLeft"), "commands": move("${Math.max(0, remoteFocus - 1)}")},
        {"when": "${%s}" % keys("ArrowRight"), "commands": move("${Math.min(lyricsAvailable ? 3 : 2, remoteFocus + 1)}")},
        {"when": "${%s}" % keys("ArrowUp"), "commands": move(SLIDER)},
        {"when": "${%s}" % keys("ArrowDown"), "commands": move("${%s ? 1 : remoteFocus}" % on_bar)},
        {"when": "${%s}" % keys("Enter", "NumpadEnter"), "commands": press},
        {"when": "${%s}" % PREV, "commands": [{"type": "SendEvent", "arguments": ["Previous"]}]},
        {"when": "${%s}" % NEXT, "commands": [{"type": "SendEvent", "arguments": ["Next"]}]},
        {"when": "${%s}" % PLAY, "commands": [{"type": "SendEvent", "arguments": ["PlayPause"]}]},
    ],
}
for h in catcher["handleKeyDown"]:
    h["commands"] = [fdiag] + h["commands"]
root["items"].append(catcher)

# Keys that reach the document mean nothing has focus yet: take it and highlight
# play/pause (the bar for Up). Only OK acts, as a press on play/pause.
def take_focus(index):
    return [{"type": "SetValue", "componentId": "AudioPlayerRoot", "property": "remoteFocus", "value": index},
            {"type": "SetFocus", "componentId": "maRemote"}]


doc["handleKeyDown"] = [
    {"when": "${%s}" % keys("ArrowUp"), "commands": [diag] + take_focus(SLIDER)},
    {"when": "${%s}" % keys("ArrowLeft", "ArrowRight", "ArrowDown"), "commands": [diag] + take_focus(1)},
    {"when": "${%s}" % keys("Enter", "NumpadEnter"),
     "commands": [diag, {"type": "SendEvent", "arguments": ["PlayPause"]}] + take_focus(1)},
    {"when": "${%s}" % PREV, "commands": [diag, {"type": "SendEvent", "arguments": ["Previous"]}]},
    {"when": "${%s}" % NEXT, "commands": [diag, {"type": "SendEvent", "arguments": ["Next"]}]},
    {"when": "${%s}" % PLAY, "commands": [diag, {"type": "SendEvent", "arguments": ["PlayPause"]}]},
    {"commands": [diag]},
]
json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("apl_document (navigation TV): patch applique")
