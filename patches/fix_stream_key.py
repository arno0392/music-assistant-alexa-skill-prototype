"""PATCH: compare stream URLs by identity, not by spelling.

After a launch the skill republishes the stream URL itself (/alexa/push-url)
rewritten: MA_HOSTNAME, .flac -> .mp3, sometimes percent-encoded. Comparing raw
strings then said "not the current stream", so /alexa/playback-state answered
current=false and MA 2.11 ignored every position report; a re-push of the same
stream could also re-render the screen.

Streams are now compared on their flow path without host, encoding or extension.
Also: before re-rendering the screen for a new stream, refresh the metadata
cache from the store, otherwise the skill republishes the previous title.

Requires fix_live_page.py first.
usage: python3 fix_stream_key.py SRC_DIR
"""
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
        assert src.count(old) == 1, f"{label}: code inattendu, patch non applique ({old[:60]!r})"
        src = src.replace(old, new, 1)
    if append:
        src = src.rstrip("\n") + "\n" + append
    open(path, "w", encoding="utf-8").write(src)
    print(f"{label}: patch applique")


patch_text(P("shared_store.py"), "shared_store (cle flux)", "def stream_key", [], append='''

def stream_key(url):
    """PATCH: identity of a stream URL: its path, decoded, without the extension."""
    if not url:
        return None
    from urllib.parse import urlparse, unquote
    path = unquote(urlparse(str(url)).path or "")
    head, dot, ext = path.rpartition(".")
    return head if dot and "/" not in ext else path
''')

patch_text(P("music_assistant_api", "ma_routes.py"), "ma_routes (cle flux)", "stream_key(", [(
    "            if live and stream_url != shared_store._rendered_stream.get(player_id):",
    "            if live and shared_store.stream_key(stream_url) != shared_store.stream_key(\n"
    "                    shared_store._rendered_stream.get(player_id)):",
)])

patch_text(P("alexa_api", "alexa_routes.py"), "alexa_routes (cle flux)", "stream_key(", [(
    "            'current': bool(latest) and report.get('streamUrl') == latest,",
    "            'current': bool(latest) and shared_store.stream_key(report.get('streamUrl'))\n"
    "                       == shared_store.stream_key(latest),",
)])

patch_text(P("skill", "lambda_function.py"), "lambda_function (cache)", "# PATCH: fresh metadata cache", [(
    "        util.play(url=url, offset=0, text=None, response_builder=rb, supports_apl=True)",
    "        # PATCH: fresh metadata cache before util.play republishes it\n"
    "        try:\n"
    "            data.get_latest()\n"
    "        except Exception:\n"
    "            logger.exception(\"Failed to refresh metadata before re-render\")\n"
    "        util.play(url=url, offset=0, text=None, response_builder=rb, supports_apl=True)",
)])
