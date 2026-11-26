"""PATCH: let Music Assistant (2.11+) drive an open APL screen without relaunching the skill.

Music Assistant 2.11 talks to a "screen-aware" skill:
  * POST /ma/push-url  {..., playerId, canSkipSpeech}  -> {"pageLive": bool}
      pageLive true: MA does NOT relaunch the skill by voice (no "voici", no home screen);
      the skill swaps the stream on the open screen itself.
  * POST /ma/control   {playerId, command: pause|resume, canSkipSpeech} -> {"pageLive": bool}
  * GET  /alexa/playback-state?player_id=X
      -> {current, activity, offsetMs, ageSeconds, observedAt}
      MA uses it to correct its elapsed time / play state (and so its current queue item).

This patch implements the three endpoints for the APL screen:
  * the APL refresh event now also reports the Video position and play state;
  * a pending new stream re-renders the screen on the next refresh (~1 s);
  * a pending pause/resume is applied with ControlMedia on the hidden Video.
It also fixes the per-track time display (no Math.max, explicit slider total).

With Music Assistant 2.10 nothing changes for MA (it ignores the extra answers).

usage:
  python3 fix_live_page.py SRC_DIR
where SRC_DIR holds copies of: shared_store.py, music_assistant_api/ma_routes.py,
alexa_api/alexa_routes.py, skill/lambda_function.py, skill/util.py, skill/apl_document.json
(fix_apl_buttons.py, fix_apl_refresh.py and fix_apl_time.py must be applied first).
"""
import json
import os
import sys

base = sys.argv[1]
P = lambda *p: os.path.join(base, *p)


def patch_text(path, label, marker, edits, append=None):
    src = open(path, encoding="utf-8").read()
    if marker in src:
        print(f"{label}: deja patche")
        return
    for old, new in edits:
        assert src.count(old) == 1, f"{label}: code inattendu, patch non applique ({old[:50]!r})"
        src = src.replace(old, new, 1)
    if append:
        src = src.rstrip("\n") + "\n" + append
    open(path, "w", encoding="utf-8").write(src)
    print(f"{label}: patch applique")


# ---------------------------------------------------------------- shared_store.py
patch_text(P("shared_store.py"), "shared_store", "def page_live", [], append='''

# PATCH (live page): state shared between the MA API and the skill.
import threading as _threading
import time as _time

LIVE_PAGE_TIMEOUT = 6          # seconds without APL refresh -> screen considered closed
_live_lock = _threading.Lock()
_live_pages = {}               # player_id -> time of the last APL refresh
_pending = {}                  # player_id -> ["stream" | "pause" | "resume", ...]
_rendered_stream = {}          # player_id -> stream URL shown on the open screen
_reports = {}                  # player_id -> {activity, offsetMs, observedAt, streamUrl}


def page_live(player_id):
    if not player_id:
        return False
    with _live_lock:
        return _time.time() - _live_pages.get(player_id, 0) < LIVE_PAGE_TIMEOUT


def mark_page_live(player_id):
    with _live_lock:
        _live_pages[player_id] = _time.time()


def add_pending(player_id, action):
    with _live_lock:
        _pending.setdefault(player_id, []).append(action)


def pop_pending(player_id):
    with _live_lock:
        return _pending.pop(player_id, [])


def set_report(player_id, activity, offset_ms, stream_url):
    with _live_lock:
        _reports[player_id] = {"activity": activity, "offsetMs": int(offset_ms),
                               "observedAt": _time.time(), "streamUrl": stream_url}


def get_report(player_id):
    with _live_lock:
        r = _reports.get(player_id)
        return dict(r) if r else None
''')

