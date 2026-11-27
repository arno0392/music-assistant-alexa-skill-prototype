"""PATCH: report the real Video position/state of the APL screen to the skill.

The refresh SendEvent sent by the skill (ExecuteCommands) is evaluated in the
document context, where the screen's bound values (videoProgressValue,
videoPlaying) are not visible: the report always said 0 / paused.

Fix: the Video events write "position|playing" into a hidden Text component
(id maReport) and every refresh SendEvent lists it in "components", so its
text is sent with the UserEvent whatever the evaluation context.

Requires fix_live_page.py first.
usage: python3 fix_live_report.py SRC_DIR   (same SRC_DIR as fix_live_page.py)
"""
import json
import os
import sys

base = sys.argv[1]
P = lambda *p: os.path.join(base, *p)

REPORT = "${event.currentTime}|${event.paused ? 'false' : 'true'}"

# ---------------------------------------------------------------- apl_document.json
doc_path = P("skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
if "maReport" in json.dumps(doc):
    print("apl_document (rapport): deja patche")
else:
    assert "videoPlaying" in json.dumps(doc), "fix_live_page.py doit etre applique avant"
    root = doc["layouts"]["AudioPlayer"]["item"][0]
    root.setdefault("items", []).append({
        "type": "Text", "id": "maReport", "text": "0|true",
        "position": "absolute", "width": 1, "height": 1, "opacity": 0,
    })
    n = 0
    for cmd in root.get("onMount", []):
        for c in cmd.get("commands", []):
            if c.get("type") == "SendEvent":
                c["components"] = ["maReport"]
                n += 1
    assert n == 1, "boucle de rafraichissement introuvable"
    videos = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "Video":
                videos.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc)
    video = videos[0]
    write = {"type": "SetValue", "componentId": "maReport", "property": "text", "value": REPORT}
    for ev in ("onPlay", "onPause", "onEnd", "onTimeUpdate"):
        video[ev] = video.get(ev, []) + [dict(write)]
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (rapport): patch applique")

# ---------------------------------------------------------------- util.py
path = P("skill", "util.py")
src = open(path, encoding="utf-8").read()
if '"components": ["maReport"' in src:   # also matches ["maReport", "maSeek"]
    print("util (rapport): deja patche")
else:
    old = '''                    "${videoProgressValue}",
                    "${videoPlaying}"
                ]'''
    new = '''                    "${videoProgressValue}",
                    "${videoPlaying}"
                ],
                "components": ["maReport"]'''
    assert src.count(old) == 1, "fix_live_page.py doit etre applique avant"
    open(path, "w", encoding="utf-8").write(src.replace(old, new))
    print("util (rapport): patch applique")

# ---------------------------------------------------------------- lambda_function.py
path = P("skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "maReport" in src:
    print("lambda_function (rapport): deja patche")
else:
    old = '''    args = getattr(handler_input.request_envelope.request, 'arguments', None) or []
    if len(args) >= 4:
        try:
            playing = str(args[3]).lower() in ('true', '1')
            shared_store.set_report(player_id, 'PLAYING' if playing else 'PAUSED',
                                    float(args[2] or 0),
                                    shared_store._rendered_stream.get(player_id))
        except (TypeError, ValueError):
            pass'''
    new = '''    # Position/state written by the Video events into the hidden Text "maReport".
    components = getattr(handler_input.request_envelope.request, 'components', None) or {}
    report = components.get('maReport') if isinstance(components, dict) else None
    if isinstance(report, str) and '|' in report:
        try:
            position, playing = report.split('|', 1)
            shared_store.set_report(player_id,
                                    'PLAYING' if playing.strip().lower() == 'true' else 'PAUSED',
                                    float(position or 0),
                                    shared_store._rendered_stream.get(player_id))
        except (TypeError, ValueError):
            pass'''
    assert src.count(old) == 1, "fix_live_page.py doit etre applique avant"
    open(path, "w", encoding="utf-8").write(src.replace(old, new))
    print("lambda_function (rapport): patch applique")
