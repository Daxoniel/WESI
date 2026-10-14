# 塔罗第一轮：开源参考与实现范围

2026-10-14 核对仓库 README、许可证信息及相关源码。本轮沿用 WESI 的 Python / pywebview，不引入远程服务或另一个前端框架。

| 参考 | 查阅内容 | 本轮采用范围 |
| --- | --- | --- |
| [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json) | MIT LICENSE、README、78 牌 JSON 及 m/c/s/w/p 图片命名 | WESI 原有牌库和图片命名与其一致；继续使用仓库现有 78 张牌面，本轮未下载新牌面 |
| [ekelen/tarot-api](https://github.com/ekelen/tarot-api) | static/card_data.json 的 meaning_up / meaning_rev / desc | 参考独立正逆位数据结构，未复制英文内容或部署 API；该仓库未发现独立许可证 |
| [dreamhunter2333/chatgpt-tarot-divination](https://github.com/dreamhunter2333/chatgpt-tarot-divination) | MIT、TarotPage.tsx、src/divination/tarot.py | 参考问题输入与结果查看的交互分工；不复制源码，不采用模型生成抽牌结果 |
| [daman-ovo-0404/tarot-skill](https://github.com/daman-ovo-0404/tarot-skill) | README 中六种牌阵、牌间关系与叙事结构介绍 | 仅参考功能方向；README 声明 MIT，未见独立许可证，不复制技能文件、解读文本或脚本 |
| [uxiaohan/Tarot-Web](https://github.com/uxiaohan/Tarot-Web) | README、App.vue、项目结构 | 仅调研，未发现明确许可证，不复用其代码或图片 |

新牌背、布局与动画由 WESI CSS 实现，中文正逆位文本由 WESI 编写。复用现有本地 Inter 字体，其 OFL 授权仍见 ui/vendor/INTER-LICENSE.txt。

## 现有牌面来源说明

原项目 `assets/tarot/` 的 m00、c01 等命名及尺寸与 tarot-json 一致，但原项目未提供逐图来源清单，不能仅凭一致命名证明每张图的来源。该上游提供 MIT 项目许可证，同时 README 对 RWS 原作提出独立的图片版权说明；代码许可证不等于所有扫描版本或重绘牌面的授权。本轮不替换图片、不宣称新取得图片授权。对外分发牌面前应补齐原项目图片来源记录；后续新牌面应使用可核实的来源与授权。

## 行为与边界

- 八种牌阵各自有牌位解释、预览与布局。程序均匀、不放回抽牌，并独立确定正逆位；问题不改变抽取结果。
- 本轮固定离线解读：核心牌义 + 牌位透镜 + 行动/反思提示，不声称对自由文本问题完成个性化理解，也不声称能够确定他人的想法或未来。
- 新历史保存完整阅读快照；旧历史保持原文。保存失败时保留之前的牌桌，用户可以检查历史再决定是否重试。
- 不改工资或游戏币，不引入 AI 密钥配置。经典 Tk 塔罗保留兼容；新功能从工资监控入口或 `--tarot` 使用。

## 第二轮：整组解读

`tarot_reading.py` 根据花色统计、正逆位概况、问题关键词和关键牌位对照生成可追溯的离线内容。每个关系说明引用实际牌名、牌位与方向；凯尔特十字对照核心/挑战、基础/目标、自己/环境、期待/发展。关键词分类公开标为规则，并非自由文本理解。

`tarot_ai.py` 可选调用 OpenAI 兼容服务，模型仅收到当前问题与固定牌面内容，输出总览、牌间关系、行动和核实问题。返回结构有类型、长度与数量验证，前端作为纯文本呈现。配置只读取环境变量，不暴露密钥、不记录原始服务错误；请求不接受重定向，避免将认证头转发到其他服务。

默认关闭，启用后仍需按钮触发与发送确认。AI 输出是生成式建议，可能有偏差；不改写原牌面和离线解读。保存成功后历史直接复用结果。桌面检查使用临时历史与本机模拟 HTTP 服务，不消耗真实服务额度。
