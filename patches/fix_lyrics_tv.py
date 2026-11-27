"""PATCH: lyrics on a TV, and lyrics kept open after "next".

- Lines are lit LYRICS_LEAD_MS (400) early to make up for an Echo's decoding delay;
  a TV plays the stream without it, so its lines came slightly early. A TV now uses
  LYRICS_LEAD_MS_TV (default 0).
- The open/closed state of the lyrics panel is taken from the screen only once the
  lyrics were shown on it: a new screen (next track, seek) first reports a closed
  panel while its lyrics are still loading, which forgot that the panel was open.

usage: python3 fix_lyrics_tv.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "LYRICS_LEAD_MS_TV" in src:
    print("lambda_function (paroles TV): deja patche")
    sys.exit(0)

edits = [
    ('''            if len(parts) > 4 and parts[4].strip() in ('0', '1'):
                _lyrics_open[player_id] = parts[4].strip() == '1\'''',
     '''            _shown_lyrics = _lyrics_state.get(player_id) or {}
            if (len(parts) > 4 and parts[4].strip() in ('0', '1')
                    and _shown_lyrics.get("sent") and _shown_lyrics.get("lines")):
                _lyrics_open[player_id] = parts[4].strip() == '1\''''),
    ('''def _parse_lyrics(lyrics, lrc):''', '''def _parse_lyrics(lyrics, lrc, lead=None):'''),
    ('''            try:
                lead = int(os.environ.get("LYRICS_LEAD_MS", "400"))
            except ValueError:
                lead = 400''', '''            if lead is None:
                try:
                    lead = int(os.environ.get("LYRICS_LEAD_MS", "400"))
                except ValueError:
                    lead = 400'''),
    ('''            st["lines"], st["synced"] = _parse_lyrics(found.get("lyrics"), found.get("lrc"))''',
     '''            st["lines"], st["synced"] = _parse_lyrics(found.get("lyrics"), found.get("lrc"),
                                                      lead=_lyrics_lead(player_id))'''),
]
for old, new in edits:
    assert src.count(old) == 1, old[:60]
    src = src.replace(old, new)

src = src.rstrip("\n") + '''


_player_on_tv = {}      # player_id -> its screen is a TV


def _lyrics_lead(player_id):
    """How early the lines are lit, in ms (None: the default for an Echo)."""
    if not _player_on_tv.get(player_id):
        return None
    try:
        return int(os.environ.get("LYRICS_LEAD_MS_TV", "0"))
    except ValueError:
        return 0


class ScreenModeInterceptor(AbstractRequestInterceptor):
    """Remember which players show the page on a TV."""
    def process(self, handler_input):
        try:
            viewport = getattr(handler_input.request_envelope.context, 'viewport', None)
            mode = getattr(viewport, 'mode', None)
            if mode is None:
                return
            player_id = device_mapping.get_player_for_device(_device_id_from(handler_input))
            if player_id:
                _player_on_tv[player_id] = str(getattr(mode, 'value', mode)).upper() == "TV"
        except Exception:
            pass


sb.add_global_request_interceptor(ScreenModeInterceptor())
'''
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (paroles TV): patch applique")
