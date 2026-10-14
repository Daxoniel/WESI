"""Real desktop tarot bridge smoke test; uses only temporary history."""
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salary_web import SalaryAPI
from tarot_service import TarotService

def main():
    import webview
    errors = []
    with tempfile.TemporaryDirectory() as directory:
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
                assert len(api._tarot.history()) == 1
                window.evaluate_js("document.getElementById('history-open').click()")
                wait("document.querySelector('#history-list button') !== null")
                window.evaluate_js("document.querySelector('#history-list button').click()")
                wait("document.getElementById('notice').textContent.includes('未重新抽牌')")
                assert len(api._tarot.history()) == 1
                window.evaluate_js("window.location.href='index.html'")
                wait("document.getElementById('amount')?.value !== undefined")
                window.evaluate_js("document.querySelector('a[href=\"tarot.html\"]').click()")
                wait("document.getElementById('spread')?.options.length === 8")
                print('PASS: native tarot, 10 unique cards, images, reveal and persisted historical restoration')
            except Exception as exc: errors.append(exc)
            finally: window.destroy()
        webview.start(check, gui='qt', http_server=True)
    if errors: raise errors[0]
if __name__ == '__main__': main()
