"""PATCH: "Alexa, suivant / précédent" while the screen is open.

The Next/Previous intent ended the session (shouldEndSession true), which
closes the APL screen: MA then had no live page and fell back to the voice
relaunch ("voici"), or the change was lost. While the screen is live the
session is now left open (shouldEndSession unset), like the screen buttons.

usage: python3 fix_voice_next.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "def _page_is_live" in src:
    print("lambda_function (suivant vocal): deja patche")
    sys.exit(0)
old = '''        handler_input.response_builder.set_should_end_session(True)
        return handler_input.response_builder.response


class CancelOrStopIntentHandler('''
new = '''        # keep the session, hence the screen, open on a screen Echo showing MA
        logger.info("Voice %s on %s (screen live: %s)", command, player_id, _page_is_live(player_id))
        handler_input.response_builder.set_should_end_session(None if _page_is_live(player_id) else True)
        return handler_input.response_builder.response


class CancelOrStopIntentHandler('''
assert src.count(old) == 1, "lambda_function (suivant vocal): code inattendu"
src = src.replace(old, new).rstrip("\n") + '''


def _page_is_live(player_id):
    try:
        import shared_store
        return bool(player_id) and shared_store.page_live(player_id)
    except Exception:
        return False
'''
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (suivant vocal): patch applique")
