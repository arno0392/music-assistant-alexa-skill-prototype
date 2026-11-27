"""PATCH (temporary diagnostic): see what a TV's Alexa app does with the APL page.

- every remote key that reaches the page is logged ("Remote key: ...") and, when it
  arrives with nothing focused, still drives the player;
- the first request of each device logs its screen mode and APL version.

usage: python3 fix_tv_diag.py SRC_DIR
"""
import json
import os
import sys

base = sys.argv[1]
doc_path = os.path.join(base, "skill", "apl_document.json")
doc = json.load(open(doc_path, encoding="utf-8"))


def find(node, cid):
    if isinstance(node, dict):
        if node.get("id") == cid:
            return node
        node = list(node.values())
    if isinstance(node, list):
        for v in node:
            hit = find(v, cid)
            if hit:
                return hit
    return None


diag = {"type": "SendEvent", "arguments": ["KeyDiag", "${event.keyboard.code}", "${event.keyboard.key}"]}
if "handleKeyDown" in doc:
    print("apl_document (diagnostic TV): deja patche")
else:
    button = find(doc["layouts"]["AudioPlayer"]["item"], "maLyricsButton")
    handlers = [dict(h, commands=[diag] + h["commands"]) for h in (button or {}).get("handleKeyDown", [])]
    if button is not None:
        button["handleKeyDown"] = [dict(h) for h in handlers]
    doc["handleKeyDown"] = handlers + [{"commands": [diag]}]
    json.dump(doc, open(doc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("apl_document (diagnostic TV): patch applique")

path = os.path.join(base, "skill", "lambda_function.py")
src = open(path, encoding="utf-8").read()
if "class APLKeyDiagEventHandler" in src:
    print("lambda_function (diagnostic TV): deja patche")
else:
    src = src.rstrip("\n") + '''


class APLKeyDiagEventHandler(AbstractRequestHandler):
    """Diagnostic: a remote key reached the page."""
    def can_handle(self, handler_input):
        if not is_request_type("Alexa.Presentation.APL.UserEvent")(handler_input):
            return False
        args = getattr(handler_input.request_envelope.request, 'arguments', None) or []
        return bool(args) and args[0] == "KeyDiag"

    def handle(self, handler_input):
        args = handler_input.request_envelope.request.arguments
        logger.info("Remote key: code=%s key=%s", *(list(args[1:3]) + [None, None])[:2])
        return handler_input.response_builder.set_should_end_session(None).response


_screen_seen = set()


class ScreenDiagInterceptor(AbstractRequestInterceptor):
    """Diagnostic: log each device's screen mode and APL version once."""
    def process(self, handler_input):
        try:
            ctx = handler_input.request_envelope.context
            dev = ctx.system.device
            if dev.device_id in _screen_seen:
                return
            _screen_seen.add(dev.device_id)
            vp = getattr(ctx, 'viewport', None)
            apl = getattr(getattr(dev, 'supported_interfaces', None), 'alexa_presentation_apl', None)
            logger.info("Screen of %s...: mode=%s shape=%s %sx%s dpi=%s APL=%s", dev.device_id[-8:],
                        getattr(vp, 'mode', None), getattr(vp, 'shape', None),
                        getattr(vp, 'pixel_width', None), getattr(vp, 'pixel_height', None),
                        getattr(vp, 'dpi', None),
                        getattr(getattr(apl, 'runtime', None), 'max_version', None))
        except Exception:  # diagnostic only
            pass


sb.add_request_handler(APLKeyDiagEventHandler())
sb.add_global_request_interceptor(ScreenDiagInterceptor())
'''
    open(path, "w", encoding="utf-8").write(src)
    print("lambda_function (diagnostic TV): patch applique")
