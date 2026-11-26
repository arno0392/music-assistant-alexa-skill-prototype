"""PATCH: APL screen usability.

* Seek: the slider used ControlMedia seek on the hidden Video, but the flow
  stream cannot be seeked, so the track restarted. The slider now sends
  ["Seek", <ms in the current track>] and the skill asks Music Assistant to seek
  the queue (MA restarts the flow stream at that position).
* Visual feedback on the previous/next buttons (dim while pressed).
* Each new screen (skill launched again by MA) restarts the per-track time
  sync, so the elapsed/total time is set again after "next" from MA.

Requires fix_apl_buttons.py, fix_apl_time.py and fix_live_page.py first.
usage: python3 fix_apl_ux.py SRC_DIR MA_CONTROL
  SRC_DIR    : same as fix_live_page.py (skill/apl_document.json, skill/lambda_function.py)
  MA_CONTROL : the patched ma_control.py copy
"""
import json
import os
import sys

base, ma_path = sys.argv[1], sys.argv[2]
P = lambda *p: os.path.join(base, *p)

# ---------------------------------------------------------------- apl_document.json
doc_path = P("skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
raw = json.dumps(doc)
if '"Seek"' in raw:
    print("apl_document (ux): deja patche")
else:
    assert "MaSkipButtons" in raw and "trackOffset" in raw, "patches precedents manquants"
    sliders, touch = [], []

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "AlexaSlider":
                sliders.append(x)
            if x.get("type") == "TouchWrapper" and any(
                    c.get("type") == "SendEvent" and c.get("arguments", [""])[0] in ("Next", "Previous")
                    for c in x.get("onPress", [])):
                touch.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc)
    assert len(sliders) == 1 and len(touch) == 2, "slider/boutons introuvables"
    slider = sliders[0]
    slider["onUpCommand"] = [
        {"type": "SetValue", "property": "sliderActive", "value": False},
        {"type": "SendEvent", "arguments": ["Seek", "${sliderThumbPosition}"]},
    ]
    for t in touch:
        send = t["onPress"]
        t["onPress"] = [{
            "type": "Sequential",
            "commands": [{"type": "SetValue", "property": "opacity", "value": 0.35}]
                        + send + [{"type": "Idle", "delay": 250}],
            "finally": [{"type": "SetValue", "property": "opacity", "value": 1}],
        }]
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (ux): patch applique")

# ---------------------------------------------------------------- ma_control.py
src = open(ma_path, encoding="utf-8").read()
if "def seek_player" in src:
    print("ma_control (seek): deja patche")
else:
    src = src.rstrip("\n") + '''


# PATCH: seek the active queue of a player (position in seconds in the current track).
async def _seek(server_url, token, player_id, seconds):
    async with aiohttp.ClientSession() as session:
        async with MusicAssistantClient(server_url, session, token=token) as client:
            queue = await client.player_queues.get_active_queue(player_id)
            if queue is None:
                raise ValueError(f"No active queue for player {player_id}")
            await client.player_queues.seek(queue.queue_id, int(seconds))


def seek_player(player_id, seconds):
    server_url = get_env_secret("MA_API_URL")
    token = get_env_secret("MA_API_TOKEN")
    if not server_url or not player_id:
        return False
    try:
        asyncio.run(_seek(server_url, token, player_id, max(0, seconds)))
        return True
    except Exception:
        logger.exception("Seek to %ss failed for MA player %s", seconds, player_id)
        return False
'''
    open(ma_path, "w", encoding="utf-8").write(src)
    print("ma_control (seek): patch applique")

# ---------------------------------------------------------------- lambda_function.py
path = P("skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "class APLSeekEventHandler" in src:
    print("lambda_function (seek): deja patche")
else:
    handler = '''

class APLSeekEventHandler(AbstractRequestHandler):
    """PATCH: the APL slider sends ["Seek", ms]; seek the MA queue instead of
    the (unseekable) flow stream."""
    def can_handle(self, handler_input):
        if not is_request_type("Alexa.Presentation.APL.UserEvent")(handler_input):
            return False
        args = getattr(handler_input.request_envelope.request, 'arguments', None) or []
        return bool(args) and args[0] == "Seek"

    def handle(self, handler_input):
        args = handler_input.request_envelope.request.arguments
        try:
            seconds = float(args[1]) / 1000.0
        except (IndexError, TypeError, ValueError):
            seconds = None
        player_id = device_mapping.get_player_for_device(_device_id_from(handler_input))
        logger.info("In APLSeekEventHandler: %ss (player=%s)", seconds, player_id)
        if player_id and seconds is not None:
            ma_control.seek_player(player_id, seconds)
        return handler_input.response_builder.set_should_end_session(None).response

'''
    anchor = "\nclass APLUserEventHandler(AbstractRequestHandler):"
    reg = "sb.add_request_handler(APLSkipEventHandler())"
    assert src.count(anchor) == 1 and src.count(reg) == 1, "fix_apl_buttons.py doit etre applique avant"
    src = src.replace(anchor, handler + anchor, 1)
    src = src.replace(reg, "sb.add_request_handler(APLSeekEventHandler())\n" + reg, 1)
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (seek): patch applique")

# ---------------------------------------------------------------- lambda_function.py (new screen)
src = open(path, encoding="utf-8").read()
if "_reset_screen_state" in src:
    print("lambda_function (nouvel ecran): deja patche")
else:
    old = '''        logger.info("Playing URL: %s", url)'''
    new = '''        logger.info("Playing URL: %s", url)
        _reset_screen_state(handler_input, url)'''
    helper = '''

def _reset_screen_state(handler_input, url):
    """PATCH: a new screen is rendered: restart the time sync for this player."""
    try:
        import shared_store
        player_id = device_mapping.get_player_for_device(_device_id_from(handler_input))
        if player_id:
            _now_playing_state.pop(player_id, None)
            shared_store._rendered_stream[player_id] = (shared_store._store or {}).get('streamUrl') or url
    except Exception:
        logger.exception("Failed to reset screen state")

'''
    anchor = "\nclass APLUserEventHandler(AbstractRequestHandler):"
    assert src.count(old) == 1 and src.count(anchor) == 1, "code inattendu, patch non applique"
    src = src.replace(old, new, 1).replace(anchor, helper + anchor, 1)
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (nouvel ecran): patch applique")
