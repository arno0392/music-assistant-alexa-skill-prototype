"""PATCH: seeking back to the very start of the track restarts it.

A seek to 0 s (slider or TV remote pulled fully left) did nothing in MA; the track
is now restarted from the start, like "start over".

usage: python3 fix_seek_start.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "seek to the start: restarting the track" in src:
    print("lambda_function (retour au debut): deja patche")
    sys.exit(0)
old = '''            _seek_hint[player_id] = (seconds, _time.time(), _shown_item_id(player_id))
            ma_control.seek_player(player_id, seconds)'''
assert src.count(old) == 1, "live page seek not found"
src = src.replace(old, '''            if seconds < 1:
                logger.info("Live page %s: seek to the start: restarting the track", player_id)
                ma_control.send_player_command(player_id, "start_over", ref_item_id=_shown_item_id(player_id))
            else:
                _seek_hint[player_id] = (seconds, _time.time(), _shown_item_id(player_id))
                ma_control.seek_player(player_id, seconds)''')
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (retour au debut): patch applique")
