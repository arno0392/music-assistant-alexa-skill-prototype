"""PATCH: custom intents for more "next"/"previous" phrasings.

AMAZON.NextIntent / AMAZON.PreviousIntent cannot be extended with sample
utterances. Phrasings like "chanson précédente" can be put in two custom
intents, MaNextIntent and MaPreviousIntent (added in the developer console),
handled exactly like the built-in ones.

usage: python3 fix_custom_skip_intents.py SRC_DIR
"""
import os
import sys

path = os.path.join(sys.argv[1], "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "MaPreviousIntent" in src:
    print("lambda_function (intents perso): deja patche")
    sys.exit(0)
edits = [
    ('''        return (is_intent_name("AMAZON.NextIntent")(handler_input) or
                is_intent_name("AMAZON.PreviousIntent")(handler_input))''',
     '''        return (is_intent_name("AMAZON.NextIntent")(handler_input) or
                is_intent_name("AMAZON.PreviousIntent")(handler_input) or
                is_intent_name("MaNextIntent")(handler_input) or
                is_intent_name("MaPreviousIntent")(handler_input))'''),
    ('''        command = "next" if intent_name == "AMAZON.NextIntent" else "previous"''',
     '''        command = "next" if intent_name in ("AMAZON.NextIntent", "MaNextIntent") else "previous"'''),
]
for old, new in edits:
    assert src.count(old) == 1, f"lambda_function (intents perso): code inattendu ({old[:50]!r})"
    src = src.replace(old, new)
open(path, "w", encoding="utf-8").write(src)
print("lambda_function (intents perso): patch applique")
