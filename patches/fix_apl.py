import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "audio_src" in s:
    print("deja patche"); sys.exit(0)
old1 = '''    if hostname:
        cover_image = replace_ip_in_url(cover_image, hostname)
        background_image = replace_ip_in_url(background_image, hostname)

    # Load the APL document template'''
new1 = '''    if hostname:
        cover_image = replace_ip_in_url(cover_image, hostname)
        background_image = replace_ip_in_url(background_image, hostname)

    # PATCH: encode the audio URL like the AudioPlayer path does (spaces -> %20, flac -> mp3)
    import re as _re
    from urllib.parse import quote as _quote
    audio_src = metadata.get("audioSources", "") or ""
    audio_src = _re.sub(r'(?i)\\.flac(?=$|\\?)', '.mp3', audio_src)
    audio_src = replace_ip_in_url(audio_src, hostname) if hostname else _quote(audio_src, safe=':/%?=&')

    # Load the APL document template'''
old2 = '"audioSources": metadata.get("audioSources", ""),'
new2 = '"audioSources": audio_src,'
assert s.count(old1) == 1 and s.count(old2) == 1, "code inattendu, patch non applique"
s = s.replace(old1, new1).replace(old2, new2)
open(p, "w", encoding="utf-8").write(s)
print("patch applique")
