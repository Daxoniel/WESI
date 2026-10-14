import {test, expect} from '@playwright/test';
const entry = {id:'demo', time:'2026-10-14 12:00:00', question:'我的问题 <script>', spread:'guidance', spread_label:'现状与建议', layout:{coordinates:[[0,0],[1,0],[2,0]]}, cards:[0,1,2].map((i)=>({name_zh:['愚者','魔术师','女祭司'][i],name_en:'Card',position:['现状','阻碍','建议'][i],reversed:i===1,img:'m00.jpg',desc:'核心',reading:{core:i===1?'逆位独立牌义':'正位独立牌义',position:'牌位视角',action:'具体行动',reflection:'反思问题'}}))};
entry.synthesis={overview:'离线整组总览',themes:['花色主题'],relations:['现状与阻碍对照'],actions:['先核实事实'],questions:['有哪些支持证据？'],method:'离线规则'};
test.beforeEach(async ({page})=>{
 await page.addInitScript(entry=>{
  window.saved=[];
  window.pywebview={api:{
   tarot_catalog:async()=>({deck_size:78,ai:{available:!!window.aiAvailable,model:'test'},spreads:{guidance:{label:'现状与建议',description:'行动梳理',positions:['现状','阻碍','建议']}}}),
   tarot_draw:async()=>{if(window.failDraw)return {ok:false,error:'历史保存失败'};window.saved.push(entry);return {ok:true,entry};},
   tarot_ai_reading:async()=>{
     window.aiRequests=(window.aiRequests||0)+1;
     if(window.failAI)return {ok:false,error:'AI 请求失败'};
     const report={overview:'结合问题的深入解读',relations:['相互呼应'],actions:['执行步骤'],questions:['需要核实'],model:'test'};
     window.saved[0]={...window.saved[0],ai_reading:report};
     return {ok:true,entry:window.saved[0]};
   },
   tarot_history:async()=>window.saved,
   tarot_image:async()=>null,
  }};
 },entry);
 await page.goto('/tarot.html');
 await expect(page.locator('#notice')).toHaveText('本地牌库已就绪。');
});
test('draw, keyboard reveal, position reading and historical restoration', async({page})=>{
 await page.locator('#draw').click();
 await expect(page.locator('.tarot-card')).toHaveCount(3);
 await expect(page.locator('.revealed')).toHaveCount(0);
 await page.locator('.tarot-card').nth(1).focus();
 await page.keyboard.press('Enter');
 await expect(page.locator('#orientation')).toContainText('逆位');
 await expect(page.locator('#card-reading')).toContainText('逆位独立牌义');
 await expect(page.locator('#reading-question')).toContainText('<script>');
 await page.locator('#history-open').click();
 await page.locator('#history-list button').click();
 await expect(page.locator('.revealed')).toHaveCount(3);
 await expect(page.locator('#notice')).toContainText('未重新抽牌');
 expect(await page.evaluate(()=>window.saved.length)).toBe(1);
});
test('save failure keeps current table and responsive page fits',async({page})=>{
 await page.locator('#draw').click();
 await page.evaluate(()=>{window.failDraw=true;});
 await page.locator('#draw').click();
 await expect(page.locator('#notice')).toHaveText('历史保存失败');
 await expect(page.locator('.tarot-card')).toHaveCount(3);
 await page.setViewportSize({width:420,height:760});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('whole reading waits for reveal; optional AI saves without drawing again',async({page})=>{
 await page.addInitScript(()=>{window.aiAvailable=true;});await page.reload();
 await expect(page.locator('#notice')).toHaveText('本地牌库已就绪。');
 await page.locator('#draw').click();
 await expect(page.locator('#whole-reading')).toBeHidden();
 await page.locator('.tarot-card').first().click();
 await expect(page.locator('#whole-reading')).toBeHidden();
 await page.locator('#reveal-all').click();
 await expect(page.locator('#offline-reading')).toContainText('现状与阻碍对照');
 page.once('dialog',dialog=>dialog.accept());await page.locator('#ai-generate').click();
 await expect(page.locator('#ai-reading')).toContainText('结合问题的深入解读');
 await page.locator('#history-open').click();await page.locator('#history-list button').click();
 await expect(page.locator('#ai-reading')).toContainText('结合问题的深入解读');
 expect(await page.evaluate(()=>window.aiRequests)).toBe(1);
 expect(await page.evaluate(()=>window.saved.length)).toBe(1);
});
test('AI failure preserves offline report and allows retry',async({page})=>{
 await page.addInitScript(()=>{window.aiAvailable=true;window.failAI=true;});await page.reload();
 await expect(page.locator('#notice')).toHaveText('本地牌库已就绪。');await page.locator('#draw').click();await page.locator('#reveal-all').click();
 page.once('dialog',dialog=>dialog.accept());await page.locator('#ai-generate').click();
 await expect(page.locator('#notice')).toHaveText('AI 请求失败');
 await expect(page.locator('#offline-reading')).toContainText('离线整组总览');
 await expect(page.locator('#ai-generate')).toBeEnabled();
 await expect(page.locator('.revealed')).toHaveCount(3);
});
