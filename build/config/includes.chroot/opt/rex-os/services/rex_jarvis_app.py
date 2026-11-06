#!/usr/bin/env python3
"""Local-only REX holographic assistant web app backed by the OS OpenRouter keyring."""
import argparse, asyncio, json, mimetypes, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "vendor" / "jarvis-ui"
sys.path.insert(0, str(ROOT))
from ais.ai_providers import OpenRouterProvider

HOST, PORT = "127.0.0.1", 8764
ORIGIN = f"http://{HOST}:{PORT}"
SYSTEM_PROMPT = ("You are REX, the helpful AI assistant built into REX OS. Be accurate, concise, friendly, and practical. "
                 "Never claim to have performed an action on the computer. You have no shell, filesystem, browser, camera, "
                 "or device-control tools in this interface.")

def generate(prompt):
    async def call():
        provider = OpenRouterProvider()
        try:
            if not await provider.check_availability():
                raise RuntimeError("OpenRouter is not configured. Open REX AI Settings first.")
            return await provider.generate(prompt, max_tokens=1200)
        finally:
            provider.shutdown()
    return asyncio.run(call())

class Handler(BaseHTTPRequestHandler):
    server_version = "REXLocal/1.0"
    def log_message(self, *_args): pass
    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            provider = OpenRouterProvider()
            configured = bool(asyncio.run(provider.check_availability())); provider.shutdown()
            return self.send_json(200,{"ok":True,"provider":"OpenRouter","configured":configured})
        if path.startswith("/api/"): return self.send_json(404,{"error":"Not found"})
        target = (STATIC_ROOT / (unquote(path.lstrip("/")) or "index.html")).resolve()
        if not target.is_relative_to(STATIC_ROOT.resolve()) or not target.is_file():
            return self.send_json(404,{"error":"REX interface is not installed. Rebuild the REX interface."})
        body=target.read_bytes(); self.send_response(200)
        self.send_header("Content-Type",mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length",str(len(body))); self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path != "/api/chat": return self.send_json(404,{"error":"Not found"})
        if self.headers.get("Host") != f"{HOST}:{PORT}" or self.headers.get("Origin") != ORIGIN:
            return self.send_json(403,{"error":"Request origin rejected"})
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size < 2 or size > 32768: raise ValueError("Request size is invalid")
            data=json.loads(self.rfile.read(size)); prompt=data.get("prompt"); history=data.get("history",[])
            if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>6000: raise ValueError("Message must contain 1–6000 characters")
            if not isinstance(history,list) or len(history)>16: raise ValueError("Conversation history is invalid")
            turns=[]
            for item in history:
                if not isinstance(item,dict) or item.get("role") not in ("user","assistant"): raise ValueError("Conversation history is invalid")
                content=item.get("content")
                if not isinstance(content,str) or len(content)>4000: raise ValueError("Conversation history is invalid")
                turns.append(f"{item['role'].upper()}: {content}")
            transcript="\n".join(turns)
            full=SYSTEM_PROMPT+"\n\n"+(transcript+"\n" if transcript else "")+"USER: "+prompt.strip()
            if len(full)>24000: raise ValueError("Conversation is too long. Start a new conversation.")
            self.send_json(200,{"text":generate(full)})
        except ValueError as exc: self.send_json(400,{"error":str(exc)})
        except Exception: self.send_json(502,{"error":"REX could not reach OpenRouter. Check the key and network connection in REX AI Settings."})

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--launch",action="store_true")
    args=parser.parse_args(); server=ThreadingHTTPServer((HOST,PORT),Handler); server.daemon_threads=True
    if args.launch: threading.Timer(1.0,lambda:webbrowser.open(ORIGIN)).start()
    print(f"REX assistant listening on {ORIGIN}",flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=="__main__": main()
