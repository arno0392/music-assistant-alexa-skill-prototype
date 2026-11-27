"""PATCH: keep the APL refresh loop alive when the screen is touched.

APL stops whatever runs on the MAIN sequencer as soon as the screen is touched
(a skip button, play/pause, the slider). The refresh loop (onMount and the
Idle+SendEvent chain sent back by the skill) ran on MAIN, so the first touch
killed it: no more refresh, the screen was no longer "live" for MA 2.11, MA
fell back to the voice relaunch ("voici"), pending pause/stream were never
applied and the session could end after a pause.

The loop now runs on its own named sequencer "maRefresh", which touches do not
stop. Also logs every /ma/push-url and /ma/control with the pageLive answer.

Requires every previous patch (fix_apl_followups.py last).
usage: python3 fix_apl_sequencer.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
P = lambda *p: os.path.join(base, *p)
SEQ = "maRefresh"


def patch_text(path, label, marker, edits):
    src = open(path, encoding="utf-8").read()
    if marker in src:
        print(f"{label}: deja patche")
        return
    for old, new in edits:
        assert src.count(old) == 1, f"{label}: code inattendu, patch non applique ({old[:60]!r})"
        src = src.replace(old, new)
    open(path, "w", encoding="utf-8").write(src)
    print(f"{label}: patch applique")


# ---------------------------------------------------------------- apl_document.json
doc_path = P("skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
if f'"sequencer": "{SEQ}"' in json.dumps(doc):
    print("apl_document (sequenceur): deja patche")
else:
    found = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "Sequential" and x.get("repeatCount") == -1 and "MetadataRefresh" in json.dumps(x):
                x["sequencer"] = SEQ
                found.append(x)
                return
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(doc)
    assert len(found) == 1, f"apl_document (sequenceur): {len(found)} boucles de rafraichissement trouvees"
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (sequenceur): patch applique")


# ---------------------------------------------------------------- util.py
patch_text(P("skill", "util.py"), "util (sequenceur)", '"sequencer": "maRefresh"', [(
    """        response_builder.add_directive(
            ExecuteCommandsDirective(
                commands=commands,
                token="playbackToken"
            )
        )
    except Exception:
        logging.exception('Error while scheduling APL refresh')""",
    """        # PATCH: own sequencer, so that touching the screen does not stop it
        commands = [{"type": "Sequential", "sequencer": "maRefresh", "commands": commands}]
        response_builder.add_directive(
            ExecuteCommandsDirective(
                commands=commands,
                token="playbackToken"
            )
        )
    except Exception:
        logging.exception('Error while scheduling APL refresh')""")])


# ---------------------------------------------------------------- ma_routes.py
patch_text(P("music_assistant_api", "ma_routes.py"), "ma_routes (logs)", "_ma_log", [
    ("import shared_store\n",
     "import shared_store\nimport logging as _logging\n_ma_log = _logging.getLogger('ma_routes')\n"),
    ("            answer['pageLive'] = live\n",
     "            answer['pageLive'] = live\n"
     "            _ma_log.info(\"push-url %s: pageLive=%s (%s)\", player_id, live,\n"
     "                         (data.get('title') or '')[:40])\n"),
    ("        if live:\n            shared_store.add_pending(player_id, command)\n",
     "        if live:\n            shared_store.add_pending(player_id, command)\n"
     "        _ma_log.info(\"control %s %s: pageLive=%s\", player_id, command, live)\n"),
])
