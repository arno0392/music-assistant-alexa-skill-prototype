"""PATCH: pause from Music Assistant (web) no longer stopped the APL screen.

A pause that reaches the skill in a new session re-renders the APL screen with
start_paused=True. apl.py then sets autoplay=false on the Video and on the
AlexaTransportControls by a fixed path in the document. fix_apl_buttons.py
wrapped AlexaTransportControls in a Container (MaSkipButtons), so the fixed
path hit that Container: the transport controls kept autoplay=true and started
the audio again right away.

Fix: find the Video and the AlexaTransportControls by type.
usage: python3 fix_apl_pause.py APL_PY   (the patched apl.py copy, e.g. patches/apl_src.py)
"""
import sys

path = sys.argv[1]
src = open(path, encoding="utf-8").read()
if "_find_components" in src:
    print("apl (pause): deja patche")
    sys.exit(0)

old = '''    # Update autoplay in Video component and AlexaTransportControls
    try:
        video_component = apl_document["layouts"]["AudioPlayer"]["item"][0]["items"][2]["items"][1]["items"][0]
        video_component["autoplay"] = autoplay
    except (KeyError, IndexError):
        logging.debug("Could not set video autoplay in APL template")

    try:
        transport_controls = apl_document["layouts"]["AudioPlayer"]["item"][0]["items"][2]["items"][1]["items"][1]["items"][0]["item"][1]
        transport_controls["autoplay"] = autoplay
    except (KeyError, IndexError):
        logging.debug("Could not set transport autoplay in APL template")'''
new = '''    # Update autoplay in Video component and AlexaTransportControls.
    # PATCH: found by type, the document layout is patched (buttons container).
    def _find_components(node, wanted, found):
        if isinstance(node, dict):
            if node.get("type") in wanted:
                found.append(node)
            for value in node.values():
                _find_components(value, wanted, found)
        elif isinstance(node, list):
            for value in node:
                _find_components(value, wanted, found)
        return found

    targets = _find_components(apl_document.get("layouts", {}),
                               ("Video", "AlexaTransportControls"), [])
    if not targets:
        logging.debug("Could not set autoplay in APL template")
    for component in targets:
        component["autoplay"] = autoplay'''
assert src.count(old) == 1, "code inattendu, patch non applique"
open(path, "w", encoding="utf-8").write(src.replace(old, new))
print("apl (pause): patch applique")