# ---------------------------------------------------------------- ma_routes.py
patch_text(P("music_assistant_api", "ma_routes.py"), "ma_routes", "pageLive", [
    ("""        return jsonify({'status': 'ok', 'version': shared_store._version})""",
     """        # PATCH (live page): MA 2.11 sends playerId + canSkipSpeech and skips the
        # voice relaunch when we answer pageLive: true.
        answer = {'status': 'ok', 'version': shared_store._version}
        player_id = data.get('playerId')
        if player_id:
            live = bool(data.get('canSkipSpeech')) and shared_store.page_live(player_id)
            if live and stream_url != shared_store._rendered_stream.get(player_id):
                shared_store.add_pending(player_id, 'stream')
            answer['pageLive'] = live
        return jsonify(answer)"""),
    ("""    @bp.route('/latest-url', methods=['GET'])""",
     """    @bp.route('/control', methods=['POST'])
    def control():
        # PATCH (live page): pause/resume for the open APL screen.
        data = request.get_json(silent=True) or {}
        player_id = data.get('playerId')
        command = data.get('command')
        if command not in ('pause', 'resume'):
            return jsonify({'error': 'Unsupported command', 'pageLive': False}), 400
        live = bool(data.get('canSkipSpeech')) and shared_store.page_live(player_id)
        if live:
            shared_store.add_pending(player_id, command)
        return jsonify({'pageLive': live})

    @bp.route('/latest-url', methods=['GET'])"""),
])

# ---------------------------------------------------------------- alexa_routes.py
patch_text(P("alexa_api", "alexa_routes.py"), "alexa_routes", "playback-state", [
    ("""    @bp.route('/latest-url', methods=['GET'])""",
     """    @bp.route('/playback-state', methods=['GET'])
    def playback_state():
        # PATCH (live page): what the Echo last reported, for MA's position correction.
        import time as _time
        player_id = request.args.get('player_id')
        report = shared_store.get_report(player_id)
        if not report:
            return jsonify({})
        latest = (shared_store._store or {}).get('streamUrl')
        activity = report['activity']
        if activity == 'PLAYING' and not shared_store.page_live(player_id):
            activity = 'STOPPED'
        return jsonify({
            'current': bool(latest) and report.get('streamUrl') == latest,
            'activity': activity,
            'offsetMs': report['offsetMs'],
            'ageSeconds': max(0.0, _time.time() - report['observedAt']),
            'observedAt': report['observedAt'],
        })

    @bp.route('/latest-url', methods=['GET'])"""),
])

# ---------------------------------------------------------------- util.py (refresh args)
patch_text(P("skill", "util.py"), "util (refresh)", "${videoPlaying}", [
    ('''                "arguments": [
                    "MetadataRefresh",
                    "${refreshTick}"
                ]''',
     '''                "arguments": [
                    "MetadataRefresh",
                    "${refreshTick}",
                    "${videoProgressValue}",
                    "${videoPlaying}"
                ]'''),
])

# ---------------------------------------------------------------- apl_document.json
doc_path = P("skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))
raw = json.dumps(doc)
if "videoPlaying" in raw:
    print("apl_document (live): deja patche")
else:
    assert "MaTimeRoot" in raw, "fix_apl_time.py doit etre applique avant"
    root = doc["layouts"]["AudioPlayer"]["item"][0]
    root["bind"].append({"name": "videoPlaying", "type": "boolean", "value": True})
    # refresh loop in onMount: also report position and play state
    n = 0
    for cmd in root.get("onMount", []):
        for c in cmd.get("commands", []):
            if c.get("type") == "SendEvent" and c.get("arguments", [None])[0] == "MetadataRefresh":
                c["arguments"] = ["MetadataRefresh", "${refreshTick}",
                                  "${videoProgressValue}", "${videoPlaying}"]
                n += 1
    assert n == 1, "boucle de rafraichissement introuvable"
    videos, sliders = [], []

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "Video":
                videos.append(x)
            if x.get("type") == "AlexaSlider":
                sliders.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc)
    video, slider = videos[0], sliders[0]
    playing = lambda v: {"type": "SetValue", "property": "videoPlaying", "value": v}
    video.setdefault("onPlay", []).append(playing(True))
    video["onPause"] = video.get("onPause", []) + [playing(False)]
    video["onEnd"] = video.get("onEnd", []) + [playing(False)]
    video["onTrackFail"] = video.get("onTrackFail", []) + [playing(False)]
    # per-track time: no Math.max (not on every APL runtime)
    s = json.dumps(doc)
    s = s.replace("${Math.max(0, videoProgressValue - trackOffset)}",
                  "${videoProgressValue > trackOffset ? videoProgressValue - trackOffset : 0}")
    s = s.replace("${sliderThumbPosition - Math.max(0, videoProgressValue - trackOffset)}",
                  "${sliderThumbPosition - (videoProgressValue > trackOffset ? videoProgressValue - trackOffset : 0)}")
    assert "Math.max" not in s
    doc = json.loads(s)
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (live): patch applique")

