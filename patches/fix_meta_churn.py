"""PATCH: send the screen's title/cover only when they change.

data.get_latest() always answers "changed": every refresh (about every
1.5 s) sent the title, texts and image sources to the screen again.
Now only a real change (or a new screen) sends them.

usage: python3 fix_meta_churn.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "_meta_signature" in src:
    print("lambda_function (metadonnees): deja patche")
    sys.exit(0)
old = '''            changed = bool(result and result.get('changed'))
'''
new = '''            changed = bool(result and result.get('changed')) and _meta_changed(handler_input)
'''
assert src.count(old) == 1, "lambda_function (metadonnees): code inattendu"
src = src.replace(old, new).rstrip("\n") + '''


_meta_signature = {}        # player/device -> (screen, title, texts, images) last sent


def _meta_changed(handler_input):
    device_id = _device_id_from(handler_input)
    key = device_mapping.get_player_for_device(device_id) or device_id
    i = data.info or {}
    sig = (_screen_started.get(key, 0), i.get("primaryText"), i.get("secondaryText"),
           i.get("coverImageSource"), i.get("backgroundImageSource"))
    if _meta_signature.get(key) == sig:
        return False
    _meta_signature[key] = sig
    return True
'''
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (metadonnees): patch applique")
