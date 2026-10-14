"""Real desktop companion and shared idle game smoke test, temporary save only."""
import sys,tempfile,time
from datetime import datetime,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from salary_web import SalaryAPI

def main():
 import webview
 errors=[]
 with tempfile.TemporaryDirectory() as directory:
  api=SalaryAPI(Path(directory)/'state.json')
  api._window=webview.create_window('WESI pet validation',str(Path(__file__).resolve().parents[1]/'ui/pet.html'),js_api=api,width=1040,height=760)
  api._window.events.closed+=api.close_desktop_pet
  def wait(condition):
   deadline=time.monotonic()+15
   while time.monotonic()<deadline:
    if condition():return
    time.sleep(.1)
   raise AssertionError('Native companion condition failed')
  def check():
   try:
    window=api._window
    wait(lambda:window.evaluate_js("document.getElementById('notice')?.textContent==='伙伴已就绪。'"))
    window.evaluate_js("document.getElementById('desktop').click()")
    wait(lambda:api._pet_window is not None)
    companion=api._pet_window
    wait(lambda:companion.evaluate_js("document.getElementById('sprite')?.complete && document.getElementById('sprite')?.naturalWidth>0"))
    assert companion.on_top
    api.open_desktop_pet();assert api._pet_window is companion
    companion.evaluate_js("document.getElementById('collision').click()")
    wait(lambda:companion.evaluate_js("document.getElementById('speech').textContent.includes('探险')"))
    window.evaluate_js("document.querySelector('#routes button').click()")
    wait(lambda:api._store.state['pet_game']['task'] is not None)
    api._pet_game.clock=lambda:datetime.now()+timedelta(minutes=2)
    assert api.pet_snapshot()['game']['xp']==5
    assert api.pet_snapshot()['game']['xp']==5
    companion.evaluate_js("document.getElementById('game-open').click()")
    wait(lambda:window.evaluate_js("document.getElementById('name')?.textContent==='Mochi'"))
    api.close_desktop_pet()
    wait(lambda:api._pet_window is None)
    print('PASS: real upstream sprite, native companion, interaction, singleton, shared save and one-time offline reward')
   except Exception as exc:errors.append(exc)
   finally:api.close_desktop_pet();api._window.destroy()
  webview.start(check,gui='qt',http_server=True)
 if errors:raise errors[0]
if __name__=='__main__':main()