# ---------------------------------------------------------------- lambda_function.py
patch_text(P("skill", "lambda_function.py"), "lambda_function (live)", "_handle_live_page", [
    # explicit slider total with the per-track time
    ('''        {"type": "SetValue", "componentId": "MaTimeRoot",
         "property": "needsResync", "value": True},
    ]''',
     '''        {"type": "SetValue", "componentId": "MaTimeRoot",
         "property": "needsResync", "value": True},
        {"type": "SetValue", "componentId": "slider",
         "property": "totalValue", "value": info.get("duration_ms", 0)},
    ]'''),
    # live page handling at the start of the APL refresh
    ('''        time_commands = None
        try:
            time_commands = _sync_now_playing_from_ma(handler_input)''',
     '''        try:
            live_response = _handle_live_page(handler_input)
            if live_response is not None:
                return live_response
        except Exception:
            logger.exception("Failed to handle live page actions")

        time_commands = None
        try:
            time_commands = _sync_now_playing_from_ma(handler_input)'''),
    ("\nclass APLUserEventHandler(AbstractRequestHandler):",
     '''

# PATCH (live page): MA 2.11 drives the open APL screen (see shared_store).
def _handle_live_page(handler_input):
    """Record the open screen and its position; apply what MA queued for it.

    Returns a full response when the screen must be re-rendered (new stream),
    None otherwise (pause/resume commands are added to the normal refresh)."""
    import shared_store
    from ask_sdk_model.interfaces.alexa.presentation.apl import ExecuteCommandsDirective
    device_id = _device_id_from(handler_input)
    player_id = device_mapping.get_player_for_device(device_id)
    if not player_id:
        return None
    shared_store.mark_page_live(player_id)
    store = shared_store._store or {}
    if player_id not in shared_store._rendered_stream and store.get('streamUrl'):
        shared_store._rendered_stream[player_id] = store['streamUrl']

    args = getattr(handler_input.request_envelope.request, 'arguments', None) or []
    if len(args) >= 4:
        try:
            playing = str(args[3]).lower() in ('true', '1')
            shared_store.set_report(player_id, 'PLAYING' if playing else 'PAUSED',
                                    float(args[2] or 0),
                                    shared_store._rendered_stream.get(player_id))
        except (TypeError, ValueError):
            pass

    actions = shared_store.pop_pending(player_id)
    if not actions:
        return None
    rb = handler_input.response_builder
    after = actions[actions.index('stream') + 1:] if 'stream' in actions else actions
    if 'stream' in actions and store.get('streamUrl'):
        url = store['streamUrl']
        logger.info("Live page %s: new stream, re-rendering the screen", player_id)
        util.play(url=url, offset=0, text=None, response_builder=rb, supports_apl=True)
        shared_store._rendered_stream[player_id] = url
        _now_playing_state.pop(player_id, None)
    media = [{"type": "ControlMedia", "componentId": "videoPlayer",
              "command": "pause" if a == 'pause' else "play"}
             for a in after if a in ('pause', 'resume')]
    if media:
        logger.info("Live page %s: %s", player_id, ", ".join(after))
        rb.add_directive(ExecuteCommandsDirective(commands=media[-1:], token="playbackToken"))
    if 'stream' not in actions:
        util.schedule_apl_refresh(rb)
    rb.set_should_end_session(None)
    return rb.response


class APLUserEventHandler(AbstractRequestHandler):'''),
])
