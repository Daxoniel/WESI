const $=id=>document.getElementById(id);
const api=()=>window.pywebview?.api;
let busy=false,connected=false,timer=null,generation=0;
function notice(message){$('notice').textContent=message;}
function render(data){
 $('name').textContent=data.name;
 $('stats').textContent=`等级 ${data.level} · 经验 ${data.game.xp} · 亲密度 ${data.affinity}`;
 $('task').textContent=data.game.task?`${data.game.task.name}进行中 · 还有 ${Math.floor(data.remaining/60)} 分 ${data.remaining%60} 秒`:'伙伴正在休息，可以开始下一次冒险。';
 $('home').textContent=`小窝 ${data.game.home_level || 0} 级 · 下次出发增加 ${2*(data.game.home_level || 0)} 经验`;
 $('bag').replaceChildren(...Object.entries(data.game.materials).map(([name,count])=>{const li=document.createElement('li');li.textContent=`${name} × ${count}`;return li;}));
 $('log').replaceChildren(...data.game.log.map(entry=>{const li=document.createElement('li');li.textContent=`${entry.time.replace('T',' ').slice(0,19)} · ${entry.text}`;return li;}));
 if(!data.game.log.length)$('log').textContent='还没有旅行记录。';
 if(!$('routes').children.length)for(const [key,route]of Object.entries(data.routes)){
  const button=document.createElement('button');button.textContent=`${route.name} · ${route.seconds/60} 分钟`;button.addEventListener('click',()=>mutate(()=>api().pet_dispatch(key),'伙伴出发了，回家后会写进日志。'));$('routes').append(button);
 }
 document.querySelectorAll('#routes button').forEach(button=>button.disabled=busy||!!data.game.task);
}
async function refresh(){
 clearTimeout(timer);
 const requestGeneration=generation;
 try{if(!busy){const data=await api().pet_snapshot();if(!busy&&requestGeneration===generation){if(data.ok)render(data);else notice(data.error);}}}
 catch{notice('伙伴数据暂时无法同步，请稍后再试。');}
 finally{clearTimeout(timer);timer=setTimeout(refresh,document.hidden?5000:1000);}
}
async function mutate(operation,message){
 if(busy||!api())return;busy=true;generation++;
 try{const result=await operation();if(result.ok){render(result);notice(message);}else notice(result.error);}
 catch{notice('操作尚未确认保存，请刷新数据后检查。');}
 finally{busy=false;await refresh();}
}
function ready(){if(connected||!api())return;connected=true;notice('伙伴已就绪。');refresh();}
window.addEventListener('pywebviewready',ready);if(api())ready();
$('upgrade').addEventListener('click',()=>mutate(()=>api().pet_upgrade_home(),'小窝升级了！下一趟冒险经验增加。'));
$('pet').addEventListener('click',()=>mutate(()=>api().pet_interact('pet'),'伙伴开心地蹭了蹭你。'));
$('feed').addEventListener('click',()=>mutate(()=>api().pet_interact('feed'),'吃饱了，下一趟冒险会更有精神。'));
$('desktop').addEventListener('click',async()=>{try{await api().open_desktop_pet();notice('桌宠已打开。拖动顶部把手可移动，点击“冒险”返回这里。');}catch{notice('桌宠窗口未能打开。');}});
window.addEventListener('pagehide',()=>clearTimeout(timer));
