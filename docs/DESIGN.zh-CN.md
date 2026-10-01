# 设计与信任边界

[English](DESIGN.md) | 简体中文 | [项目主页](../README.zh-CN.md)

转版涉及下载文件、主机、Bootloader/Recovery 操作，以及必须在手机上确认的动作。CLI 将这些步骤组织为经过检查、并在人工作用处暂停的流程；它不会让社区转换包或固件本身变得安全。

## 工作阶段

`prepare` 检查本地输入并创建运行目录；`status` 显示已记录的阶段；不带执行标记的 `run` 只显示预览。执行模式使用指定 Platform Tools，并要求绑定序列号的清除数据确认。随后流程暂停并等待人工完成各阶段：

`waiting_gbl` → `waiting_unlock` → `waiting_recovery` → `waiting_ofox_sideload` → `waiting_ofox_recovery` → `waiting_rom_sideload` → `waiting_install_result` → `waiting_fresh_recovery` → `waiting_format` → `waiting_formatted_recovery` → `waiting_android` → `complete`。

`resume` 使用 `--ack-stage` 确认当前确切等待阶段，并在继续前检查观察到的设备状态。GBL 传输可能使用不同序列号；命令必须提供当时的序列号并明确确认 GBL 等待阶段。Recovery 和 Android 阶段仍绑定原始 ADB 序列号。流程会在转换前后分别保存 Recovery 日志，并拒绝使用过期的安装完成记录。手动 Format Data 后，需要检查全新的启动标识、成功的格式化结果，以及预期数据设备/文件系统，才允许进入 Android 阶段。

阶段名称表示所需检查点，不代表新工具已在实机验证。使用 `--execute` 时，此实现会向真实设备发送 ADB/fastboot 命令。执行流程尚未在实机验证；模拟测试不能证明镜像或命令对真实设备安全。`prepare`、`doctor`、预览与模拟测试均不能证明设备兼容。

## 实现模块索引

| 模块 | 职责与检查 |
| --- | --- |
| `changer/core.py` | 规范化 JSON 状态、原子替换并同步文件/目录、进程锁和流式摘要。运行记录摘要用于发现意外损坏或编辑；它不是身份认证，也不能证明本机操作者或恶意程序没有同时修改状态和摘要。 |
| `changer/artifacts.py` | 核对固定文件大小和 SHA-256，检查 ROM 成员及 sparse 镜像结构，并在传输期间持有已核验文件描述符，避免路径替换悄悄切换打开的输入文件。 |
| `changer/device.py` | 使用明确序列号运行有时限的 ADB/fastboot 子进程，限制捕获输出，并将超时、断连和非零结果视为错误。 |
| `changer/policy.py` | 应用精确的 PMA110 配置：机型/版本与锁状态检查、GPT 和分区身份/容量检查、引导链保护及固件元数据检查，以及全新 Recovery/格式化日志检查。 |
| `changer/runner.py` | 编排带运行记录的阶段流程、备份/读回检查、明确人工交接，以及中断后转为 `review_required`。不会强制继续、重置、重试不确定的写入或回滚。 |
| `changer/cli.py` | 提供 `prepare`、`status`、`run`、`resume` 和 `doctor`；默认预览，设备操作需要明确执行、序列号和清除数据确认，并用退出码表示等待或停止。 |
| `scripts/export_source.py` | 依据严格的仓库相对 `release-files.txt` 白名单生成可分享的源码包；不会收集运行数据或固件文件。 |

此模块索引描述代码路径，不代表实机成功运行的证据。检查可减少已知错误，但不能认证主机、二进制文件、连接的设备或社区固件。

