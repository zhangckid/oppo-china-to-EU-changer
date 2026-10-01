# CLI 完整操作示例

[English](CLI.md) | 简体中文 | [项目主页](../README.zh-CN.md)

第一次使用请先读[入门页](START_HERE.zh-CN.md)。操作时对照[流程图](FLOW.zh-CN.md)与[画面说明](SCREENSHOTS.zh-CN.md)。完成离线准备后，用 `python3 change.py guide "$RUN_DIR" --language zh-CN` 读取中文阶段指引；默认语言为英文。它只读取日志，不替代设备核验，也不确认执行。

以下是唯一经过审查案例的完整命令流程。起点必须是全新原厂 CN403 `PMA110`（512 GB、项目号 `25021`、固定内核），不能是已经转欧的手机。程序可以向真实设备发送命令；完整流程尚未在实机运行，实机支持仍未验证。

CLI 需要 Linux 和 Python 3.11 或更新版本，仅使用 Python 标准库。Windows 与 macOS 主机不受支持，因为执行器使用 Linux 文件锁和 `/proc` 机制。设备操作需要 Google Platform Tools **37.0.1**。ROM、GBL APK、OrangeFox IMG 和 OrangeFox ZIP 不应放入公开源码树。CLI 根据固定大小和 SHA-256 识别输入，不检查本地文件名；建议保留发布者文件名，并从发布者/维护者来源核验下载文件。

开始前，请另行备份个人数据，手机电量至少 50%，主机有足够空间保存全部目标分区备份及额外 1 GiB，开启并授权 USB 调试，并且只连接这台手机。解锁与两次 Format Data 都会清除数据。分区备份不是个人数据备份。

## 1. 设置路径并检查主机工具

请换成你自己的真实路径和序列号。这些 Shell 变量只是为了便于阅读，并非设备默认值。

```sh
TOOLS="/absolute/path/to/platform-tools-37.0.1"
INPUTS="/absolute/path/to/verified-inputs"
RUN_DIR="runs/pma110-512g-cn403-to-eu403"
ANDROID_SERIAL="replace-with-the-targets-current-adb-serial"
```

检查主机二进制文件。此命令不会连接或读取手机：

```sh
python3 change.py doctor --platform-tools "$TOOLS"
```

结果中 `adb` 和 `fastboot` 均应为 `37.0.1`。一次运行中不要更换工具版本。

## 2. 核验输入并创建新运行目录

按本地路径提供经过审查的四个输入文件。输出目录必须尚不存在；运行目录是永久证据记录，不可覆盖。

```sh
python3 change.py prepare \
  --rom "$INPUTS/Recovery Flasher F9U CN2EU 16.0.9.403.zip" \
  --gbl-apk "$INPUTS/x9u-root-flasher-v0.2.1.apk" \
  --recovery-img "$INPUTS/OrangeFox-R12.0-Unofficial-lighthouse.img" \
  --recovery-zip "$INPUTS/OrangeFox-R12.0-Unofficial-lighthouse.zip" \
  --out "$RUN_DIR"
```

准备阶段完全离线：检查大小、SHA-256、确切 ZIP 清单和镜像大小，以及 sparse `super` 结构。可能需要几分钟，不会与手机通信。任何摘要不匹配都必须停止；不要修改固定摘要或换用未经审核的包来绕过校验。查看新运行状态：

```sh
python3 change.py status "$RUN_DIR"
python3 change.py run "$RUN_DIR"
```

第二条命令只预览，不连接手机。

## 3. 明确启动执行

在手机上确认当前运行的是预期原厂 CN403 Android。在主机运行 `"$TOOLS/adb" devices -l`，确认列表中恰好有这台已授权手机、没有其他设备，然后启动：

```sh
python3 change.py run "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-erase "$ANDROID_SERIAL"
```

命令会先核对设备身份、版本、项目号、内核、锁定状态和存储几何，再安装固定摘要的 GBL 应用。通常会以退出码 `3` 返回，阶段为 `waiting_gbl`；这表示已到下一个人工检查点。退出码含义及停止处理见[故障处理](TROUBLESHOOTING.zh-CN.md)。

## 4. 安装 GBL 并解锁

在 `waiting_gbl` 阶段，使用手机上安装的 GBL 应用：

1. 获取临时 Root，并在应用中执行 `FLASH`。
2. 等待 `FLASH_VERIFY_OK`（写入与读回核验成功）。
3. 在原厂 OPPO Recovery 中执行所需的 Format Data。
4. 重启后，在手机振动时立即按住音量上进入 GBL。这是实机观察到的 GBL 进入方式，不是通用冷启动快捷键。
5. 在主机使用只读命令 `"$TOOLS/fastboot" devices` 查看当前 GBL 序列号，并将 `GBL_SERIAL` 设为该值。它可能与 Android ADB 序列号不同。

