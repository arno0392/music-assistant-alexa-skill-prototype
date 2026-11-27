"""PATCH: drive the screen with a TV remote (Echo Show on Fire TV, Alexa TVs).

On a TV the APL page shows, but its touch buttons cannot be reached with the
remote. The document now handles the remote's keys itself:

- Left / Rewind / Previous track  -> previous track (MA)
- Right / Fast forward / Next      -> next track (MA)
- OK (Enter) / Play-Pause          -> play / pause
- Up / Down                        -> show / hide the lyrics

usage: python3 fix_tv_remote.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))


def keys(*names):
    return "${" + " || ".join(f"event.keyboard.code == '{n}' || event.keyboard.key == '{n}'" for n in names) + "}"


root = doc["layouts"]["AudioPlayer"]["item"]
root = root[0] if isinstance(root, list) else root


def find(node, cid):
    if isinstance(node, dict):
        if node.get("id") == cid:
            return node
        node = list(node.values())
    if isinstance(node, list):
        for v in node:
            hit = find(v, cid)
            if hit:
                return hit
    return None


if "SetFocus" in json.dumps(root.get("onMount")):
    print("apl_document (telecommande): deja patche")
else:
    handlers = [
        {"when": keys("ArrowLeft", "MediaRewind", "MediaPreviousTrack", "MediaTrackPrevious"),
         "commands": [{"type": "SendEvent", "arguments": ["Previous"]}]},
        {"when": keys("ArrowRight", "MediaFastForward", "MediaNextTrack", "MediaTrackNext"),
         "commands": [{"type": "SendEvent", "arguments": ["Next"]}]},
        {"when": keys("Enter", "NumpadEnter", "MediaPlayPause", "MediaPlay", "MediaPause"),
         "commands": [{"type": "SendEvent", "arguments": ["PlayPause"]}]},
        {"when": keys("ArrowUp"),
         "commands": [{"type": "SetValue", "componentId": "AudioPlayerRoot",
                       "property": "lyricsVisible", "value": True}]},
        {"when": keys("ArrowDown"),
         "commands": [{"type": "SetValue", "componentId": "AudioPlayerRoot",
                       "property": "lyricsVisible", "value": False}]},
    ]
    # Keys only reach a component when something on the page has focus: on a TV,
    # give it to the lyrics button at mount. Its own handlers win over its OK = press.
    button = find(root, "maLyricsButton")
    if button is not None:
        button["handleKeyDown"] = handlers
        root["onMount"].insert(0, {"type": "SetFocus", "componentId": "maLyricsButton",
                                   "when": "${viewport.mode == 'tv'}"})
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (telecommande): patch applique")

path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "class APLPlayPauseEventHandler" in src:
    print("lambda_function (telecommande): deja patche")
else:
    src = src.rstrip("\n") + '''


class APLPlayPauseEventHandler(AbstractRequestHandler):
    """Play/pause key of a TV remote: toggles the screen's player (the pause then reaches MA)."""
    def can_handle(self, handler_input):
        if not is_request_type("Alexa.Presentation.APL.UserEvent")(handler_input):
            return False
        args = getattr(handler_input.request_envelope.request, 'arguments', None) or []
        return bool(args) and args[0] == "PlayPause"

    def handle(self, handler_input):
        from ask_sdk_model.interfaces.alexa.presentation.apl import ExecuteCommandsDirective
        player_id = device_mapping.get_player_for_device(_device_id_from(handler_input))
        pos = _screen_pos.get(player_id) or {}
        command = "pause" if pos.get("playing", True) else "play"
        logger.info("Remote play/pause on %s: %s", player_id, command)
        rb = handler_input.response_builder
        rb.add_directive(ExecuteCommandsDirective(
            commands=[{"type": "ControlMedia", "componentId": "videoPlayer", "command": command}],
            token="playbackToken"))
        return rb.set_should_end_session(None).response


sb.add_request_handler(APLPlayPauseEventHandler())
'''
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (telecommande): patch applique")
