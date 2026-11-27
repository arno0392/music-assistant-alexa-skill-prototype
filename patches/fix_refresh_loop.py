"""PATCH: a refresh loop that cannot die.

The screen asked the skill for news through a chain: each refresh answer
scheduled the next one. A single lost answer (slow, failed, or replaced by
another response) ended the chain for good: the screen was no longer "live",
MA fell back to voice relaunches, and voice commands then went to the Echo's
own player (song restarted instead of next/previous).

The document's onMount loop now repeats by itself (100000 times, one event
per second, on its own sequencer "maRefresh") and the skill no longer
schedules refreshes (the scheduled ones would replace the loop, being on the
same sequencer).

Requires fix_apl_sequencer.py.
usage: python3 fix_refresh_loop.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
REPEAT, DELAY = 100000, 1000

doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
loops = []


def walk(x):
    if isinstance(x, dict):
        if x.get("type") == "Sequential" and x.get("sequencer") == "maRefresh" and "MetadataRefresh" in json.dumps(x):
            loops.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)


walk(doc)
assert len(loops) == 1, "fix_apl_sequencer.py doit etre applique avant"
loop = loops[0]
if loop.get("repeatCount") == REPEAT:
    print("apl_document (boucle): deja patche")
else:
    loop["repeatCount"] = REPEAT
    idle = [c for c in loop["commands"] if c.get("type") == "Idle"]
    assert idle, "apl_document (boucle): Idle introuvable"
    idle[0]["delay"] = DELAY
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (boucle): patch applique")

path = os.path.join(base, "skill", "util.py")
src = open(path, encoding="utf-8").read()
marker = "    return  # the document's onMount loop sends the refreshes (fix_refresh_loop.py)\n"
if marker in src:
    print("util (boucle): deja patche")
else:
    old = '''    This keeps refreshes alive even if the onMount loop does not repeat.
    """
    if not apl_enabled():
        return
'''
    assert src.count(old) == 1, "util (boucle): code inattendu"
    src = src.replace(old, '''    This keeps refreshes alive even if the onMount loop does not repeat.
    """
''' + marker + '''    if not apl_enabled():
        return
''')
    open(path, "w", encoding="utf-8").write(src)
    print("util (boucle): patch applique")
