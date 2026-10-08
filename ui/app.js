import { NumberFlow, icons } from './vendor/number-flow.js';

icons();
const $ = id => document.getElementById(id);
const money = new Intl.NumberFormat('en-IE', {style: 'currency', currency: 'EUR'});
const amount = $('amount');
amount.format = {style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2};
amount.locales = 'en-IE';
let current = null, privacy = false, pinned = false, compact = false, pollTimer = null;
let editingPeriod = null, historySignature = null;
let connected = false, saving = false, generation = 0;
const api = () => window.pywebview?.api;
const text = (id, value) => { $(id).textContent = value; };
const financial = value => privacy ? '••••••' : money.format(value);
const pressed = (id, value) => $(id).setAttribute('aria-pressed', String(value));

function render(data) {
  current = data;
  const payroll = data.payroll || {payday: 28, animations: true, receipts: {}};
  text('payday-info', `每月 ${payroll.payday} 日 · 下次 ${data.next_payday || '—'}${data.payday_days === undefined ? '' : ` · ${data.payday_days === 0 ? '今天发薪' : `还有 ${data.payday_days} 天`}`}`);
  const entries = Object.entries(payroll.receipts).sort(([a], [b]) => b.localeCompare(a));
  text('wallet-total', financial(entries.reduce((sum, [, receipt]) => sum + receipt.amount_cents / 100, 0)));
  const signature = JSON.stringify([entries, privacy, data.income.monthly_net_salary]);
  if (signature !== historySignature) {
    historySignature = signature;
    $('receipt-history').replaceChildren(...entries.map(([period, receipt]) => {
      const item = document.createElement('li');
      const expected = receipt.expected_cents === undefined ? data.income.monthly_net_salary : receipt.expected_cents / 100;
      const description = document.createElement('div');
      description.textContent = `${period} · ${receipt.received_on} · 实际 ${financial(receipt.amount_cents / 100)}`;
      const comparison = document.createElement('div');
      comparison.className = 'receipt-comparison';
      comparison.textContent = `${receipt.expected_cents === undefined ? '当前设置月薪（旧记录参考）' : '记录时设置月薪'} ${financial(expected)} · 差额 ${financial(receipt.amount_cents / 100 - expected)}`;
      item.append(description, comparison);
      for (const [label, action] of [['编辑', () => openReceipt(period)], ['撤销', () => revokeReceipt(period)]]) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'text-button';
        button.textContent = label; button.setAttribute('aria-label', `${label} ${period} 到账记录`);
        button.addEventListener('click', action); item.append(button);
      }
      return item;
    }));
    if (!entries.length) {const li = document.createElement('li'); li.textContent = '暂无到账记录'; $('receipt-history').append(li);}
  }
  text('receipt-status', payroll.receipts[data.date.slice(0, 7)] ? '本月工资已记录到账' : '本月工资尚未确认到账');
  text('date', data.date.replaceAll('-', ' / '));
  text('status', data.status);
  $('status').classList.toggle('active', data.active);
  amount.hidden = privacy;
  $('masked').hidden = !privacy;
  if (!privacy) amount.update(data.stats.today);
  text('rate', privacy ? '金额已隐藏' : `${money.format(data.stats.rate * 60)} / 分钟`);
  text('day-percent', `${Math.round(data.day_progress * 100)}%`);
  $('ring-fill').style.strokeDashoffset = String(320.44 * (1 - data.day_progress));
  text('countdown-label', data.countdown_label);
  if (data.seconds_left === null) text('countdown', '—');
  else {
    const seconds = data.seconds_left;
    text('countdown', [Math.floor(seconds/3600), Math.floor(seconds/60)%60, seconds%60].map(n => String(n).padStart(2, '0')).join(':'));
  }
  text('daily-target', financial(data.stats.daily_target));
  text('month', financial(data.stats.month));
  text('joined', financial(data.stats.joined));
  text('hourly', financial(data.stats.hourly_rate));
  text('employment', `${data.income.employment_start.split(' ')[0]} 入职`);
  text('schedule', `${data.income.work_start} — ${data.income.work_end} / 周一至周五`);
  text('period', data.month_label);
  text('period-earned', financial(data.stats.month));
  text('salary', financial(data.income.monthly_net_salary));
  text('month-percent', `${Math.round(data.month_progress*100)}%`);
  $('month-fill').style.width = `${data.month_progress*100}%`;
}

