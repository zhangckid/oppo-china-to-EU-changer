# 已记录的国行转欧版流程

[English](CONVERSION.md) | 简体中文 | [项目主页](../README.zh-CN.md)

配套阅读：[流程图与分区变化](FLOW.zh-CN.md) · [截图与画面对照](SCREENSHOTS.zh-CN.md) · [机主体验与限制](COMPATIBILITY.zh-CN.md)。本流程纯属技术探索，真实操作需要知识背景与 AI 辅助核查；详见[入门前提](START_HERE.zh-CN.md)。上游工具、转换脚本作者和文档引用均列于[来源与致谢](SOURCES.zh-CN.md)。

本文记录一台 OPPO Find X9 Ultra 从 `PMA110_16.0.9.403(CN01)` 转为 `CPH2841_16.0.9.403(EX01)` 的历史案例。它是案例记录，不是通用教程，也不代表本项目认可所有转版操作。GBL、OrangeFox 和 CN2EU 包均由社区维护；操作前请核对其当前说明和兼容性。

社区讨论见 [XDA PMA110/PMA120 国行转全球帖](https://xdaforums.com/t/rom-pma110-pma120-convert-cn-to-global.4799566/)。论坛内容可能变化，不能作为软件包校验和权威来源；链接溯源与访问限制见[来源与溯源](SOURCES.zh-CN.md)。

## 本案例的精确设备组合

- 设备：`PMA110`，512 GB，项目号 `25021`。
- 源版本：`PMA110_16.0.9.403(CN01)`。
- 内核：`6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`。
- 目标版本：`CPH2841_16.0.9.403(EX01)`。
- 转换包：`Recovery Flasher F9U CN2EU 16.0.9.403.zip`。
- GBL Chainload App：v0.2.1。
- Recovery：OrangeFox R12.0 Unofficial `lighthouse`，v1.1。

这些标识描述的是一个有历史实机记录的组合。仅机型名称相同并不足以说明兼容。本项目不声称支持其他容量、源版本、内核、项目号或 OPPO 机型。

## 获取并核验工具

请从发布者或维护者页面获取文件。本仓库不分发转换所需二进制文件。

| 项目 | 记录版本和来源 |
| --- | --- |
| GBL Chainload App | [v0.2.1 发布页](https://github.com/koaaN/x9u-gbl-chainload-app/releases/tag/v0.2.1)及[维护者说明](https://github.com/koaaN/x9u-gbl-chainload-app) |
| OrangeFox Recovery | [lighthouse 设备仓库](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox)及[v1.1 发布页](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox/releases/tag/v1.1) |
| CN2EU 包 | [Convert Flashers 目录](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers)及[发布者校验和](https://roms.danielspringer.at/index.php?view=checksums) |
| ADB 与 fastboot | [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) |

CLI 根据大小和 SHA-256 校验以下确切文件（大小单位为字节）；本地文件名不参与校验。建议保留发布者原文件名，便于识别。

| 本地文件名 | 大小 | SHA-256 |
| --- | ---: | --- |
| `Recovery Flasher F9U CN2EU 16.0.9.403.zip` | 13,346,334,129 | `74c9754740c2587b20cd1b59a665436a62887ff078f6d7b4e79feb07973bf626` |
| `x9u-root-flasher-v0.2.1.apk` | 838,528 | `3d9c6e74cb63c5472e377690d76ae2a960b009d0cc7ed2ccb9d909edf01da46d` |
| `OrangeFox-R12.0-Unofficial-lighthouse.img` | 104,857,600 | `369fb7ef9ec2e69dd884409f3eec5349ceba8dd98e6e460f5d6871cf7246eaa4` |
| `OrangeFox-R12.0-Unofficial-lighthouse.zip` | 59,925,692 | `21f1abaf07492bcd3a8d962de10e24899fc6db3e3c146cdfbeb38231298c792d` |

选择 CN2EU 包，不要误选方向相反的 EU2CN 包。实机记录使用 `Recovery Flasher F9U CN2EU 16.0.9.403.zip`，发布者列出的 SHA256 为 `74c9754740c2587b20cd1b59a665436a62887ff078f6d7b4e79feb07973bf626`。该摘要只标识这个确切压缩包；操作前仍须检查发布者的最新清单和实际下载文件。

## 历史操作顺序

以下是该实机案例的操作记录，不保证覆盖外部工具当前版本所需的全部步骤；若上游说明不同，应遵循上游说明。首次转版会清除数据并重写分区布局。

1. 单独备份个人数据并核对所有下载文件。确认源版本和内核与 GBL、OrangeFox 维护者认可的组合完全一致。
2. 按 GBL 应用说明完成临时 Root 和 `FLASH` 流程安装 GBL。等待明确的写入/读回成功结果（本案例为 `FLASH_VERIFY_OK`），然后按其说明在原厂 Recovery 完成 **Format Data**。安装应用本身不会解锁 Bootloader。
3. 按实机观察到的方法进入 GBL：重启后，在手机振动时立即按住音量上键。不要将其概括成冷启动按键组合。
4. 本次记录的解锁命令为 `fastboot oem oem-unlock-toggle`，然后执行 `fastboot flashing unlock`。在手机屏幕上确认解锁。解锁会清除用户数据。屏幕提示或设备状态不同时立即停止。
5. 从 fastboot 将对应 OrangeFox IMG 写入 `recovery_a`，再启动 Recovery 并安装对应 ZIP 到两个槽位。核对写入结果。本案例在安装 GBL、首次格式化数据、写入 Recovery IMG 后，安装 OrangeFox ZIP 与 CN2EU 包前备份了分区和 GPT。该备份不是原厂引导链的原始备份，也不含个人数据。
6. 在 OrangeFox 中关闭自动重启，通过电脑 ADB sideload 或 USB OTG 安装 CN2EU ZIP。不要将包放入内部存储：安装器会改变 userdata 边界。此包的提示中，音量上为继续，音量下对应 **ABL = NO**，以保留 GBL。所有提示均应以当前包为准。
7. 等待安装器报告 `Installation complete`，保存完整日志，并核对 GPT、`super`、GBL/ABL 和 OrangeFox。电脑端传输进度不能证明设备端安装完成。重启至全新 Recovery 会话后再检查。
8. 在 OrangeFox 中手动执行 **Menu → Partitions management → Static partitions → Data → Format Data**，输入 `yes` 并确认完成。普通清除数据不等价；此操作会清除数据。
9. 启动 System，完成首次设置，并核对系统显示与 ADB 读取到的欧版身份，包括 `CPH2841`、`CPH2841EEA` 和目标版本。

本案例保留了 GBL/ABL 内容、EFISP 以及两个 Recovery 槽位的 OrangeFox。Bootloader 继续保持解锁。**不要在此流程中重新上锁。**

## 中断尝试与恢复记录

首次安装器尝试在 `super` 写入约 50% 时被人工中断。此时安装器已扩展 GPT 并写入 100 个固件目标，但 `super` 只写入了一部分。手机没有启动。操作者先审计手机、GPT、保留的引导链分区、安装器/辅助进程和 Recovery 状态，之后才从经过审查的状态完整重新运行整个转换 ZIP。完整安装随后成功，手机进入 Android 初始化界面。这是针对该台手机及其确切日志，由人工审查后做出的决定，不是自动恢复方案。

新 CLI 不是这次人工恢复过程的复刻。使用 `--execute` 时，它会向真实设备发送命令，但尚未在手机上运行。它不会恢复已部分刷写的手机，也不会判断重新运行完整包是否安全。其策略是在写入结果不确定时停止。不能据此推断工具运行中断后可安全续跑或重试。人工必须先检查设备、日志、已完成和不确定的写入以及备份，再决定后续操作。

历史操作中还遇到触摸服务占用 `/odm` 导致无法卸载，以及 ADB daemon 冲突。操作者针对当时会话进行了调查和人工处理。CLI 不会自动停止服务或应用 `adbd` 变通操作；这些记录不是在其他手机上停止服务的操作指南。

## 停止条件

机型、容量、版本、内核、提示、安装器版本、GPT/分区布局、目标镜像或校验和有任何差异时，都应停止并寻求针对设备的复核。写入或读回结果缺失或不确定、写入期间设备断开，或 Recovery/fastboot 模式不符合预期时也应停止。不要混淆 `fastbootd` 与 Bootloader fastboot；OrangeFox 用户空间 fastboot、Bootloader 和 GBL 是不同环境。

这些步骤不是适用于所有 OPPO 设备的通用流程。本仓库不包含固件、Recovery 镜像、APK、转换 ZIP 或设备备份。