| 阶段 | 设备/人工操作 | 程序继续前检查 |
| --- | --- | --- |
| `prepared` | 从全新、已锁定的 CN403 Android 开始；确认清除数据。 | Android 机型/版本/项目号/内核/锁状态与磁盘几何；之后安装固定摘要的 GBL APK。 |
| `waiting_gbl` | 在 GBL 应用中取得临时 Root，输入 `FLASH` 并确认验证成功，在原厂 Recovery 格式化数据，重启后于振动时按住音量上进入 GBL。 | 确认为 GBL Bootloader fastboot（不是 fastbootd）且仍锁定；之后请求 OEM 解锁与 Bootloader 解锁。屏幕确认仍由用户亲自完成。 |
| `waiting_unlock` | 在手机屏幕确认解锁，并保持在 GBL。 | 核对 GBL 已解锁；然后将固定 OrangeFox IMG 写入 `recovery_a` 并重启 Recovery。 |
| `waiting_recovery` | 等待 OrangeFox ADB。 | 核对 CN GPT/布局、预期槽位、受保护引导链摘要、Recovery 身份和至少 50% 电量；再于后续刷写前备份指定分区和 GPT。 |
| `waiting_ofox_sideload` | 在 OrangeFox 开启 ADB Sideload。 | Sideload 固定摘要的 OrangeFox ZIP。 |
| `waiting_ofox_recovery` | 等待 Recovery 返回。 | 核对全新 Recovery 启动 ID、双槽 OrangeFox 和保留的 GBL、分区容量、备份摘要、无过期队列脚本、自动重启关闭、固件文件系统未挂载；然后保存安装前 Recovery 日志。 |
| `waiting_rom_sideload` | 开启 ADB Sideload；在安装器界面按音量上继续，按音量下选择 ABL=NO。 | Sideload 确切 CN2EU ZIP。CLI 会提示此包专用按键，但仍需用户在手机上操作。 |
| `waiting_install_result` | 保持手机在 Recovery；如有需要退出 sideload，但不要重启。 | 拉取新的 Recovery 日志，要求有新的 `Installation complete`、确认保留 ABL 且无安装错误；检查磁盘上的 GPT，再请求启动全新的 Recovery。 |
| `waiting_fresh_recovery` | 等待 Recovery 重启。 | 核对新启动 ID、EU GPT/布局和分区容量、固件镜像及全部已定义 sparse `super` 区域摘要；然后保存格式化前日志。 |
| `waiting_format` | 在 OrangeFox 菜单中手动执行 Format Data 并输入 `yes`；不要启动 System。 | 要求新日志中 data（`sda15`）和 metadata（`sda10`）各有 `mkfs_f2fs` 成功记录；再请求再次启动 Recovery。 |
| `waiting_formatted_recovery` | 等待格式化后 Recovery 返回。 | 核对新启动 ID、EU Recovery/GPT 和以 F2FS 挂载的 `/data`；然后请求首次启动 Android。 |
| `waiting_android` | 完成初始化，开启 USB 调试并授权主机。 | 核对欧版机型/版本/项目号/地区、解锁状态、槽位、系统启动完成和初始化完成。 |
| `complete` | 保持 Bootloader 解锁。 | 最终记录完成；后续 OTA 使用单独审查过的更新工具。 |

`status` 会显示当前阶段的说明。若跳过阶段或证据不同，工具不会悄悄继续。模式、身份、布局、摘要、日志、超时或命令出现意外时，当前运行都会停止。退出码与证据保留方法见[故障处理](TROUBLESHOOTING.zh-CN.md)。

## 停止与恢复策略

工具只允许从已记录且符合预期的人工等待阶段恢复，并在继续前将其与连接设备状态核对。如果进程在执行操作时中断，会记录为 `review_required`。工具没有重置、强制继续、自动重试写入、自动回滚或自动越过不确定写入的功能。人工必须独立确认设备模式、已完成和不确定的操作、备份状态以及下一步安全操作。

每个破坏性阶段都需要明确人工确认。CLI 无法代替用户确认 Bootloader 解锁提示，也不会代替用户点击 OrangeFox 控件。Format Data 需手动完成。它不会为卸载 `/odm` 而停止触摸服务，不会处理 `adbd` 冲突，也不会擅自回答转换包提示。

## 文件与设备边界

主机检查本地文件身份并记录操作证据。设备检查的可信程度取决于传输链路及设备本身报告的准确性。安装器提示或传输百分比不能单独证明每个目标均正确写入。固件镜像和备份不进入源码发布包；日志可能泄露设备标识，分享前应检查并脱敏。

历史手动案例在安装 GBL、首次 Format Data 和 OrangeFox IMG 后单独备份了 121 个所选分区和六份 GPT。该备份不是出厂状态备份，也不含个人数据。不能将其与当前 CLI 的检查混为一谈。CLI 代码实现了 107 个分区及六份 GPT 的备份，以及对 100 个固件目标和 sparse `super` 中 290 个已定义 RAW/FILL 区域的读回摘要核验；19 个 DONT_CARE 区域内容未定义，不会从手机读取。这些备份或读回操作尚未由新 CLI 在实机执行；目前只通过模拟测试覆盖其行为。

## 安全前提

- 源手机与记录中的机型、容量、版本、项目号和内核完全一致。
- ROM、GBL APK、OrangeFox 文件来自所列发布者，并已独立核验。
- 操作者已单独备份个人数据，并理解解锁和格式化会清除数据。
- 能正确区分 GBL、Bootloader、OrangeFox 与 Android 模式。
- 用户亲自在设备上确认提示；画面或状态不同即停止。

任一前提不满足或未核实，都不要执行转版。