async function poll() {
  clearTimeout(pollTimer);
  if (saving) { pollTimer = setTimeout(poll, 1000); return; }
  const requestGeneration = generation;
  try {
    const data = await api().snapshot();
    if (requestGeneration !== generation || saving) return;
    render(data);
    text('connection', '');
    connected = true;
  } catch {
    text('connection', '本地工资引擎暂时不可用。显示值可能已过期，正在重试…');
    text('status', '等待同步');
    $('status').classList.remove('active');
  } finally {
    pollTimer = setTimeout(poll, document.hidden ? 5000 : 1000);
  }
}

function ready() {
  if (connected || !api()) return;
  connected = true;
  poll();
}
window.addEventListener('pywebviewready', ready);
if (api()) ready();
setTimeout(() => {
  if (!connected) text('connection', '请通过 python main.py 启动桌面监控；浏览器页面没有连接本地工资引擎。');
}, 5000);

$('privacy').addEventListener('click', () => {
  privacy = !privacy;
  if (privacy) $('coin-layer').replaceChildren();
  pressed('privacy', privacy);
  $('privacy').title = privacy ? '显示金额' : '隐藏金额';
  $('privacy').setAttribute('aria-label', $('privacy').title);
  if (current) render(current);
});

async function nativeToggle(id, value, method, commit) {
  $(id).disabled = true;
  try {
    if (!api()) throw new Error('bridge not ready');
    const enabled = await api()[method](value);
    commit(enabled);
    pressed(id, enabled);
  } catch { text('connection', '窗口操作失败，请稍后再试。'); }
  finally { $(id).disabled = false; }
}
$('pin').addEventListener('click', () => nativeToggle('pin', !pinned, 'set_pin', enabled => { pinned = enabled; }));
$('compact').addEventListener('click', () => nativeToggle('compact', !compact, 'set_compact', enabled => {
  compact = enabled;
  document.body.classList.toggle('compact', enabled);
}));
$('classic').addEventListener('click', async () => {
  if (!api() || !confirm('切换到其他功能会关闭工资监控窗口。继续吗？')) return;
  try { await api().open_classic(); }
  catch { text('connection', '暂时无法打开其他功能。'); }
});

document.querySelectorAll('.settings-open').forEach(button => button.addEventListener('click', () => {
  if (!current) return;
  $('payday-input').value = current.payroll?.payday || 28;
  $('animations-input').checked = current.payroll?.animations !== false;
  $('salary-input').value = current.income.monthly_net_salary;
  $('start-input').value = current.income.work_start;
  $('end-input').value = current.income.work_end;
  $('employment-input').value = current.income.employment_start.replace(' ', 'T');
  text('settings-error', '');
  $('settings-dialog').showModal();
}));
$('settings-close').addEventListener('click', () => $('settings-dialog').close());
$('settings-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (saving) return;
  const button = event.submitter;
  saving = true;
  generation += 1;
  button.disabled = true;
  const employment = $('employment-input').value;
  const payload = {
    payday: $('payday-input').value, animations: $('animations-input').checked,
    monthly_net_salary: $('salary-input').value,
    work_start: $('start-input').value, work_end: $('end-input').value,
    employment_start: employment.replace('T', ' ') + (employment.length === 16 ? ':00' : ''),
  };
  try {
    const result = await api().save_settings(payload);
    if (!result.ok) { text('settings-error', result.error); return; }
    render(result.snapshot);
    $('settings-dialog').close();
  } catch { text('settings-error', '保存失败，设置未确认写入。请重试。'); }
  finally { saving = false; button.disabled = false; }
});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && api() && connected && !saving) {
    // Keep a single polling chain: the existing timer will refresh shortly.
    text('connection', '正在同步本地数据…');
  }
});

