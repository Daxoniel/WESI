# WESI

Wage Extraction & Survival Interface

一个个人桌面系统，包含：
- 工资计时器
- 发泄战斗
- 内容库
- 塔罗
- 虚拟宠物与收集系统

开发环境：Python 3.10+（云环境使用 3.12）、Tk、requirements.txt 中固定的依赖。

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Windows 下使用 `.venv\Scripts\python.exe`。Linux 需可用的 Tk 和图形显示；无桌面环境可用 Xvfb 执行窗口测试。

工资设置支持周一至周五的当日上下班时段，默认 09:00–17:00，只在该时段内累计。
日收入按 `月净收入 × 12 ÷ (52 × 5)` 估算，再按当日班次时长均摊；显示流速与累计使用同一算法。
入职前、周末、上班前和下班后不增长。修改工资或班次会重新估算历史累计；当前不包含节假日、午休、跨夜班次或调薪历史。

默认沿用 `data/app_state.json` 和 `data/tarot_history.json`，保留旧存档。
可以设置 `WESI_DATA_DIR` 指向独立的可写目录，隔离存档、诗词缓存和新导入的头像/宠物图片。
新目录默认创建新档，不自动复制个人数据。JSON 原子写入；遇到无法解析或不兼容的存档会先保留 `.invalid-*.bak` 备份。
备份应妥善保留，程序不会自动恢复它们。

塔罗默认读取仓库内的 `data/tarot.json` 并映射已有的 78 张牌面；如存在有效的 `data/tarot_cards_zh.json` 则优先使用。
需要导出中文牌库时可运行：

```bash
python tools/make_tarot_json.py --output /tmp/wesi-tarot-cards.json
```

诗词接口不可用时会回退到本地内容；网络请求在后台执行，不阻塞窗口。
宠物摸鱼不依赖宠物窗口：关闭窗口仍会完成，退出程序后再次打开会恢复未完成的一次任务。

工资主页增加像素风价值回收站：变化数字滚动、工作状态与上下班倒计时、传送带和可点击的钱罐。
“收取”把已累计的完整分币收入展示钱罐，不代表银行实际到账，也不改变工资计算。
钱罐每日重置，收取记录、目标金额（默认 €10）与安静模式保存在 `salary_display` 中；旧档会自动补齐。
安静模式关闭数字滚动、传送带运动及庆祝粒子。窗口较小时可以滚动查看下方功能。
像素金币来自 Kenney 的 CC0 资源，出处及授权文件位于 `assets/salary/`。

回归检查（GUI 检查自动使用临时存档，不修改个人数据）：

```bash
python -m unittest discover -s tests -p test_core.py -v
# 在可用的图形显示下运行全部检查；无 DISPLAY 时 GUI 检查会跳过
python -m unittest discover -s tests -v
```

第一轮代码审阅与后续计划见 [docs/REVIEW.md](docs/REVIEW.md)。
