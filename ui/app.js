import { NumberFlow, icons } from './vendor/number-flow.js';

icons();
const $ = id => document.getElementById(id);
const money = new Intl.NumberFormat('en-IE', {style: 'currency', currency: 'EUR'});
const amount = $('amount');
amount.format = {style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2};
amount.locales = 'en-IE';
let current = null, privacy = false, pinned = false, compact = false, pollTimer = null;
let connected = false, saving = false, generation = 0;
const api = () => window.pywebview?.api;
const text = (id, value) => { $(id).textContent = value; };
const financial = value => privacy ? '••••••' : money.format(value);
const pressed = (id, value) => $(id).setAttribute('aria-pressed', String(value));

function render(data) {
  current = data;
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
