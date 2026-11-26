"""PATCH: make the APL slider seek actually reach the skill.

The slider's onUpCommand runs in APL "fast mode", where SendEvent is ignored:
the ["Seek", ms] event of fix_apl_ux.py was never sent. Instead, onUpCommand now
writes "<ms>@<elapsedTime>" into a hidden Text (id maSeek); the periodic refresh
event carries it in "components" and the skill seeks Music Assistant when the
value changes.

Requires fix_apl_ux.py and fix_live_report.py first.
usage: python3 fix_apl_seek.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
P = lambda *p: os.path.join(base, *p)

# ---------------------------------------------------------------- apl_document.json
doc_path = P("skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
raw = json.dumps(doc)
if "maSeek" in raw:
    print("apl_document (seek): deja patche")
else:
    assert '"Seek"' in raw and "maReport" in raw, "patches precedents manquants"
    root = doc["layouts"]["AudioPlayer"]["item"][0]
    root["items"].append({"type": "Text", "id": "maSeek", "text": "",
                          "position": "absolute", "width": 1, "height": 1, "opacity": 0})
    for cmd in root.get("onMount", []):
        for c in cmd.get("commands", []):
            if c.get("type") == "SendEvent":
                c["components"] = ["maReport", "maSeek"]
    sliders = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "AlexaSlider":
                sliders.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc)
    sliders[0]["onUpCommand"] = [
        {"type": "SetValue", "property": "sliderActive", "value": False},
        {"type": "SetValue", "componentId": "maSeek", "property": "text",
         "value": "${sliderThumbPosition}@${elapsedTime}"},
    ]
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (seek): patch applique")

# ---------------------------------------------------------------- util.py
path = P("skill", "util.py")
src = open(path, encoding="utf-8").read()
if '"maSeek"' in src:
    print("util (seek): deja patche")
else:
    old = '"components": ["maReport"]'
    assert src.count(old) == 1, "fix_live_report.py doit etre applique avant"
    open(path, "w", encoding="utf-8").write(src.replace(old, '"components": ["maReport", "maSeek"]'))
    print("util (seek): patch applique")

# ---------------------------------------------------------------- lambda_function.py
path = P("skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "_last_seek_request" in src:
    print("lambda_function (seek): deja patche")
else:
    old = '''    actions = shared_store.pop_pending(player_id)
    if not actions:
        return None'''
    new = '''    # Seek requested with the slider (written into the hidden Text "maSeek").
    seek = components.get('maSeek') if isinstance(components, dict) else None
    if isinstance(seek, str) and '@' in seek and seek != _last_seek_request.get(player_id):
        _last_seek_request[player_id] = seek
        try:
            seconds = float(seek.split('@', 1)[0]) / 1000.0
        except ValueError:
            seconds = None
        if seconds is not None:
            logger.info("Live page %s: seek to %.1fs", player_id, seconds)
            ma_control.seek_player(player_id, seconds)

    actions = shared_store.pop_pending(player_id)
    if not actions:
        return None'''
    anchor = "\ndef _handle_live_page(handler_input):"
    assert src.count(old) == 1 and src.count(anchor) == 1, "fix_live_report.py doit etre applique avant"
    src = src.replace(old, new, 1).replace(anchor, "\n_last_seek_request = {}\n" + anchor, 1)
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (seek): patch applique")
