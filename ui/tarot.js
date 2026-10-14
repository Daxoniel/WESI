const $ = id => document.getElementById(id);
const api = () => window.pywebview?.api;
let catalog = null, current = null, busy = false;
const revealed = new Set();
const notice = message => { $('notice').textContent = message; };
function preview() {
  const spread = catalog.spreads[$('spread').value];
  $('spread-description').textContent = spread.description;
  const coordinates = spread.coordinates || spread.positions.map((_, i) => [i, 0]);
  $('preview').style.gridTemplateColumns = `repeat(${Math.max(...coordinates.map(([x]) => x))+1}, minmax(0, 1fr))`;
  $('preview').replaceChildren(...spread.positions.map((position, i) => {
    const span = document.createElement('span'); span.textContent = `${i+1} ${position}`;
    const [x, y] = coordinates[i]; span.style.gridColumn = x+1; span.style.gridRow = y+1;
    if ($('spread').value === 'celtic' && i === 1) {span.style.gridRow = 5; span.textContent += '（交叉于 1）';}
    return span;
  }));
}
async function ready() {
  if (catalog || !api()) return;
  try {
    catalog = await api().tarot_catalog();
    $('spread').replaceChildren(...Object.entries(catalog.spreads).map(([key, spread]) => {
      const option = document.createElement('option'); option.value = key; option.textContent = `${spread.label} · ${spread.positions.length} 张`; return option;
    }));
    preview(); notice('本地牌库已就绪。');
  } catch { notice('牌库加载失败，请重新打开牌桌。'); }
}
window.addEventListener('pywebviewready', ready);
if (api()) ready();
setTimeout(() => {if (!api()) notice('请通过 python main.py --tarot 启动，或从工资监控打开牌桌。');}, 5000);
$('spread').addEventListener('change', preview);
function showReading(index) {
  const card = current.cards[index];
  document.querySelectorAll('.tarot-card').forEach((button, i) => button.classList.toggle('selected', i === index));
  $('card-title').textContent = `${card.name_zh} · ${card.position}`;
  $('orientation').textContent = `${card.name_en || ''} / ${card.reversed ? '逆位' : '正位'}`;
  const reading = {...(card.reading || {core:card.desc || '旧记录没有保存解读内容。'})};
  if (card.reference) {
    reading.reference = `对应${card.reversed ? '逆位' : '正位'}：${card.reference.direction_meanings.join('；')}\n建设性视角：${card.reference.constructive.join('；')}\n失衡视角：${card.reference.shadow.join('；')}\n来源：${card.reference.sources.join(' / ')}。${card.reference.note}`;
  }
  const labels = {core:'核心牌义', position:'此牌位的视角', action:'行动建议', reflection:'反思问题',reference:'公开资料原文（英语）'};
  $('card-reading').replaceChildren(...Object.entries(reading).flatMap(([key, value]) => {
    const heading = document.createElement('h3'); heading.textContent = labels[key] || key;
    const paragraph = document.createElement('p'); paragraph.textContent = value;
    if (key === 'reference') {const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent=heading.textContent;details.append(summary,paragraph);return [details];}
    return [heading, paragraph];
  }));
}
function reportNodes(report) {
  const nodes = [];
  if (!report) return nodes;
  const overview = document.createElement('p'); overview.textContent = report.overview; nodes.push(overview);
  if (report.conclusion) {const heading=document.createElement('h3');heading.textContent='针对问题的综合回答';const paragraph=document.createElement('p');paragraph.textContent=report.conclusion;nodes.push(heading,paragraph);}
  const labels = {evidence:'结论依据',themes:'整体主题',relations:'牌间关系',actions:'可执行的下一步',questions:'值得核实的问题'};
  for (const [key,label] of Object.entries(labels)) {
    if (!report[key]?.length) continue;
    const heading = document.createElement('h3'); heading.textContent = label;
    const list = document.createElement('ul');
    for (const value of report[key]) {const li = document.createElement('li');li.textContent=value;list.append(li);}
    nodes.push(heading,list);
  }
  const method = document.createElement('small');method.textContent=report.method || '';nodes.push(method);
  return nodes;
}
function wholeReading() {
  const allRevealed = current && revealed.size === current.cards.length;
  $('whole-reading').hidden = !allRevealed;
  if (!allRevealed) return;
  $('offline-reading').replaceChildren(...reportNodes({...current.synthesis,conclusion:undefined,evidence:undefined,relations:[]}));
  if (!current.synthesis) $('offline-reading').textContent = '旧记录未保存整组解读，保留原始单牌文字。';
  $('ai-reading').replaceChildren(...reportNodes(current.ai_reading));
  if (current.ai_reading) {const heading=document.createElement('h2');heading.textContent='AI 深入解读';$('ai-reading').prepend(heading);}
  $('ai-generate').hidden = !!current.ai_reading;
  $('ai-generate').disabled = busy || !catalog.ai?.available || !current.id;
  $('ai-note').textContent = current.ai_reading ? `已保存 ${current.ai_reading.model} 的解读，重看不会再次调用 AI。` : catalog.ai?.available ? `模型 ${catalog.ai.model}。点击后将当前问题、牌位与牌义发送到配置的服务，可能产生费用。` : 'AI 默认关闭；可配置服务地址、模型和密钥后重新启动。离线整组解读无需联网。';
}
$('ai-generate').addEventListener('click', async () => {
  if (busy || !current?.id || !confirm('将本次问题和抽出的牌发送到你配置的 AI 服务生成解读？')) return;
  busy = true; $('ai-generate').disabled = true; $('draw').disabled = true; $('history-open').disabled = true;
  notice('正在生成深入解读，牌面和正逆位保持不变…');
  try {
    const result = await api().tarot_ai_reading(current.id);
    if (!result.ok) {notice(result.error); return;}
    current = result.entry; wholeReading(); notice('AI 解读已保存，没有重新抽牌。');
  } catch {notice('AI 请求未确认；离线阅读仍保留，可从历史检查结果。');}
  finally {busy = false; $('draw').disabled = false; $('history-open').disabled = false; wholeReading();}
});
function reveal(index) {
  revealed.add(index);
  const button = $('table').children[index];
  button.classList.add('revealed');
  button.setAttribute('aria-label', `${current.cards[index].position}：${current.cards[index].name_zh} ${current.cards[index].reversed ? '逆位' : '正位'}`);
  button.querySelector('.card-caption').textContent = `${index+1} ${current.cards[index].position} · ${current.cards[index].name_zh}`;
  showReading(index);
  wholeReading();
}
async function renderEntry(entry, history = false) {
  current = entry; revealed.clear(); $('whole-reading').hidden = true;
  $('reading-title').textContent = entry.spread_label || catalog.spreads[entry.spread]?.label || entry.spread;
  $('reading-question').textContent = `${entry.time} · ${entry.question || '未填写问题'}`;
  $('summary').textContent = entry.summary || '旧记录：保留当次解读，不重新生成。';
  $('card-title').textContent = '逐张探索'; $('orientation').textContent = '点击牌背翻开，点击牌面查看解读。'; $('card-reading').replaceChildren();
  const layout = entry.layout || catalog.spreads[entry.spread];
  const coordinates = layout?.coordinates || entry.cards.map((_, i) => [i, 0]);
  const columns = Math.max(...coordinates.map(([x]) => x)) + 1;
  $('table').style.gridTemplateColumns = `repeat(${columns}, minmax(0, 1fr))`;
  $('table').replaceChildren(...entry.cards.map((card, index) => {
    const button = document.createElement('button'); button.className = 'tarot-card'; if (entry.spread === 'celtic' && index === 1) button.classList.add('cross-card'); button.type = 'button';
    const [x, y] = coordinates[index] || [index, 0];
    button.style.gridColumn = x+1; button.style.gridRow = y+1;
    button.setAttribute('aria-label', `翻开第 ${index+1} 张：${card.position}`);
    const surface = document.createElement('div'); surface.className = 'card-surface';
    const back = document.createElement('div'); back.className = 'card-back'; back.textContent = '✧'; back.setAttribute('aria-hidden', 'true');
    const front = document.createElement('div'); front.className = 'card-front'; front.setAttribute('aria-hidden', 'true');
    surface.append(back, front);
    const caption = document.createElement('span'); caption.className = 'card-caption'; caption.textContent = `${index+1} ${card.position}`;
    button.append(surface, caption); button.addEventListener('click', () => reveal(index));
    api().tarot_image(card.img).then(source => {
      if (!source) {front.textContent = card.name_zh; return;}
      const img = document.createElement('img'); img.src = source; img.alt = ''; if (card.reversed) img.className = 'reversed'; front.append(img);
    }).catch(() => {front.textContent = card.name_zh;});
    return button;
  }));
  $('reveal-all').hidden = false;
  if (history) entry.cards.forEach((_, index) => reveal(index));
}
$('reveal-all').addEventListener('click', () => current?.cards.forEach((_, index) => reveal(index)));
$('draw-form').addEventListener('submit', async event => {
  event.preventDefault(); if (busy || !catalog) return;
  busy = true; $('draw').disabled = true; $('history-open').disabled = true; notice('正在洗牌并保存这次阅读…');
  try {
    const result = await api().tarot_draw($('spread').value, $('question').value);
    if (!result.ok) {notice(result.error); return;}
    await renderEntry(result.entry); notice('阅读已保存。请逐张翻牌。');
  } catch {notice('抽牌结果未确认，请先查看历史记录再重试。');}
  finally {busy = false; $('draw').disabled = false; $('history-open').disabled = false; wholeReading();}
});
$('history-open').addEventListener('click', async () => {
  try {
    const entries = await api().tarot_history();
    $('history-list').replaceChildren(...entries.filter(entry => Array.isArray(entry.cards)).map(entry => {
      const button = document.createElement('button'); button.textContent = `${entry.time} · ${entry.spread_label || catalog?.spreads[entry.spread]?.label || entry.spread} · ${entry.question || '未填写问题'}`;
      button.addEventListener('click', () => {renderEntry(entry, true); $('history-dialog').close(); notice('已还原历史牌桌，未重新抽牌。');}); return button;
    }));
    if (!$('history-list').children.length) $('history-list').textContent = '还没有阅读记录。';
    $('history-dialog').showModal();
  } catch {notice('历史读取失败，请稍后重试。');}
});
$('history-close').addEventListener('click', () => $('history-dialog').close());
