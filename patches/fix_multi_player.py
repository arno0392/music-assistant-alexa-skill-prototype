"""PATCH: one "now playing" per Music Assistant player (several Echos).

The skill kept a single stream/title for every Echo (shared_store._store):
a track started on another Echo replaced the title, the cover and even the
stream that the open screen used for its next re-render.

shared_store._store now depends on the request: each request is tied to a
player (the Echo's MA player from /devices, or the playerId MA 2.11 sends
with /ma/push-url), and reads/writes that player's own entry. Without a
known player (MA 2.10, unmapped Echo) it falls back to the latest stream, as
before. Nothing else had to change: every reader keeps using _store.

usage: python3 fix_multi_player.py SRC_DIR
"""
import os
import sys

base = sys.argv[1]


def patch_text(path, label, marker, edits, append=None):
    src = open(path, encoding="utf-8").read()
    if marker in src:
        print(f"{label}: deja patche")
        return
    for old, new in edits:
        assert src.count(old) >= 1, f"{label}: code inattendu, patch non applique ({old[:60]!r})"
        src = src.replace(old, new, 1)
    if append:
        src = src.rstrip("\n") + "\n" + append
    open(path, "w", encoding="utf-8").write(src)
    print(f"{label}: patch applique")


# ---------------------------------------------------------------- shared_store.py
patch_text(os.path.join(base, "shared_store.py"), "shared_store (par lecteur)", "class _StoreModule", [], append='''

# One "now playing" per Music Assistant player.
# shared_store._store reads/writes the entry of the player tied to the current
# request (set_request_player), or the latest entry when none is known.
import sys as _sys
import types as _types

_request = _threading.local()
_by_player = {}
_latest = globals().pop("_store", None)


def set_request_player(player_id):
    _request.player = player_id or None


def request_player():
    return getattr(_request, "player", None)


def store_for(player_id):
    with _live_lock:
        if player_id and player_id in _by_player:
            return _by_player[player_id]
        return _latest


class _StoreModule(_types.ModuleType):
    @property
    def _store(self):
        return store_for(request_player())

    @_store.setter
    def _store(self, value):
        global _latest
        player = request_player()
        with _live_lock:
            if player:
                _by_player[player] = value
            _latest = value


_sys.modules[__name__].__class__ = _StoreModule
''')

# ---------------------------------------------------------------- ma_routes.py (MA pushes)
patch_text(os.path.join(base, "music_assistant_api", "ma_routes.py"), "ma_routes (par lecteur)", "set_request_player", [
    ("def register_routes(bp):\n",
     "def register_routes(bp):\n"
     "    # each HTTP request starts without a player (threads are reused)\n"
     "    bp.before_request(lambda: shared_store.set_request_player(None))\n\n"),
    ("""        data = request.get_json(silent=True) or {}
        stream_url = data.get('streamUrl')
""", """        data = request.get_json(silent=True) or {}
        shared_store.set_request_player(data.get('playerId'))   # MA 2.11
        stream_url = data.get('streamUrl')
"""),
])

# ---------------------------------------------------------------- alexa_routes.py
patch_text(os.path.join(base, "alexa_api", "alexa_routes.py"), "alexa_routes (par lecteur)", "set_request_player", [
    ("def register_routes(bp):\n",
     "def register_routes(bp):\n"
     "    bp.before_request(lambda: shared_store.set_request_player(None))\n\n"),
    ("""        data = request.get_json(silent=True) or {}
        stream_url = data.get('streamUrl')
""", """        data = request.get_json(silent=True) or {}
        shared_store.set_request_player(data.get('playerId'))
        stream_url = data.get('streamUrl')
"""),
    ("""        player_id = request.args.get('player_id')
""", """        player_id = request.args.get('player_id')
        shared_store.set_request_player(player_id)
"""),
])

# ---------------------------------------------------------------- util.py (skill republishes its stream)
patch_text(os.path.join(base, "skill", "util.py"), "util (par lecteur)", "'playerId': _request_player()", [(
    """        'imageUrl': data.info.get("coverImageSource")
    }""",
    """        'imageUrl': data.info.get("coverImageSource"),
        'playerId': _request_player()
    }""")], append='''

def _request_player():
    """MA player of the Echo this request comes from (for the republished stream)."""
    try:
        import shared_store
        return shared_store.request_player()
    except Exception:
        return None
''')

# ---------------------------------------------------------------- lambda_function.py (skill requests)
patch_text(os.path.join(base, "skill", "lambda_function.py"), "lambda_function (par lecteur)", "class PlayerContextInterceptor", [], append='''

class PlayerContextInterceptor(AbstractRequestInterceptor):
    """Ties every skill request to the MA player of its Echo (see shared_store._store)."""
    def process(self, handler_input):
        try:
            import shared_store
            shared_store.set_request_player(device_mapping.get_player_for_device(_device_id_from(handler_input)))
        except Exception:
            logger.debug("Could not set the request player", exc_info=True)


sb.add_global_request_interceptor(PlayerContextInterceptor())
''')
