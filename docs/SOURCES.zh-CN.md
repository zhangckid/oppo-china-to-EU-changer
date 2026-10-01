# 来源与溯源

[English](SOURCES.md) | 简体中文 | [项目主页](../README.zh-CN.md)

本项目结合了私有历史设备记录、经过本地审计的确切文件，以及社区维护者公开说明。项目独立维护；下列社区页面均不是 OPPO 转版服务，也不保证某个文件适用于其他版本。

| 来源 | 支持的内容 | 范围与信任限制 |
| --- | --- | --- |
| [XDA：PMA110/PMA120 国行转全球 ROM 讨论帖](https://xdaforums.com/t/rom-pma110-pma120-convert-cn-to-global.4799566/) | Find X9 Ultra 转版社区讨论 | XDA 是社区论坛。首帖与后续回复可能变化；可用于了解讨论和当前动态，不能作为校验和权威来源。本次文档审阅时直接访问页面返回 HTTP 403，因此无法在此独立读取当前页面内容。 |
| [GBL Chainload App 仓库](https://github.com/koaaN/x9u-gbl-chainload-app)及[v0.2.1 发布页](https://github.com/koaaN/x9u-gbl-chainload-app/releases/tag/v0.2.1) | GBL 应用、支持的项目号/内核、临时 Root、GBL 安装与解锁说明 | 维护者仓库与发布页。此应用不是 ROM 转换器，也不会自行解锁 Bootloader。操作前应阅读当前版本说明。 |
| [OrangeFox lighthouse 设备仓库](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox)及[v1.1 发布页](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox/releases/tag/v1.1) | 设备专用 Recovery IMG/ZIP 与版本变化 | 设备维护者来源。本项目为记录案例固定到 v1.1；其他版本需重新评估。 |
| [CN2EU 转换包目录](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers)及[发布者校验和页面](https://roms.danielspringer.at/index.php?view=checksums) | 转换包下载与发布者校验和 | 第三方归档与发布者记录，不是 OPPO 官方软件。CLI 固定校验确切文件 `Recovery Flasher F9U CN2EU 16.0.9.403.zip`；不要替换为 EU2CN 或其他版本。 |
| [Android Platform Tools 发布页](https://developer.android.com/tools/releases/platform-tools) | 官方 ADB 与 fastboot 下载 | Google 主机工具；CLI 检查经过评审的 37.0.1 版本。 |
| [koaaN/arbextract](https://github.com/koaaN/arbextract) | `changer/policy.py` 中 Qualcomm OEM 元数据定位 | MIT 许可的上游定位逻辑，增加了有边界的 ELF64 解析和本案例元数据检查。完整许可与版本记录见[第三方声明](../THIRD_PARTY_NOTICES.zh-CN.md)。 |
| [AOSP libsparse 源码](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/) | Android sparse 镜像格式参考 | 仅作格式参考；本仓库不再分发 AOSP 源码。 |

实机案例使用 `PMA110`、项目号 `25021`、内核 `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`，以及 [`changer/pins.json`](../changer/pins.json) 中列出的确切文件。公开的 `hardware.json` 只包含分区容量，不含私有设备身份。固定摘要只用于标识文件，不能证明其在案例以外的安全性或兼容性。

链接与 XDA 搜索结果于 2026-10-01 核对。由于 XDA 页面阻止自动读取，操作前请直接检查当前首帖与维护者发布页。本项目不会整段照搬 XDA 指引，也不把论坛报告视为本 CLI 的实机验证。
