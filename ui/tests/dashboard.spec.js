import { test, expect } from '@playwright/test';

const snapshot = {
  income: {monthly_net_salary: 2600, work_start: '09:00', work_end: '17:00', employment_start: '2026-04-01 09:00:00'},
  stats: {today: 72.48, rate: .0041667, month: 912.48, joined: 15912.48, hourly_rate: 15, daily_target: 120},
  active: true, status: '工作中', seconds_left: 10800, countdown_label: '距离下班',
  date: '2026-10-08', month_label: '2026.10.01 — 10.31', day_progress: .604, month_progress: .351,
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(data => {
    window.fixture = data;
    window.calls = [];
    window.pywebview = {api: {
      snapshot: async () => {
        if (window.failSnapshot) throw Error('offline');
        return window.fixture;
      },
      set_pin: async value => { window.calls.push(['pin', value]); return value; },
      set_compact: async value => { window.calls.push(['compact', value]); return value; },
      open_classic: async () => window.calls.push(['classic']),
      save_settings: async payload => {
        if (payload.work_end <= payload.work_start) return {ok: false, error: '下班时间须晚于上班时间'};
        window.fixture.income = {...window.fixture.income, ...payload};
        return {ok: true, snapshot: window.fixture};
      },
    }};
  }, snapshot);
  await page.goto('/');
});

test('real NumberFlow and Lucide load locally and update from bridge', async ({ page }) => {
  await expect(page.locator('#status')).toHaveText('工作中');
  await expect(page.locator('#month')).toHaveText('€912.48');
  expect(await page.locator('#amount').evaluate(el => !!el.shadowRoot)).toBe(true);
  expect(await page.locator('#amount').evaluate(el => el.value)).toBe(72.48);
  await expect(page.locator('#privacy svg')).toHaveCount(1);
  await page.evaluate(() => { window.fixture.stats.today = 72.49; });
  await expect.poll(() => page.locator('#amount').evaluate(el => el.value)).toBe(72.49);
});

test('privacy hides every money field and restores it', async ({ page }) => {
  await page.getByRole('button', {name: '隐藏金额', exact: true}).click();
  await expect(page.locator('#amount')).toBeHidden();
  await expect(page.locator('#masked')).toBeVisible();
  for (const id of ['month', 'joined', 'hourly', 'salary', 'period-earned', 'daily-target'])
    await expect(page.locator(`#${id}`)).toHaveText('••••••');
  await page.getByRole('button', {name: '显示金额', exact: true}).click();
  await expect(page.locator('#amount')).toBeVisible();
  await expect(page.locator('#joined')).toHaveText('€15,912.48');
});

test('native pin and compact actions are bridged; compact does not overflow', async ({ page }) => {
  await page.getByRole('button', {name: '窗口置顶', exact: true}).click();
  await expect(page.locator('#pin')).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', {name: '紧凑视图', exact: true}).click();
  await page.setViewportSize({width: 420, height: 440});
  await expect(page.locator('aside')).toBeHidden();
  await expect(page.locator('.metrics')).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.evaluate(() => window.calls)).toEqual([['pin', true], ['compact', true]]);
});

test('settings reject invalid schedule then save without reloading', async ({ page }) => {
  await page.getByRole('button', {name: '工资设置', exact: true}).click();
  await page.locator('#end-input').fill('08:00');
  await page.getByRole('button', {name: '保存并更新监控'}).click();
  await expect(page.locator('#settings-error')).toContainText('下班时间');
  await page.locator('#end-input').fill('18:00');
  await page.locator('#salary-input').fill('3000');
  await page.getByRole('button', {name: '保存并更新监控'}).click();
  await expect(page.locator('#settings-dialog')).not.toBeVisible();
  await expect(page.locator('#salary')).toHaveText('€3,000.00');
});

test('bridge failure is visible instead of pretending stale data is live', async ({ page }) => {
  await expect(page.locator('#status')).toHaveText('工作中');
  await page.evaluate(() => { window.failSnapshot = true; });
  await expect(page.locator('#connection')).toContainText('可能已过期');
  await expect(page.locator('#status')).toHaveText('等待同步');
  await page.evaluate(() => { window.failSnapshot = false; });
  await expect(page.locator('#status')).toHaveText('工作中');
});

test('dashboard needs no third-party network requests', async ({ page }) => {
  const external = [];
  page.on('request', request => { if (!request.url().startsWith('http://127.0.0.1:8768')) external.push(request.url()); });
  await page.reload();
  await expect(page.locator('#status')).toHaveText('工作中');
  expect(external).toEqual([]);
});
