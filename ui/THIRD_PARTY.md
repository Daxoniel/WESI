# 工资界面使用的开源组件

| 项目 | 实际用途 | 固定版本 | 授权 |
| --- | --- | --- | --- |
| [NumberFlow](https://github.com/barvian/number-flow) | 金额滚动 Web Component，实际导入并调用 `update()` | 0.6.2 | MIT |
| [Lucide](https://github.com/lucide-icons/lucide) | 导航、隐私、置顶、设置及统计图标 | 1.53.0 | ISC，包含源图标的其他授权条款 |
| [Inter / Fontsource](https://github.com/fontsource/fontsource) | 本地可变字体（拉丁字符） | @fontsource-variable/inter 5.2.8 | OFL-1.1 |
| [esm-env](https://github.com/benmccann/esm-env) | NumberFlow 的环境依赖 | 见 package-lock.json | MIT |
| [Kenney UI Pack Pixel Adventure](https://kenney.nl/assets/ui-pack-pixel-adventure) | 到账成功的金币图片，复用原项目素材 | 原始 tile_0039.png | CC0（vendor/KENNEY-LICENSE.txt） |
| [pywebview](https://github.com/r0x0r/pywebview) | Python 与系统 WebView 桥接 | 6.2.1 | BSD-3-Clause |

JavaScript、字体及对应原始授权文本位于 `vendor/`，运行时完全本地加载。
pywebview 通过 Python 依赖安装，保留其上游授权。Qt/PySide6 是 Linux 下可选的系统界面后端，具有自身的 LGPL/GPL/商业授权条件，未打包进前端。

页面布局和工资数据桥接由 WESI 实现。[Salary Ticker](https://github.com/DEOKYOUNGKO/salary-ticker) 仅作为桌面交互参考，本次没有复制其源码或资源（未发现明确许可证）。

## 重建与验证

普通用户无需安装 Node.js；仓库包含前端运行文件。修改第三方组件时：

```bash
cd ui
npm ci
npm run build
npm test
```

测试首次运行可使用 `npx playwright install chromium` 安装浏览器，或用 `WESI_CHROMIUM_PATH` 指向现有 Chromium。
测试使用模拟桥接验证界面；`python tools/check_webview.py` 另行验证真实桌面 WebView 与 Python 数据。
构建脚本会从锁定依赖复制授权文件和字体，运行时不访问 CDN、远程字体或第三方图标服务。
