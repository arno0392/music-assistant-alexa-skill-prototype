import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "_now_playing_metadata" in s:
    print("deja patche"); sys.exit(0)

helper = '''

def _now_playing_metadata(hostname):
    """PATCH: title/artist/cover for the native Echo Show 'now playing' screen."""
    try:
        import shared_store
        store = shared_store._store or {}
    except Exception:
        store = {}
    title = store.get("title") or ""
    artist = store.get("artist") or ""
    album = store.get("album") or ""
    image = store.get("imageUrl") or ""
    if not (title or artist or image):
        return None
    subtitle = store.get("secondary") or " - ".join(x for x in (artist, album) if x)
    art = None
    if image:
        image = replace_ip_in_url(image, hostname) if hostname else image
        art = display.Image(sources=[display.ImageInstance(url=image)])
    return AudioItemMetadata(title=title[:150] or None, subtitle=subtitle[:150] or None,
                             art=art, background_image=art)


def play(url, offset, text, response_builder, supports_apl=False):'''
old_def = '\n\ndef play(url, offset, text, response_builder, supports_apl=False):'
assert s.count(old_def) == 1, "def play introuvable"
s = s.replace(old_def, helper, 1)

old_a = '''                        offset_in_milliseconds=offset,
                        expected_previous_token=None
                    )
                )'''
new_a = '''                        offset_in_milliseconds=offset,
                        expected_previous_token=None
                    ),
                    metadata=_now_playing_metadata(hostname)
                )'''
old_b = '''                    offset_in_milliseconds=0,
                    expected_previous_token=expected_previous_token
                )
            )'''
new_b = '''                    offset_in_milliseconds=0,
                    expected_previous_token=expected_previous_token
                ),
                metadata=_now_playing_metadata(hostname)
            )'''
assert s.count(old_a) == 1 and s.count(old_b) == 1, "code inattendu, patch non applique"
s = s.replace(old_a, new_a).replace(old_b, new_b)
open(p, "w", encoding="utf-8").write(s)
print("patch applique")
