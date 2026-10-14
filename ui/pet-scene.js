import {RubberDuck} from './vendor/pet-engine.js';
const $=id=>document.getElementById(id);
const embedded=new URLSearchParams(location.search).has('embedded');
if(embedded){$('pet-tools').hidden=true;document.documentElement.classList.add('embedded');}
const pet=new RubberDuck($('sprite'),$('collision'),$('speech'),'large',40,8,'./vendor/vscode-pets/media/rubber-duck/yellow',8,'Mochi',3);
pet.nextFrame();
let timer=setInterval(()=>{if(!document.hidden)pet.nextFrame();},100);
const play=()=>{if(pet.canSwipe)pet.swipe();pet.showSpeechBubble('嘎！一起去探险吧。',2000);};
$('collision').addEventListener('click',play);
$('collision').addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();play();}});
$('game-open').addEventListener('click',()=>window.pywebview?.api.open_pet_game());
$('pet-close').addEventListener('click',()=>window.pywebview?.api.close_desktop_pet());
window.addEventListener('pagehide',()=>clearInterval(timer));
