"""PATCH: "PlayAudio" while the screen already plays: do not restart.

The French interaction model has no AMAZON.NextIntent / PreviousIntent, so
"Alexa, suivant" was understood as the closest custom intent, PlayAudio
("joue"...), which re-rendered the screen with the same stream: the song
restarted. While the screen is live, PlayAudio now just resumes playback.

usage: python3 fix_play_audio_live.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "def _play_audio_on_live_page" in src:
    print("lambda_function (PlayAudio): deja patche")
    sys.exit(0)
old = '''        logger.info("In LaunchRequestOrPlayAudioHandler")
'''
assert src.count(old) == 1, "lambda_function (PlayAudio): code inattendu"
src = src.replace(old, old + '''        live_response = _play_audio_on_live_page(handler_input)
        if live_response is not None:
            return live_response
''')
src = src.rstrip("\n") + '''


def _play_audio_on_live_page(handler_input):
    """PlayAudio on an Echo whose MA screen is open: resume instead of restarting."""
    if not is_intent_name("PlayAudio")(handler_input):
        return None
    player_id = device_mapping.get_player_for_device(_device_id_from(handler_input))
    if not _page_is_live(player_id):
        return None
    from ask_sdk_model.interfaces.alexa.presentation.apl import ExecuteCommandsDirective
    logger.info("PlayAudio on %s while the screen plays: resume only", player_id)
    rb = handler_input.response_builder
    rb.add_directive(ExecuteCommandsDirective(
        commands=[{"type": "ControlMedia", "componentId": "videoPlayer", "command": "play"}],
        token="playbackToken"))
    return rb.set_should_end_session(None).response
'''
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (PlayAudio): patch applique")
