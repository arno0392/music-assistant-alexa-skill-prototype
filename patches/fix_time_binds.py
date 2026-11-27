"""PATCH: keep the per-track time values on the Video component itself.

The track offset / pending elapsed / resync flag were binds of the root
container "MaTimeRoot", written by the skill (SetValue on MaTimeRoot) and by
the Video's own handlers (SetValue without componentId = on the Video). APL
documents SetValue as updating a bind *of the target component*: the Video
handlers did not reliably reach the container's binds, so every resync (track
change, seek, MA correction) was silently lost and the slider kept counting
from the start of the stream.

The three values are now binds of the Video ("videoPlayer"): its handlers read
and write their own binds, and the skill targets "videoPlayer".

Requires fix_seek_offset.py.
usage: python3 fix_time_binds.py SRC_DIR
"""
import json
import os
import re
import sys

base = sys.argv[1]
NAMES = ("trackOffset", "pendingElapsed", "needsResync")

# ---------------------------------------------------------------- apl_document.json
doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
root = doc["layouts"]["AudioPlayer"]["item"][0]
assert root.get("id") == "MaTimeRoot", "fix_apl_time.py doit etre applique avant"
videos = []


def walk(x):
    if isinstance(x, dict):
        if x.get("type") == "Video" and x.get("id") == "videoPlayer":
            videos.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)


walk(doc)
assert len(videos) == 1, f"apl_document (binds video): {len(videos)} Video trouvees"
video = videos[0]
if any(b.get("name") == "needsResync" for b in video.get("bind", [])):
    print("apl_document (binds video): deja patche")
else:
    defs = [dict(b) for b in root["bind"] if b["name"] in NAMES]
    assert len(defs) == 3, "apl_document (binds video): binds de temps introuvables"
    video.setdefault("bind", []).extend(defs)
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (binds video): patch applique")

# ---------------------------------------------------------------- lambda_function.py
path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
pattern = re.compile(r'"componentId": "MaTimeRoot"(,\s*)"property": "(' + "|".join(NAMES) + r')"')
if '"componentId": "videoPlayer",' in src and not pattern.search(src):
    print("lambda_function (binds video): deja patche")
else:
    src, n = pattern.subn(r'"componentId": "videoPlayer"\1"property": "\2"', src)
    assert n == 4, f"lambda_function (binds video): {n} SetValue trouves au lieu de 4"
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (binds video): patch applique")
