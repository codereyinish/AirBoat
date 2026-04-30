import json
import socket
import threading
from mitmproxy import ctx, http


SOCKET_PATH = "/tmp/airboat.sock"
#/tmp is the temporary files on the mac which gets deleted on the reboot and .sock is the file extension, we cant open it like usual file in text editor

class AirboatAddon:
    def __init__(self):
        self._lock = threading.Lock()
        self._convo_id = "PASTE_YOUR_CONVO_ID_HERE"



    def responseheaders(self, flow:http.HTTPFlow) -> None:
        if "claude.ai" not in flow.request.pretty_host:
            return
        if self._convo_id not in flow.request.path:
            return
        if "text/event-stream" not in flow.response.headers.get("content-type", ""):
            return
        flow.response.stream = self._make_stream_handler()


    def _make_stream_handler(self):
        addon = self

        def handler(chunks):
            buf = ""
            for chunk in chunks:
                buf+= chunk.decode("utf-8", errors = "replace") #OS convets packets into bytes, we decode the bytes into text
                while "\n\n" in buf:
                    event_text , buf = buf.split("\n\n", 1)
                    addon._process_event(event_text)
                yield chunk

        return handler


    def _process_event(self, event_txt:str) -> None:
        for line in event_txt.strip().splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                self._send("__STOP__")
                return
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            
            t = obj.get("type")
            if t == "content_block_delta":
                delta = obj.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        self._send(text)
            elif  t == "message_stop":
                self._send("__STOP__")

    def _send(self, text:str) -> None:
        try:
            with self._lock:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.connect(SOCKET_PATH)
                    s.sendall((text + "\x00").encode("utf-8"))
        except(ConnectionRefusedError, FileNotFoundError):
            ctx.log.warn("airboat: window.py not listening")
            
        except Exception as e:
            ctx.log.error(f"airboat: send error: {e}")

addons = [AirboatAddon()]