function openReceipt(period = null) {
  if (!current || saving) return;
  editingPeriod = period;
  const receipt = period ? current.payroll.receipts[period] : null;
  $('receipt-period').value = period || current.date.slice(0, 7);
  $('receipt-period').max = current.date.slice(0, 7);
  $('receipt-date').value = receipt?.received_on || current.date;
  $('receipt-date').max = current.date;
  $('receipt-amount').value = receipt ? (receipt.amount_cents / 100).toFixed(2) : current.income.monthly_net_salary;
  text('receipt-title', period ? '编辑到账记录' : '确认工资到账');
  $('receipt-form').querySelector('button[type=submit]').textContent = period ? '保存修改' : '保存到账记录';
  text('receipt-error', '');
  $('receipt-dialog').showModal();
}
$('receipt-open').addEventListener('click', () => openReceipt());
$('wallet-icon').addEventListener('click', () => { $('wallet-details').open = !$('wallet-details').open; });
$('wallet-details').addEventListener('toggle', () => {
  $('wallet-icon').setAttribute('aria-expanded', String($('wallet-details').open));
});
async function revokeReceipt(period) {
  if (saving || !confirm(`撤销 ${period} 的到账记录？钱包合计会扣除这笔记录，此操作不会移动银行资金。`)) return;
  saving = true; generation += 1;
  try {
    const result = await api().revoke_receipt(period);
    if (!result.ok) {text('receipt-notice', result.error); return;}
    render(result.snapshot); text('receipt-notice', `${period} 到账记录已撤销`);
  } catch {text('receipt-notice', '撤销结果尚未确认，请刷新明细后检查。');}
  finally {saving = false;}
}
$('receipt-close').addEventListener('click', () => $('receipt-dialog').close());
function celebrateReceipt() {
  if (privacy || current.payroll?.animations === false || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const target = $('wallet-icon').getBoundingClientRect();
  const source = $('receipt-open').getBoundingClientRect();
  const layer = $('coin-layer');
  for (let i = 0; i < 16; i++) {
    const coin = document.createElement('img');
    coin.src = './vendor/coin.png'; coin.className = 'receipt-coin';
    coin.style.left = `${source.left + source.width / 2}px`;
    coin.style.top = `${source.top + source.height / 2}px`;
    layer.append(coin);
    const dx = target.left + target.width/2 - source.left - source.width/2;
    const dy = target.top + target.height/2 - source.top - source.height/2;
    const animation = coin.animate([
      {transform: 'translate(-50%, -50%) scale(.5)', opacity: 0},
      {transform: `translate(${dx/2 + (i%5-2)*24}px, ${dy/2-75-i%3*15}px) rotate(160deg)`, opacity: 1, offset: .45},
      {transform: `translate(${dx}px, ${dy}px) rotate(360deg) scale(.25)`, opacity: 0},
    ], {duration: 800, delay: i*45, easing: 'ease-in-out'});
    animation.onfinish = () => coin.remove();
    animation.oncancel = () => coin.remove();
  }
  $('wallet-icon').animate([{transform:'scale(1)'},{transform:'scale(1.25)'},{transform:'scale(1)'}], {duration:400, delay:1000});
}
$('receipt-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (saving) return;
  const button = event.submitter;
  saving = true; generation += 1; button.disabled = true;
  try {
    const payload = {
      period: $('receipt-period').value, amount: $('receipt-amount').value, received_on: $('receipt-date').value,
    };
    const result = editingPeriod ? await api().edit_receipt(editingPeriod, payload) : await api().confirm_receipt(payload);
    if (!result.ok) {text('receipt-error', result.error); return;}
    render(result.snapshot);
    $('receipt-dialog').close();
    if (editingPeriod) text('receipt-notice', '到账记录已更新');
    else {text('receipt-notice', '到账记录已保存'); celebrateReceipt();}
  } catch {text('receipt-error', '未能确认记录是否保存，请重试；同一月份不会重复记账。');}
  finally {saving = false; button.disabled = false;}
});
