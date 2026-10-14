# WESI

Wage Extraction & Survival Interface

一个个人桌面系统，包含：
- 工资计时器
- 发泄战斗
- 内容库
- 塔罗
- 虚拟宠物与收集系统

默认启动新的工资监控桌面界面，使用 [NumberFlow](https://github.com/barvian/number-flow) 金额动画、[Lucide](https://github.com/lucide-icons/lucide) 图标和 pywebview。支持金额隐私、窗口置顶、紧凑视图、工作倒计时和工资设置。

发薪日默认每月 28 日，可在设置中调整为 1–31 日；短月使用月末，不自动因周末提前或顺延。工资月份与实际到账日期分别记录，每个工资月份只能确认一次，金额以整数分保存。确认成功后金币飞入钱包；可关闭动画，隐藏金额或系统减少动态效果时也不播放。钱包合计为手动确认记录的总额，不是银行余额。点击钱包展开明细，可编辑金额、到账日期和所属月份，或经确认撤销记录。修改月份不会覆盖已有记录。新增记录保留当时的设置月薪，显示实际到账与月薪差额；旧记录标注当前设置月薪参考，不能还原历史月薪。差额不代表扣税或扣款的自动判断。编辑不播放金币动画，撤销后可重新确认。当前仍不支持分笔到账。组件、字体与授权说明见 [ui/THIRD_PARTY.md](ui/THIRD_PARTY.md)，运行无需 Node.js 或联网下载美术资源。

![工资监控预览（演示数据）](docs/screenshots/salary-web.png)

推荐 Python 3.12。Windows 在项目目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Windows 使用系统 Edge WebView2；缺少运行时可从 [微软官网](https://developer.microsoft.com/microsoft-edge/webview2/) 安装。当前版本已在 Linux Qt 后端验证，Windows 外观仍需本地验收。

Linux 需要图形显示、Tk 与 Qt 平台依赖：

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-linux-ui.txt
QT_API=pyside6 .venv/bin/python main.py
```

点击“打开其他功能”切换到原来的 Tk 界面，或运行 `python main.py --classic`。切换时会关闭工资监控窗口，避免两个界面同时写入存档。

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

新版工资监控不包含游戏币或收取玩法，显示的是工资估算，并非银行实际到账记录。月度进度按自然月估算；尚未接入真实发薪周期或银行接口。
旧版像素钱罐仍保留在经典界面，原有 `salary_display` 存档保持兼容。其 Kenney CC0 素材授权位于 `assets/salary/`。

回归检查（GUI 检查自动使用临时存档，不修改个人数据）：

```bash
# 在可用的图形显示下运行全部检查；无 DISPLAY 时 GUI 检查会跳过
python -m unittest discover -s tests -v
```

真实 WebView 检查（临时存档，需要图形显示）：

```bash
python tools/check_webview.py
# Linux Qt 后端
QT_API=pyside6 python tools/check_webview.py --gui qt
```

前端交互检查和组件重建方法见 [ui/THIRD_PARTY.md](ui/THIRD_PARTY.md)。

第一轮代码审阅与后续计划见 [docs/REVIEW.md](docs/REVIEW.md)。

## 塔罗牌桌

从工资监控侧栏点击“塔罗牌桌”，或运行 `python main.py --tarot`。在同一 WebView 内切换，不同时启动两个工资存档写入窗口。

新增 WebView 界面提供八种牌阵：单张、时间三牌、二选一、关系镜像、现状与建议、五牌探索、七牌马蹄、凯尔特十字。选择时预览牌位；抽取后点击牌背逐张翻开，点击牌面查看核心牌义、牌位视角、行动建议及反思问题。逆位采用独立内容，不是正位加前缀。十字牌阵第二张横置在核心牌上。支持键盘翻牌及系统减少动态效果。

![塔罗牌桌（演示阅读）](docs/screenshots/tarot-table.png)

78 张牌的正逆位中文内容位于 `data/tarot_meanings_zh.json`，由 WESI 编写。当前解读为固定牌义与牌位视角组合，不是 AI 个性化推理；问题只用于记录和自行对照，不用于猜测个人经历。复杂牌间关系和可选 AI 解读留待下一轮。

新版历史沿用 `tarot_history.json`，保存当次牌面、正逆位、牌位布局和解读文本。打开历史不重新抽牌、不按新牌义改写旧记录。旧 Tk 历史兼容，经典窗口仍保留旧的四种牌阵；新版从 WebView 进入。不会自动把阅读问题发往外部服务。

开源参考、现有牌面来源及本轮复用范围见 [docs/TAROT_DESIGN.md](docs/TAROT_DESIGN.md)。桌面验证使用临时历史：`QT_API=pyside6 python tools/check_tarot_webview.py`（Linux Qt）；测试详情同前端说明。Windows WebView2 翻牌效果仍需本地验收。

### 整组解读与可选 AI

翻开全部牌后显示离线阅读资料：问题关键词提示、花色主题、正逆位概况和单牌行动提示。离线层不生成整体故事或牌间综合结论；这部分由配置后的语义模型处理。新阅读保存当次资料，旧记录保持原文，不自动重算。

AI 默认不请求任何服务。可在启动前配置兼容 OpenAI Chat Completions 的服务（密钥不写入存档或前端）：

```powershell
$env:WESI_TAROT_AI_BASE = "https://api.openai.com/v1"
$env:WESI_TAROT_AI_MODEL = "你使用的模型名称"
$env:WESI_TAROT_AI_KEY = "你的服务密钥"
.\.venv\Scripts\python.exe main.py --tarot
```

本机服务可使用 `http://127.0.0.1:端口/v1`；远程服务使用 HTTPS。配置后点击“结合问题深入解读（AI）”，确认发送当前问题、牌位及牌义。调用可能产生服务费用；不会发送工资数据、历史中的其他阅读或牌面图片。超时为 45 秒，服务需返回可解析的结构化 JSON；不兼容响应会显示失败并保留离线阅读。

AI 结果保存到当次历史，重看不重新调用，也不重新抽牌。当前不提供重新生成按钮。生成成功但保存失败时，当前进程缓存结果以便重试写入；超时、重启或服务端已完成但客户端未收到响应时，重试仍可能产生新的请求。未使用真实付费服务验证，桌面集成测试使用本机模拟服务，实际模型质量与服务兼容性需要配置后试用。

### 成熟资料与解读质量评审

新版单牌详情可展开公开资料原文：本地固定版本的 LindseyB/tarot-api 正逆位含义与 Corpora（注明 Mark McElroy 来源）的建设性/失衡视角。出处与授权见 [data/tarot_reference/SOURCES.md](data/tarot_reference/SOURCES.md)。AI 实际读取这些资料，旧版中文提示仅作辅助；不使用预测日期条目。

离线页不再生成关键词拼接的整体结论，只提供统计与单牌依据。完整问题导向的解读需要配置真实模型；程序测试和模拟服务不能证明解读质量。三个固定案例覆盖财务时间、关系沟通与职业选择，可先导出用于评审：

```bash
python tools/evaluate_tarot_reading.py --output /tmp/tarot-cases.json
# 已配置模型时，明确执行真实调用（可能产生费用）
python tools/evaluate_tarot_reading.py --ai --output /tmp/tarot-model-review.json
```

评审重点是是否回答问题、是否解释牌位之间的矛盾、是否考虑相反线索、行动是否具体、是否编造个人事实。导出文件默认标为“未评审”，不自动打语义质量分。

## 桌宠与文字放置冒险

默认工资页左侧点击“宠物与冒险”，或运行 `python main.py --pet`。点击“放到桌面”打开置顶、无边框的透明伙伴窗口：顶部把手拖动窗口，点击小黄鸭互动，“冒险”返回游戏页，“×”关闭桌宠。主程序关闭或切换经典界面时桌宠也关闭。

实际接入 [VS Code Pets](https://github.com/tonybaloney/vscode-pets) 的 MIT 引擎与 Marc Duiker 小黄鸭动画；普通用户无需 VS Code 或 Node.js。出处和固定源码见 [ui/vendor/vscode-pets/UPSTREAM.md](ui/vendor/vscode-pets/UPSTREAM.md)。本轮小黄鸭会在自己的窗口内行走/跑步，尚不检测其他应用边缘或穿透点击；Windows WebView2 的透明与拖动外观需要本地验收。Linux 透明显示还取决于桌面合成器。

文字游戏有公园散步（1 分钟）、林间采集（5 分钟）、旧城探索（15 分钟）。一次派出一趟，退出后回来会结算一次，不按离线天数重复产出。探索获得经验、干粮、树枝和石片；喂食消耗干粮，公园可补充。摸摸/喂食每种互动间隔一分钟，提高亲密度。用树枝与石片升级小窝，最多 5 级；每级给之后派出的任务增加 2 经验，不改写已在途任务。

新进度保存在 app_state.json 的 pet_game，沿用旧宠物名称和亲密度，保留原背包与历史。所有虚拟物品都与现实工资无关。文字冒险日志最多保留 50 条，保留总经验与材料。桌宠与工资页使用同一存档写入器，原经典宠物页保持兼容。

![伙伴小屋预览（演示存档）](docs/screenshots/pet-companion.png)

真实桌面检查：`QT_API=pyside6 python tools/check_pet_webview.py`，使用临时存档，验证上游精灵、置顶窗口、互动、唯一窗口、共享存档及一次性离线奖励。
