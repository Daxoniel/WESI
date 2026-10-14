# 本地公开塔罗资料

本轮实际打包并读取以下固定版本 JSON，不依赖运行时 API 或 CDN。

- `tarot.json`：[LindseyB/tarot-api](https://github.com/LindseyB/tarot-api/blob/319ce18f1b583035e00c63854a2a405a0088bc73/tarot.json)，提交 `319ce18f1b583035e00c63854a2a405a0088bc73`，MIT；原始许可证保留于 `MIT-LICENSE.txt`。78 牌、独立正逆位含义。
- `corpora_interpretations.json`：[dariusk/corpora](https://github.com/dariusk/corpora/blob/2e7adec11a0561696c236ae1fca82e88be173d42/data/divination/tarot_interpretations.json)，提交 `2e7adec11a0561696c236ae1fca82e88be173d42`，上游 README 明确以 CC0 发布数据，保留于 `CORPORA-README.md`。数据说明注明牌义来自 Mark McElroy 的 *A Guide to Tarot Meanings*。这是对仓库所发布资料的来源说明，不宣称整本书可自由使用。

以花色与等级映射，不依赖上游名字拼写。LindseyB 的 pentacles 与 Corpora 的 coins 统一对应 WESI 星币；宫廷牌使用 page/knight/queen/king。保留原文，不下载或替换图片。

Corpora 的 light/shadow 表示建设性与失衡的表现，不机械对应正逆位。解读不使用 fortune_telling、季节、占星或数字推算日期。只选该方向含义与 light/shadow 的原文，传给模型并在单牌详情显示。传统象征不是用户现实情况的证据。

`READING_PROTOCOL.md` 是 WESI 编写的综合流程及示范，未复制未授权技能。示范不是上游生成结果，也不是经过真实服务验证的模型输出。这里接入资料检索，不是模型训练或微调。

打包文件仅清理行尾空白，JSON 字段内容未修改。