```sh
GBL_SERIAL="replace-with-current-gbl-fastboot-serial"
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$GBL_SERIAL" --ack-stage waiting_gbl
```

CLI 会核对当前处于 GBL Bootloader fastboot，然后发送 OEM 解锁切换和 Bootloader 解锁请求。手机屏幕提示必须由用户亲自确认。请在手机上确认 Bootloader 解锁。保持 GBL 模式，使用同一个 GBL 序列号继续：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$GBL_SERIAL" --ack-stage waiting_unlock
```

CLI 核实已解锁后，将固定 OrangeFox IMG 写入 `recovery_a` 并请求重启 Recovery。下一阶段需使用原来的 `ANDROID_SERIAL`，不能再用 GBL 序列号。

## 5. Recovery、备份与 OrangeFox ZIP

进入 `waiting_recovery` 后，等待 OrangeFox Recovery ADB 可用。使用原 Android ADB 序列号恢复：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_recovery
```

CLI 核验 CN GPT/布局、受保护 GBL 部件、OrangeFox 身份、分区容量和电量；随后在更多刷写操作前，把指定固件分区及 GPT 备份到主机。该备份发生在安装 GBL、原厂 Format Data 和写入 Recovery IMG 之后；它不是出厂状态备份，也不包含 `userdata`。

进入 `waiting_ofox_sideload` 后，在 OrangeFox 界面开启 **ADB Sideload**，然后运行：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_ofox_sideload
```

等待 OrangeFox ZIP 完成并返回 Recovery。进入 `waiting_ofox_recovery` 后，使用同一序列号：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_ofox_recovery
```

允许转换包安装前，CLI 会核验全新 Recovery 启动、两个 OrangeFox 槽位、受保护 GBL 状态、容量和备份摘要、Recovery 队列中无旧脚本、自动重启已关闭，且固件文件系统未挂载；随后保存安装前 Recovery 日志。任一核验失败都应停止；详细处理见[故障处理](TROUBLESHOOTING.zh-CN.md)。

## 6. Sideload 并验证 CN2EU 安装器

进入 `waiting_rom_sideload` 后，在 OrangeFox 开启 ADB Sideload 并运行：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_rom_sideload
```

运行这个确切安装器时，按音量上继续，再按音量下选择 **ABL = NO**。绝不能选择 ABL = YES，否则不能保留预期的 GBL 引导链。保持 USB 连接，等待安装器本身完成。

在 `waiting_install_result` 阶段，确保手机处于普通 Recovery ADB，而非 sideload 模式，并且不要重启。然后运行：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_install_result
```

CLI 会对比安装前后的 Recovery 日志，要求出现新的 `Installation complete`，确认保留当前 ABL，没有安装错误，并且磁盘上的 GPT 符合预期。电脑端传输百分比或 ADB 进程成功退出都不足以证明安装成功。通过检查后，CLI 会请求启动全新的 Recovery。

进入 `waiting_fresh_recovery` 后，等待 Recovery 重启并继续：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_fresh_recovery
```

程序核验全新内核中的 EU GPT/布局和容量、每个记录固件目标的读回摘要，以及 sparse `super` 中所有已定义的 RAW/FILL 区域。DONT_CARE 区域不会被宣称已写入或读回。程序还会保存格式化前日志。

## 7. Format Data 并启动欧版 Android

进入 `waiting_format` 后，在 OrangeFox 手动执行 **Menu → Partitions management → Static partitions → Data → Format Data**，输入 `yes` 并等待完成。不要启动 System。然后在同一 Recovery 会话继续：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_format
```

工具要求新日志中 `/dev/block/sda15`（data）和 `/dev/block/sda10`（metadata）都存在格式化成功证据。随后它会请求再次重启 Recovery。进入 `waiting_formatted_recovery` 后，等待重启并运行：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_formatted_recovery
```

CLI 确认全新 Recovery/GPT 以及 `/data` 已挂载为 F2FS 后，请求首次启动 Android。完成 Android 初始化，开启 USB 调试并授权主机，然后在 `waiting_android` 阶段继续：

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_android
python3 change.py status "$RUN_DIR"
```

仅在核验欧版机型/版本/项目号/地区、解锁状态、预期槽位、系统已启动和初始化完成后，工具才会记录 `complete`。保持 Bootloader 解锁；后续欧版 OTA 属于单独流程。

## 任一阶段停止时

不要重复上一个命令，也不要未经审查就修改手机。读取确切状态与说明：

```sh
python3 change.py status "$RUN_DIR"
```

若阶段为 `review_required`，工具不会提供恢复、重置或强制继续命令。保留运行目录、手机当前画面/模式和可能已发生的部分写入。查看[故障处理](TROUBLESHOOTING.zh-CN.md)与[验证限制](VALIDATION.zh-CN.md)。运行目录含私有路径、序列号、Recovery 日志和备份，未经隐私审查不要公开。
