# 来源、前人贡献与致谢

[English](SOURCES.md) | 简体中文 | [项目主页](../README.zh-CN.md)

本项目结合了私有历史设备记录、经过本地审计的确切文件，以及社区维护者公开说明。项目独立维护；下列社区页面均不是 OPPO 转版服务，也不保证某个文件适用于其他版本。

## 贡献归属

| 作者、维护者或社区 | 已有工作及本项目如何使用 |
| --- | --- |
| **koaaN** | [GBL Chainload App](https://github.com/koaaN/x9u-gbl-chainload-app) 的作者及 [lighthouse OrangeFox 设备适配](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox)维护者。固定 CN2EU ZIP 内的安装脚本也署名 `by koaaN`；本项目调用该安装器，不自行发明转版包的 GPT/固件写入算法。 |
| **Jonas Salo / koaaN，arbextract** | Qualcomm OEM 元数据定位逻辑来源；本项目改编到 `changer/policy.py`。版权姓名来自上游 MIT 许可，完整许可与固定 revision 见[第三方声明](../THIRD_PARTY_NOTICES.zh-CN.md)。 |
| **OrangeFox Recovery 团队** | [OrangeFox Recovery](https://orangefox.download/) 项目；本流程使用 koaaN 的设备专用非官方构建，不将其称为 OrangeFox 官方支持的 X9U 版本。 |
| **Daniel Springer ROM Archive** | [转换包归档、分发及校验和](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers)来源。分发者与安装脚本作者分开标注；归档站点并不因此拥有全部固件的作者身份。 |
| **Google / Android Open Source Project** | ADB/fastboot 主机工具与 sparse 格式参考。本仓库不包含其二进制；sparse 解析器为本项目实现。 |
| **XDA 原帖作者与回复贡献者** | 转版经验交流、问题反馈与背景讨论。由于当前页面返回 403，本次无法核实首帖作者姓名或逐条贡献，不猜测署名。请以原帖为准；相关经验并非本项目首次发现。 |
| **Zhang Chen** | 本项目维护者、实机操作者与体验报告提供者；整理本地实验记录，定义检查、备份、状态机及公开发布范围。 |
| **OpenAI Codex（AI 协助）** | 协助日志分析、代码实现、异常检查、模拟测试与双语文档整理。AI 协助不构成硬件验证、上游背书或安全认证；上游工作的归属保持不变。 |

### 转换包作者证据

本地审计的 `Recovery Flasher F9U CN2EU 16.0.9.403.zip`，SHA-256 为 `74c9754740c2587b20cd1b59a665436a62887ff078f6d7b4e79feb07973bf626`。其中 `META-INF/com/google/android/update-binary` 第 506 行显示作者标记 `by koaaN`。这是**该确切安装脚本**的署名证据，不是所有内含 OPPO 固件、依赖或 GBL 组件的作者证明。本仓库不复制该安装脚本或固件；下载路径见下表。

本项目贡献的是外围工作流与检查：固定输入审计、可持久化阶段记录、显式人工交接、指定分区备份、写后回读检查、只读中英文指引以及双语文档。Bootloader 访问能力、Recovery 与转换安装器均依赖上述前人工作。

## 引用文档与用途

| 来源 | 支持的内容 | 范围与信任限制 |
| --- | --- | --- |
| [XDA：PMA110/PMA120 国行转全球 ROM 讨论帖](https://xdaforums.com/t/rom-pma110-pma120-convert-cn-to-global.4799566/) | Find X9 Ultra 转版社区讨论 | XDA 是社区论坛。首帖与后续回复可能变化；可用于了解讨论和当前动态，不能作为校验和权威来源。本次文档审阅时直接访问页面返回 HTTP 403，因此无法在此独立读取当前页面内容。 |
| [GBL Chainload App 仓库](https://github.com/koaaN/x9u-gbl-chainload-app)及[v0.2.1 发布页](https://github.com/koaaN/x9u-gbl-chainload-app/releases/tag/v0.2.1) | GBL 应用、支持的项目号/内核、临时 Root、GBL 安装与解锁说明 | 维护者仓库与发布页。此应用不是 ROM 转换器，也不会自行解锁 Bootloader。操作前应阅读当前版本说明。 |
| [OrangeFox lighthouse 设备仓库](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox)及[v1.1 发布页](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox/releases/tag/v1.1) | 设备专用 Recovery IMG/ZIP 与版本变化 | 设备维护者来源。本项目为记录案例固定到 v1.1；其他版本需重新评估。 |
| [CN2EU 转换包目录](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers)及[发布者校验和页面](https://roms.danielspringer.at/index.php?view=checksums) | 转换包下载与发布者校验和 | 第三方归档与发布者记录，不是 OPPO 官方软件。CLI 固定校验确切文件 `Recovery Flasher F9U CN2EU 16.0.9.403.zip`；不要替换为 EU2CN 或其他版本。 |
| [Android Platform Tools 发布页](https://developer.android.com/tools/releases/platform-tools) | 官方 ADB 与 fastboot 下载 | Google 主机工具；CLI 检查经过评审的 37.0.1 版本。 |
| [koaaN/arbextract](https://github.com/koaaN/arbextract) | `changer/policy.py` 中 Qualcomm OEM 元数据定位 | MIT 许可的上游定位逻辑，增加了有边界的 ELF64 解析和本案例元数据检查。完整许可与版本记录见[第三方声明](../THIRD_PARTY_NOTICES.zh-CN.md)。 |
| [AOSP libsparse 源码](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/) | Android sparse 镜像格式参考 | 仅作格式参考；本仓库不再分发 AOSP 源码。 |
| [Mermaid 文档](https://mermaid.js.org/config/usage.html) | 图表渲染工具参考；流程内容由本项目编写 | Markdown 中的 Mermaid 是源图，随附 SVG 由 Mermaid 12 渲染；图表不构成实机证据，仓库不包含 Mermaid 运行库。 |

实机案例使用 `PMA110`、项目号 `25021`、内核 `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`，以及 [`changer/pins.json`](../changer/pins.json) 中列出的确切文件。公开的 `hardware.json` 只包含分区容量，不含私有设备身份。固定摘要只用于标识文件，不能证明其在案例以外的安全性或兼容性。

链接与 XDA 搜索结果于 2026-10-01 核对。由于 XDA 页面阻止自动读取，操作前请直接检查当前首帖与维护者发布页。本项目不会整段照搬 XDA 指引，也不把论坛报告视为本 CLI 的实机验证。

## 后续 OTA 项目

[oppo china to EU OTA updater](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater)（[中文文档](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater/blob/main/README.zh-CN.md)）是 Zhang Chen 维护、Codex 协助的后续升级项目。它记录同一设备从 EU403 手工升级到 EU500 的经验；当前自动化有自身的 EU500 基线和本地 profile 要求。它不是初次 CN2EU 安装器，也不能作为本转换 CLI 已通过实机验证的证据。

引用不是重新授权：外部文档、图片、固件与工具仍受原作者条款约束。除已注明的 arbextract 代码改编外，公开文档以链接和本项目的说明为主；缺少可核实许可时不假设允许重新分发二进制或复制整篇教程。
