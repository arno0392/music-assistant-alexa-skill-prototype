"""HTTP integration test against the real running skill app (patched).

MA side: real HTTP calls with basic auth, exactly as MA 2.10 / 2.11 send them.
Echo side: the app's own /simulator/send with full request envelopes.
"""
import json
import sys
import time

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5055"
AUTH = ("u", "p")
PLAYER = "Echo de la Cuisine"
PAYLOAD = json.load(open("/tmp/payload.json"))
APL_IF = {"AudioPlayer": {}, "Alexa.Presentation.APL": {"runtime": {"maxVersion": "2023.3"}}}


def env(request, new=False):
    ev = json.loads(json.dumps(PAYLOAD))
    ev["session"]["new"] = new
    ev["context"]["System"]["device"]["supportedInterfaces"] = APL_IF
    ev["request"] = {"requestId": "r", "locale": "fr-FR", "timestamp": "2026-11-27T20:00:00Z", **request}
    return ev


def echo(request, new=False):
    r = requests.post(f"{BASE}/simulator/send", auth=AUTH, timeout=30,
                      json={"intent": "x", "override_payload": env(request, new)})
    d = r.json()
    assert d["status_code"] == 200, d
    return json.loads(d["body"])["response"]


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


def refresh(report="1000|true", seek=""):
    return echo({"type": "Alexa.Presentation.APL.UserEvent", "source": {},
                 "arguments": ["MetadataRefresh", "", "", ""],
                 "components": {"maReport": report, "maSeek": seek}})


def ma_push(url, **kw):
    r = requests.post(f"{BASE}/ma/push-url", auth=AUTH, timeout=10,
                      json={"streamUrl": url, "title": "T", "artist": "A", "album": "B",
                            "imageUrl": "http://192.168.1.30:8097/imageproxy/x", **kw})
    assert r.status_code == 200, r.text
    return json.loads(r.text)   # MA parses the text body


def ma_control(cmd, player=PLAYER):
    r = requests.post(f"{BASE}/ma/control", auth=AUTH, timeout=5,
                      json={"playerId": player, "command": cmd, "canSkipSpeech": True})
    return r.status_code, json.loads(r.text)


def playback_state():
    r = requests.get(f"{BASE}/alexa/playback-state", params={"player_id": PLAYER}, auth=AUTH, timeout=5)
    r.raise_for_status()
    return r.json()


H = "http://192.168.1.30:8097/flow/"
assert requests.post(f"{BASE}/ma/push-url", json={"streamUrl": "x"}).status_code == 401
print("OK  MA API requires basic auth")

# MA 2.10 then launch
assert "pageLive" not in ma_push(H + "s1/Echo de la Cuisine/i1/Echo de la Cuisine.flac")
resp = echo({"type": "LaunchRequest"})
assert kinds(resp) == ["RenderDocument"], kinds(resp)
assert "s1/Echo%20de%20la%20Cuisine/i1/Echo%20de%20la%20Cuisine.mp3" in json.dumps(resp)
print("OK  launch through the real app: APL with encoded mp3 URL")

resp = refresh("2500|true")
assert not any("SendEvent" in x for x in kinds(resp)), kinds(resp)
st = playback_state()
assert st["current"] is True and st["activity"] == "PLAYING" and st["offsetMs"] == 2500, st
print("OK  refresh -> /alexa/playback-state PLAYING 2500 ms (shared state across the real app)")

# MA 2.11: new stream while the screen is open
r = ma_push(H + "s2/Echo de la Cuisine/i2/Echo de la Cuisine.flac", playerId=PLAYER, canSkipSpeech=True)
assert r.get("pageLive") is True, r
assert playback_state()["current"] is False
resp = refresh()
assert kinds(resp) == ["RenderDocument"] and "s2/Echo%20de%20la%20Cuisine" in json.dumps(resp), kinds(resp)
refresh("300|true")
assert playback_state()["current"] is True
print("OK  2.11 push with open screen: pageLive, screen re-rendered with s2, report current again")

code, r = ma_control("pause")
assert code == 200 and r == {"pageLive": True}, r
assert kinds(refresh())[0] == "ExecuteCommands[pause]"
refresh("900|false")
assert playback_state()["activity"] == "PAUSED"
code, r = ma_control("resume")
assert kinds(refresh("900|false"))[0] == "ExecuteCommands[play]"
assert ma_control("louder")[0] == 400
print("OK  2.11 /ma/control pause/resume through the real app")

# pause by voice / text command (MA 2.10) in a new session: paused screen, no autoplay
resp = echo({"type": "IntentRequest", "intent": {"name": "AMAZON.PauseIntent", "confirmationStatus": "NONE"}}, new=True)
import re
assert kinds(resp) == ["RenderDocument"] and re.findall(r'"autoplay": (\w+)', json.dumps(resp)) == ["false", "false"]
print("OK  PauseIntent new session: paused screen (Video + controls autoplay off)")

# screen closed -> MA must fall back to voice
print("    waiting 7 s for the screen to be considered closed...")
time.sleep(7)
r = ma_push(H + "s3/Echo de la Cuisine/i3/Echo de la Cuisine.flac", playerId=PLAYER, canSkipSpeech=True)
assert r.get("pageLive") is False, r
assert ma_control("pause") == (200, {"pageLive": False})
print("OK  screen closed: pageLive false")

for path in ("/status", "/devices", "/ma/latest-url", "/alexa/latest-url"):
    assert requests.get(BASE + path, auth=AUTH, timeout=10).status_code == 200, path
print("OK  /status, /devices, /ma/latest-url, /alexa/latest-url still answer 200")
print("\nHTTP INTEGRATION: ALL PASSED")
