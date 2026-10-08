"""Exercise the real native WebView/JS/Python bridge with temporary state.

Run from the repo: python tools/check_webview.py [--gui qt]
"""
import argparse
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from salary_web import SalaryAPI


def main():
    import webview
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui")
    args = parser.parse_args()
    errors = []
    with tempfile.TemporaryDirectory() as directory:
        api = SalaryAPI(Path(directory)/"state.json", clock=lambda: datetime(2026, 10, 8, 13))
        api._store.state["income"]["employment_start"] = "2026-10-08 09:00:00"
        window = api._window = webview.create_window("WESI bridge validation", str(Path(__file__).resolve().parents[1]/"ui/index.html"), js_api=api, width=1040, height=760)
        def wait_for(expression):
            end = time.monotonic()+15
            while time.monotonic() < end:
                if window.evaluate_js(expression):
                    return
                time.sleep(.1)
            raise AssertionError(f"Native bridge condition not met: {expression}")
        def check():
            try:
                wait_for("document.getElementById('status')?.textContent === '工作中'")
                assert window.evaluate_js("document.getElementById('amount').value") == 60
                window.evaluate_js("document.getElementById('receipt-open').click(); document.getElementById('receipt-form').requestSubmit(document.querySelector('#receipt-form button[type=submit]'))")
                wait_for("document.getElementById('wallet-total').textContent === '€2,600.00'")
                assert api._store.state["payroll"]["receipts"]["2026-10"]["amount_cents"] == 260000
                window.evaluate_js("document.getElementById('privacy').click()")
                wait_for("document.getElementById('amount').hidden")
                window.evaluate_js("document.getElementById('pin').click()")
                wait_for("document.getElementById('pin').getAttribute('aria-pressed') === 'true'")
                assert window.on_top
                window.evaluate_js("document.getElementById('compact').click()")
                wait_for("document.body.classList.contains('compact')")
                assert window.width == 420 and window.height == 440
                print("PASS: native WebView, real Python snapshot, NumberFlow, persisted salary receipt, privacy, native pin and compact resize")
            except Exception as exc:
                errors.append(exc)
            finally:
                window.destroy()
        webview.start(check, gui=args.gui, http_server=True)
    if errors:
        raise errors[0]


if __name__ == "__main__":
    main()
