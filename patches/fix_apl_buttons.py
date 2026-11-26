"""PATCH: route the APL next/previous buttons to Music Assistant.

usage: python3 fix_apl_buttons.py apl_document.json lambda_function.py
"""
import json, sys

doc_path, lambda_path = sys.argv[1], sys.argv[2]

# ---------- 1. APL document ----------
doc = json.load(open(doc_path, encoding="utf-8"))
raw = json.dumps(doc)
if "MaSkipButtons" in raw:
    print("apl_document: deja patche")
else:
    doc.setdefault("graphics", {})
    for name, path in (("maSkipPrevious", "M6 6h2v12H6zm3.5 6l8.5 6V6z"),
                       ("maSkipNext", "M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z")):
        doc["graphics"][name] = {
            "type": "AVG", "version": "1.2", "width": 24, "height": 24,
            "items": [{"type": "path", "pathData": path, "fill": "white"}],
        }

    def skip_button(event, graphic):
        return {
            "type": "TouchWrapper",
            "width": "@secondaryControlSize", "height": "@secondaryControlSize",
            "onPress": [{"type": "SendEvent", "arguments": [event]}],
            "item": {"type": "VectorGraphic", "source": graphic,
                     "width": "100%", "height": "100%", "scale": "best-fit"},
        }

    found = []
    def walk(node):
        if isinstance(node, dict):
            for key in ("item", "items"):
                val = node.get(key)
                if isinstance(val, list):
                    for i, child in enumerate(val):
                        if isinstance(child, dict) and child.get("type") == "AlexaTransportControls":
                            child["secondaryControls"] = "none"
                            val[i] = {
                                "type": "Container", "id": "MaSkipButtons",
                                "direction": "row", "alignItems": "center",
                                "justifyContent": "center",
                                "items": [skip_button("Previous", "maSkipPrevious"),
                                          child,
                                          skip_button("Next", "maSkipNext")],
                            }
                            found.append(child)
                        else:
                            walk(child)
                elif isinstance(val, dict):
                    walk(val)
            for k, v in node.items():
                if k not in ("item", "items"):
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(doc)
    assert len(found) == 1, "AlexaTransportControls introuvable, patch non applique"
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document: patch applique")

# ---------- 2. skill handler ----------
src = open(lambda_path, encoding="utf-8").read()
if "class APLSkipEventHandler" in src:
    print("lambda_function: deja patche")
else:
    handler = '''

class APLSkipEventHandler(AbstractRequestHandler):
    """PATCH: Next/Previous buttons of the APL screen -> Music Assistant.

    The stock AlexaTransportControls skip buttons act on the hidden Video
    component, which only holds the current flow stream, so they just restart
    it. The patched APL document sends UserEvent ["Next"] / ["Previous"].
    """
    def can_handle(self, handler_input):
        if not is_request_type("Alexa.Presentation.APL.UserEvent")(handler_input):
            return False
        args = getattr(handler_input.request_envelope.request, 'arguments', None) or []
        return bool(args) and args[0] in ("Next", "Previous")

    def handle(self, handler_input):
        args = handler_input.request_envelope.request.arguments
        command = "next" if args[0] == "Next" else "previous"
        device_id = _device_id_from(handler_input)
        player_id = device_mapping.get_player_for_device(device_id)
        logger.info("In APLSkipEventHandler: %s (player=%s)", command, player_id)
        if player_id:
            ma_control.send_player_command(player_id, command)
        else:
            logger.warning("No MA player mapped for device_id=%s (APL %s)", device_id, command)
        return handler_input.response_builder.set_should_end_session(None).response

'''
    anchor = "\nclass APLUserEventHandler(AbstractRequestHandler):"
    reg = "sb.add_request_handler(APLUserEventHandler())"
    assert src.count(anchor) == 1 and src.count(reg) == 1, "code inattendu, patch non applique"
    src = src.replace(anchor, handler + anchor, 1)
    src = src.replace(reg, "sb.add_request_handler(APLSkipEventHandler())\n" + reg, 1)
    open(lambda_path, "w", encoding="utf-8").write(src)
    print("lambda_function: patch applique")
