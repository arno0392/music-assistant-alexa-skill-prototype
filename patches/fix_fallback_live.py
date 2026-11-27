"""PATCH: an utterance Alexa does not understand must not close the screen.

AMAZON.FallbackIntent answered "Sorry, I could not understand..." and ended
the session, which closes the APL screen (MA then relaunches by voice). While
the screen is live it now just keeps playing, silently.

Requires fix_voice_next.py (_page_is_live).
usage: python3 fix_fallback_live.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "Fallback while the screen plays" in src:
    print("lambda_function (fallback): deja patche")
    sys.exit(0)
old = '''        logger.info("In UnhandledIntentHandler")
'''
assert src.count(old) == 1, "lambda_function (fallback): code inattendu"
src = src.replace(old, old + '''        _player = device_mapping.get_player_for_device(_device_id_from(handler_input))
        if _page_is_live(_player):
            logger.info("Fallback while the screen plays on %s: ignored", _player)
            return handler_input.response_builder.set_should_end_session(None).response
''')
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (fallback): patch applique")
