"""PATCH: serve the Video's second source (ma-voice-next.mp3) for real, without auth.

The page's Video lists a second, dummy source: the Echo jumps to it on "Alexa, next".
That URL had no route, so the app's basic auth answered 401 with a password challenge:
an Echo Show ignores it, but a TV's player preloads the source and opens a login box
over the page (which also takes the remote's focus). It is now a short silent MP3,
reachable without credentials (it holds nothing but silence).

usage: python3 fix_voice_next_file.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "app.py")
src = open(path, encoding="utf-8").read()
if "_VOICE_NEXT_MP3" in src:
    print("app (piste voix silencieuse): deja patche")
    sys.exit(0)

old = """    if request.path == '/' and request.method == 'POST':
        return None
    # Read credentials from secrets (APP_USERNAME/APP_PASSWORD)"""
assert src.count(old) == 1, "app.py: auth hook not found"
src = src.replace(old, """    if request.path == '/' and request.method == 'POST':
        return None
    if request.path == '/ma-voice-next.mp3' and request.method in ('GET', 'HEAD'):
        return None
    # Read credentials from secrets (APP_USERNAME/APP_PASSWORD)""")

route = '''# One second of silence (MPEG-1 Layer III, 128 kb/s, 44.1 kHz, zeroed frames).
_VOICE_NEXT_MP3 = (bytes.fromhex("fffb9064") + bytes(413)) * 38


@app.route('/ma-voice-next.mp3', methods=['GET'])
def _voice_next_audio():
    """Second source of the screen's Video, reached when the Echo skips ("Alexa, next")."""
    resp = Response(_VOICE_NEXT_MP3, mimetype='audio/mpeg')
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


'''
anchor = 'if __name__ == "__main__":'
src = src.replace(anchor, route + anchor, 1) if anchor in src else src.rstrip("\n") + "\n\n\n" + route
open(path, "w", encoding="utf-8").write(src)
print("app (piste voix silencieuse): patch applique")
