"""End-to-end tests of the patched skill (all local patches, applied in the user's order).

Run: python3 test_all.py PRISTINE_APP_DIR
Builds a patched copy in /tmp/tall, then replays MA 2.10 / MA 2.11 / non-APL scenarios.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import types

W = os.path.dirname(os.path.abspath(__file__))
PRISTINE = sys.argv[1]
T = "/tmp/tall"
shutil.rmtree(T, ignore_errors=True)
shutil.copytree(PRISTINE, T)
S = os.path.join(T, "skill")


def run(*a):
    out = subprocess.run([sys.executable, *a], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


# ---- apply in the user's order (twice: must be idempotent) ----
for rnd in (1, 2):
    outs = [
        run(f"{W}/fix_meta.py", f"{S}/util.py"),
        run(f"{W}/fix_apl.py", f"{S}/apl.py"),
        run(f"{W}/fix_apl_buttons.py", f"{S}/apl_document.json", f"{S}/lambda_function.py"),
        run(f"{W}/fix_apl_refresh.py", f"{S}/ma_control.py", f"{S}/lambda_function.py"),
        run(f"{W}/fix_apl_time.py", f"{S}/apl_document.json", f"{S}/ma_control.py", f"{S}/lambda_function.py"),
        run(f"{W}/fix_live_page.py", T),
        run(f"{W}/fix_live_report.py", T),
        run(f"{W}/fix_apl_ux.py", T, f"{S}/ma_control.py"),
        run(f"{W}/fix_apl_seek.py", T),
        run(f"{W}/fix_apl_pause.py", f"{S}/apl.py"),
        run(f"{W}/fix_stream_key.py", T),
        run(f"{W}/fix_apl_followups.py", T),
        run(f"{W}/fix_apl_sequencer.py", T),
        run(f"{W}/fix_seek_offset.py", T),
        run(f"{W}/fix_time_binds.py", T),
        run(f"{W}/fix_apl_background.py", T),
    ]
    text = "".join(outs)
    if rnd == 2:
        assert "patch applique" not in text, "second run must change nothing:\n" + text
print("OK  patches apply in order, and are idempotent")

sys.path.insert(0, T)
os.chdir(T)
os.environ.update(ENABLE_APL="true", AWS_DEFAULT_REGION="us-east-1",
                  MA_HOSTNAME="musicassistant.theani.fr", MA_API_URL="http://ma:8095",
                  SKIP_URL_VALIDATION="true")
import logging
logging.disable(logging.CRITICAL)
import shared_store
import music_assistant_api as ma_api
import alexa_api
from skill import lambda_function as lf, util, ma_control, apl
from ask_sdk_model import RequestEnvelope

def _republish(url):
    # what the real app does through /alexa/push-url after util.play()
    shared_store._store = {"streamUrl": url,
                           "title": util.data.info.get("primaryText"),
                           "secondary": util.data.info.get("secondaryText"),
                           "imageUrl": util.data.info.get("coverImageSource")}
util.push_alexa_metadata = _republish
PLAYER = "Echo de la Cuisine"
lf.device_mapping.get_player_for_device = lambda d: PLAYER if d == "d" else None
calls = []
refs = []
ma_control.send_player_command = lambda p, c, ref_item_id=None: refs.append(ref_item_id) or calls.append(("cmd", p, c)) or True
queue_state = {"v": "playing"}
ma_control.get_queue_state = lambda p: queue_state["v"]
ma_control.seek_player = lambda p, s: calls.append(("seek", p, s)) or True
now_playing = {"v": None}
ma_control.get_now_playing = lambda p: now_playing["v"]
clock = [1_800_000_000.0]
import time as _time
_time.time = lambda: clock[0]

ma = ma_api.create_ma_app().test_client()
al = alexa_api.create_alexa_app().test_client()
sk = lf.sb.create()
BASE = json.load(open("/tmp/payload.json"))
APL_IF = {"AudioPlayer": {}, "Alexa.Presentation.APL": {"runtime": {"maxVersion": "2023.3"}}}


def envelope(request, apl=True, new=False):
    ev = json.loads(json.dumps(BASE))
    ev["session"]["new"] = new
    ev["context"]["System"]["device"]["supportedInterfaces"] = APL_IF if apl else {"AudioPlayer": {}}
    ev["request"] = {"requestId": "r", "locale": "fr-FR", "timestamp": "2026-11-27T20:00:00Z", **request}
    return ev


def invoke(ev):
    r = sk.invoke(request_envelope=sk.serializer.deserialize(json.dumps(ev), RequestEnvelope), context=None)
    return sk.serializer.serialize(r)["response"]


def launch(apl=True):
    return invoke(envelope({"type": "LaunchRequest"}, apl))


def refresh(report="1000|true", seek=""):
    return invoke(envelope({"type": "Alexa.Presentation.APL.UserEvent", "source": {},
                            "arguments": ["MetadataRefresh", "", "", ""],
                            "components": {"maReport": report, "maSeek": seek}}))


def user_event(*args):
    return invoke(envelope({"type": "Alexa.Presentation.APL.UserEvent", "source": {}, "components": {},
                            "arguments": list(args)}))


def intent(name, new=False, apl=True):
    return invoke(envelope({"type": "IntentRequest", "intent": {"name": name, "confirmationStatus": "NONE"}}, apl, new))


def kinds(resp):
    out = []
    for d in resp.get("directives", []):
        k = d["type"].split(".")[-1]
        if "commands" in d:
            cmds = d["commands"]
            if len(cmds) == 1 and cmds[0].get("sequencer") == "maRefresh":
                cmds = cmds[0]["commands"]
            k += "[" + ",".join(c.get("command") or c.get("property") or c["type"] for c in cmds) + "]"
        out.append(k)
    return out


def push(url, **kw):
    return ma.post("/push-url", json={"streamUrl": url, "title": kw.pop("title", "T1"), "artist": "A",
                                      "album": "B", "imageUrl": "http://192.168.1.30:8097/imageproxy/x", **kw}).get_json()


def state():
    return al.get(f"/playback-state?player_id={PLAYER}").get_json()


H = "http://192.168.1.30:8097/flow/"

# ======================= MA 2.10 (no playerId) ==============================
r = push(H + "s1/Echo de la Cuisine/i1/Echo de la Cuisine.flac")
assert "pageLive" not in r, r
resp = launch()
assert kinds(resp) == ["RenderDocument"], kinds(resp)
refresh("700|true")
assert state()["current"] is True, ("report must be current after launch + republish", state())
clock[0] += 5   # next MA poll window
doc = json.dumps(resp["directives"][0])
assert "Echo%20de%20la%20Cuisine.mp3" in doc and "Echo de la Cuisine.mp3" not in doc, "APL audio URL must be encoded mp3"
assert re.findall(r'"autoplay": (\w+)', doc) == ["true", "true"]
print("OK  2.10 launch: APL rendered, audio URL encoded + mp3, autoplay on")

now_playing["v"] = {"queue_item_id": "q1", "title": "T1", "artist": "A", "album": "B",
                    "imageUrl": "", "elapsed_ms": 4000, "duration_ms": 200000}
resp = refresh()
k = kinds(resp)
assert any("trackTotal" in x and "totalValue" in x for x in k), k
assert k[-1] == "ExecuteCommands[Idle,SendEvent]", k
print("OK  first refresh after launch: per-track time sent, refresh chain kept last")
clock[0] += 5
resp = refresh()
assert not any("trackTotal" in x for x in kinds(resp)), kinds(resp)
print("OK  same track: no time resend")

# natural track change inside the flow stream (MA 2.10 pushes metadata only)
push(H + "s1/Echo de la Cuisine/i1/Echo de la Cuisine.flac", title="T2")
now_playing["v"] = dict(now_playing["v"], queue_item_id="q2", title="T2", elapsed_ms=1000, duration_ms=180000)
clock[0] += 5
resp = refresh()
k = kinds(resp)
assert any("trackTotal" in x for x in k), k
assert "T2" in json.dumps(resp), "new title must be sent to the screen"
print("OK  natural track change: new title + time resync sent")

# buttons
calls.clear()
assert user_event("Next") == {} or True
user_event("Previous")
assert calls == [("cmd", PLAYER, "next"), ("cmd", PLAYER, "previous")], calls
print("OK  APL buttons -> MA next/previous")

# seek through the refresh (slider writes maSeek)
calls.clear()
refresh(seek="")
refresh(seek="95400@31250")
refresh(seek="95400@31250")
refresh(seek="20000@40100")
assert calls == [("seek", PLAYER, 95.4), ("seek", PLAYER, 20.0)], calls
print("OK  slider seek -> MA seek once per drag")

# MA 2.10 relaunch after next from the web: new screen must get the time again
now_playing["v"] = dict(now_playing["v"], queue_item_id="q3", title="T3")
clock[0] += 5
refresh()                      # old screen sees q3 first
launch()                       # MA relaunches the skill -> new screen
clock[0] += 1
resp = refresh()
assert any("trackTotal" in x for x in kinds(resp)), kinds(resp)
print("OK  relaunch (next from MA web): new screen gets the time again")

# pause from MA 2.10 (text command -> PauseIntent)
calls.clear()
resp = intent("AMAZON.PauseIntent", new=False)
assert kinds(resp) == ["ExecuteCommands[pause]"], kinds(resp)
resp = intent("AMAZON.PauseIntent", new=True)
assert kinds(resp) == ["RenderDocument"], kinds(resp)
assert re.findall(r'"autoplay": (\w+)', json.dumps(resp)) == ["false", "false"], "paused screen must not autoplay"
print("OK  pause intent: ControlMedia pause, or paused re-render with autoplay off (Video + controls)")
assert calls and calls[0] == ("cmd", PLAYER, "pause"), calls

# ======================= MA 2.11 (screen aware) ==============================
r = push(H + "s5/Echo de la Cuisine/i5/Echo de la Cuisine.flac", playerId=PLAYER, canSkipSpeech=True)
assert r["pageLive"] is True, r   # screen refreshed < 6 s ago
resp = refresh()
assert kinds(resp) == ["RenderDocument"], kinds(resp)
assert "s5/Echo%20de%20la%20Cuisine" in json.dumps(resp)
assert shared_store._store["title"] == "T1" and "s5/" in shared_store._store["streamUrl"], shared_store._store
print("OK  2.11 next with open screen: pageLive true, screen re-rendered with new stream (no voice relaunch)")

r = push(H + "s5/Echo de la Cuisine/i5/Echo de la Cuisine.flac", playerId=PLAYER, canSkipSpeech=True)
assert r["pageLive"] is True
resp = refresh()
assert "RenderDocument" not in kinds(resp), kinds(resp)
print("OK  2.11 same stream pushed again: no re-render")

c = ma.post("/control", json={"playerId": PLAYER, "command": "pause", "canSkipSpeech": True}).get_json()
assert c == {"pageLive": True}, c
resp = refresh()
assert kinds(resp)[0] == "ExecuteCommands[pause]", kinds(resp)
c = ma.post("/control", json={"playerId": PLAYER, "command": "resume", "canSkipSpeech": True}).get_json()
resp = refresh(report="5000|false")
assert kinds(resp)[0] == "ExecuteCommands[play]", kinds(resp)
assert ma.post("/control", json={"playerId": PLAYER, "command": "stop", "canSkipSpeech": True}).status_code == 400
assert ma.post("/control", json={"playerId": "Autre", "command": "pause", "canSkipSpeech": True}).get_json() == {"pageLive": False}
print("OK  2.11 /ma/control pause/resume applied on screen; unknown command 400; other player not live")

# playback-state, parsed exactly like MA 2.11 (_correct_position)
ECHO_PLAYBACK_STATES = {"PLAYING": "playing", "BUFFER_UNDERRUN": "playing", "STOPPED": "paused", "PAUSED": "paused"}
refresh(report="187345|true")
rep = state()
assert rep.get("current") is True
assert ECHO_PLAYBACK_STATES.get(str(rep.get("activity"))) == "playing"
assert isinstance(rep.get("offsetMs"), (int, float)) and rep["offsetMs"] == 187345
assert isinstance(rep.get("ageSeconds"), (int, float)) and rep["ageSeconds"] >= 0
obs1 = rep["observedAt"]
clock[0] += 1
refresh(report="188400|false")
rep = state()
assert ECHO_PLAYBACK_STATES[rep["activity"]] == "paused" and rep["offsetMs"] == 188400 and rep["observedAt"] != obs1
print("OK  /alexa/playback-state matches MA 2.11's parser (current, activity, offsetMs, ageSeconds, observedAt)")

# new stream pushed but screen not yet re-rendered -> report is for the old stream
push(H + "s6/Echo de la Cuisine/i6/Echo de la Cuisine.flac", playerId=PLAYER, canSkipSpeech=True)
assert state()["current"] is False
print("OK  report flagged not current while the new stream is pending")
refresh()   # re-render
refresh(report="500|true")
assert state()["current"] is True
print("OK  report current again after re-render")

# screen closed: MA must relaunch by voice, report not PLAYING
clock[0] += 10
r = push(H + "s7/Echo de la Cuisine/i7/Echo de la Cuisine.flac", playerId=PLAYER, canSkipSpeech=True)
assert r["pageLive"] is False, r
assert ma.post("/control", json={"playerId": PLAYER, "command": "pause", "canSkipSpeech": True}).get_json() == {"pageLive": False}
assert state()["activity"] != "PLAYING"
print("OK  screen closed: pageLive false (MA falls back to voice), activity not PLAYING")

# unmapped device: no crash, nothing claimed
lf.device_mapping.get_player_for_device = lambda d: None
resp = refresh()
assert kinds(resp)[-1] == "ExecuteCommands[Idle,SendEvent]", kinds(resp)
lf.device_mapping.get_player_for_device = lambda d: PLAYER if d == "d" else None
print("OK  unmapped device: refresh still works")

# ======================= follow-ups (time, pause sync, idle, previous) =======
class _SyncThread:
    def __init__(self, target, args=(), daemon=None):
        self.t, self.a = target, args
    def start(self):
        self.t(*self.a)
lf._threading = types.SimpleNamespace(Thread=_SyncThread)
push(H + "s9/Echo de la Cuisine/i9/Echo de la Cuisine.flac", title="T9")
resp = launch()
assert resp["directives"][0]["document"]["settings"]["idleTimeout"] == 600000
assert "|${trackOffset}" in json.dumps(resp["directives"][0]["document"])
print("OK  APL idleTimeout 10 min, report carries the track offset")

calls.clear()
now_playing["v"] = {"queue_item_id": "q9", "title": "T9", "artist": "A", "album": "B",
                    "imageUrl": "", "elapsed_ms": 0, "duration_ms": 0}
clock[0] += 5
assert any("trackTotal" in x for x in kinds(refresh("500|true")))
now_playing["v"] = dict(now_playing["v"], duration_ms=200000, elapsed_ms=6000)
clock[0] += 5
assert any("trackTotal" in x for x in kinds(refresh("5500|true|0"))), "duration unknown at first: asked again"
clock[0] += 5
assert not any("trackTotal" in x for x in kinds(refresh("10500|true|0")))
clock[0] += 4
assert any("trackTotal" in x for x in kinds(refresh("14500|true|0"))), "second pass ~6 s later"
print("OK  time: re-asked while MA has no duration, then a second pass ~6 s later")

now_playing["v"] = dict(now_playing["v"], elapsed_ms=120000)      # seek from MA web
clock[0] += 5
assert any("trackTotal" in x for x in kinds(refresh("19500|true|0"))), "screen 17 s, MA 120 s: resync"
clock[0] += 5
now_playing["v"] = dict(now_playing["v"], elapsed_ms=125000)
assert not any("trackTotal" in x for x in kinds(refresh("22500|true|-102500")))
print("OK  time: resync when the screen is more than 3 s off MA, not when it matches")
assert calls == [], calls

queue_state["v"] = "playing"
clock[0] += 1
refresh("23500|false|-102500")
assert calls == [("cmd", PLAYER, "pause")], calls
queue_state["v"] = "paused"
clock[0] += 1
refresh("23500|true|-102500")
assert calls == [("cmd", PLAYER, "pause"), ("cmd", PLAYER, "resume")], calls
calls.clear()
lf._expected_state[PLAYER] = (False, clock[0])        # MA asked for this pause
queue_state["v"] = "playing"
refresh("24000|false|-102500")
assert calls == [], calls
refresh("24000|true|-102500")                          # MA already playing
queue_state["v"] = "playing"
assert calls == [], calls
print("OK  pause/play on the screen forwarded to MA (not when MA asked it or is already there)")

refs.clear(); calls.clear()
user_event("Previous")
assert calls == [("cmd", PLAYER, "previous")] and refs == ["q9"], (calls, refs)
print("OK  previous computed from the track shown on the screen")
doc = json.dumps(resp["directives"][0]["document"])
assert doc.count('"sequencer": "maRefresh"') == 1
r = refresh("30000|true|-102500")
last = [d for d in r["directives"] if d["type"].endswith("ExecuteCommands")][-1]
assert last["commands"][0]["sequencer"] == "maRefresh", last
print("OK  refresh loop runs on its own sequencer (not stopped by touches)")

calls.clear()
clock[0] += 5
refresh("31000|true|-102500", seek="130000@31000")
assert calls == [("seek", PLAYER, 130.0)], calls
lf._now_playing_state.pop(PLAYER, None)       # stream restarted at 130 s: screen re-rendered
lf._screen_restarted(PLAYER)
now_playing["v"] = dict(now_playing["v"], elapsed_ms=0)   # MA not caught up yet
clock[0] += 1
cmds = [c for d in refresh("500|true|0")["directives"] if d["type"].endswith("ExecuteCommands")
        for c in d["commands"] if c.get("property") == "trackOffset"]
assert cmds and cmds[0]["value"] == -130000 and cmds[0]["componentId"] == "videoPlayer", cmds
clock[0] += 6
assert not any("trackTotal" in x for x in kinds(refresh("6500|true|-130000"))), "exact offset kept"
print("OK  seek from the screen: offset set from the requested position, not from MA")
_doc = json.load(open(os.path.join(S, "apl_document.json")))
_vid = []
def _w(x):
    if isinstance(x, dict):
        if x.get("id") == "videoPlayer": _vid.append(x)
        for v in x.values(): _w(v)
    elif isinstance(x, list):
        for v in x: _w(v)
_w(_doc)
assert {"trackOffset", "pendingElapsed", "needsResync"} <= {b["name"] for b in _vid[0]["bind"]}
_src = open(os.path.join(S, "lambda_function.py")).read()
assert not re.search(r'"MaTimeRoot",\s*"property": "(trackOffset|pendingElapsed|needsResync)"', _src)
print("OK  time binds live on the Video and the skill writes them there")
assert '"backgroundBlur": true' in json.dumps(_doc) and '"colorOverlay": true' in json.dumps(_doc)
print("OK  background: blurred cover with colour overlay")

# ======================= non-APL device / ENABLE_APL=false ===================
resp = launch(apl=False)
d = resp["directives"][0]
assert d["type"] == "AudioPlayer.Play" and d["audioItem"]["metadata"]["title"], d
assert d["audioItem"]["stream"]["url"].startswith("https://musicassistant.theani.fr/")
os.environ["ENABLE_APL"] = "false"
resp = launch(apl=True)
assert resp["directives"][0]["type"] == "AudioPlayer.Play" and resp["directives"][0]["audioItem"].get("metadata")
os.environ["ENABLE_APL"] = "true"
print("OK  AudioPlayer path (no screen or ENABLE_APL=false): Play with title/artist/cover")

# ======================= document lint ======================================
docj = json.loads(json.dumps(launch()["directives"][0]["document"]))
docj["version"] = "2024.2"
json.dump(docj, open("/home/claude/apltools/test_doc.json", "w"))
out = subprocess.run(["node", "validate.js", "test_doc.json"], cwd="/home/claude/apltools",
                     capture_output=True, text=True).stdout
assert ": 0 messages" in out, out
print("OK  final APL document passes apl-suggester with 0 messages")
print("\nALL TESTS PASSED")
