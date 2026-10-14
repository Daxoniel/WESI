import {test,expect} from '@playwright/test';
test('upstream engine loads and companion game bridges dispatch, feed and desktop',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.addInitScript(()=>{
  const snapshot={ok:true,name:'Mochi',level:1,affinity:0,game:{xp:0,materials:{干粮:3},task:null,log:[]},remaining:0,routes:{park:{name:'公园散步',seconds:60}}};
  window.calls=[];window.pywebview={api:{pet_snapshot:async()=>snapshot,
   pet_dispatch:async route=>{window.calls.push(route);snapshot.game.task={name:'公园散步'};snapshot.remaining=60;return snapshot;},
   pet_interact:async action=>{window.calls.push(action);snapshot.affinity++;return snapshot;},
   open_desktop_pet:async()=>{window.calls.push('desktop');return true;}}};
 });
 await page.goto('/pet.html');await expect(page.locator('#notice')).toHaveText('伙伴已就绪。');
 const frame=page.frameLocator('iframe');
 await expect(frame.locator('#sprite')).toHaveAttribute('src',/yellow_.*gif/);
 await expect(frame.locator('#pet-tools')).toBeHidden();
 await frame.locator('#collision').click();await expect(frame.locator('#speech')).toContainText('探险');
 await page.locator('#feed').click();await expect(page.locator('#stats')).toContainText('亲密度 1');
 await page.locator('#routes button').click();await expect(page.locator('#task')).toContainText('进行中');
 await page.locator('#desktop').click();
 expect(await page.evaluate(()=>window.calls)).toEqual(['feed','park','desktop']);
 expect(errors).toEqual([]);
 await page.setViewportSize({width:420,height:760});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
