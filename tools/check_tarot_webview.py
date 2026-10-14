"""Real desktop bridge test with temporary history and a local simulated AI."""
import json
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salary_web import SalaryAPI
from tarot_service import TarotService


def main():
    import webview
    errors = []
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            report={'overview':'本机模拟 AI 整组解读','relations':['仅解释已抽出的十张牌'],'actions':['核实一个具体事实'],'questions':['有哪些条件仍然未知？']}
            body=json.dumps({'choices':[{'message':{'content':json.dumps(report)}}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'WESI_TAROT_AI_BASE':f'http://127.0.0.1:{server.server_port}/v1','WESI_TAROT_AI_MODEL':'local-test','WESI_TAROT_AI_KEY':''}):
            api = SalaryAPI(Path(directory)/'state.json')
            api._tarot = TarotService(Path(directory)/'tarot.json')
            window = webview.create_window('WESI tarot validation', str(Path(__file__).resolve().parents[1]/'ui/tarot.html'), js_api=api, width=1280, height=900)
            def wait(expression):
                deadline = time.monotonic()+15
                while time.monotonic()<deadline:
                    if window.evaluate_js(expression): return
                    time.sleep(.1)
                raise AssertionError(expression)
            def check():
                try:
                    wait("document.getElementById('spread').options.length === 8")
                    window.evaluate_js("document.getElementById('spread').value='celtic'; document.getElementById('draw-form').requestSubmit()")
                    wait("document.querySelectorAll('.tarot-card').length === 10")
                    window.evaluate_js("document.getElementById('reveal-all').click()")
                    wait("document.querySelectorAll('.revealed').length === 10 && document.querySelectorAll('.card-front img').length === 10")
                    wait("document.getElementById('offline-reading').textContent.includes('牌间关系')")
                    cards=api._tarot.history()[0]['cards']
                    window.evaluate_js("window.confirm=()=>true; document.getElementById('ai-generate').click()")
                    wait("document.getElementById('ai-reading').textContent.includes('本机模拟 AI')")
                    assert api._tarot.history()[0]['cards'] == cards
                    assert len(requests) == 1
                    window.evaluate_js("document.getElementById('history-open').click()")
                    wait("document.querySelector('#history-list button') !== null")
                    window.evaluate_js("document.querySelector('#history-list button').click()")
                    wait("document.getElementById('notice').textContent.includes('未重新抽牌')")
                    assert len(api._tarot.history()) == 1 and len(requests) == 1
                    window.evaluate_js("window.location.href='index.html'")
                    wait("document.getElementById('amount')?.value !== undefined")
                    window.evaluate_js("document.querySelector('a[href=\"tarot.html\"]').click()")
                    wait("document.getElementById('spread')?.options.length === 8")
                    print('PASS: native tarot, offline synthesis, local AI HTTP, unchanged cards, saved history and page switching')
                except Exception as exc: errors.append(exc)
                finally: window.destroy()
            webview.start(check, gui='qt', http_server=True)
    finally:
        server.shutdown();server.server_close()
    if errors: raise errors[0]
if __name__ == '__main__': main()
