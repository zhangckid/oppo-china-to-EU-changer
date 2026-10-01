# oppo china to EU changer

[English](README.md) | 简体中文

本项目整理 OPPO Find X9 Ultra（`PMA110`）从已记录的国行版本转为欧版 `CPH2841_16.0.9.403(EX01)` 的谨慎流程，并提供实验性的命令行工作流。**使用 `--execute` 时，CLI 会向真实设备发送命令；但完整流程尚未在手机上端到端验证。** 这份记录不能证明其他 OPPO 机型受支持。

实机记录对应一台 512 GB 的 `PMA110`，原版本为 `PMA110_16.0.9.403(CN01)`，项目号 `25021`，内核 `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`；使用社区转换包 `Recovery Flasher F9U CN2EU 16.0.9.403.zip` 转为 `CPH2841_16.0.9.403(EX01)`。首次安装约在 `super` 写入 50% 时中断，此前 GPT 已扩展并写入 100 个固件目标。操作者审计部分写入状态后才完整重跑安装包；手机随后进入系统初始化。该人工恢复并非本 CLI 自动完成，也不代表本工具通过实机验证。

## 范围与安全

首次转版会改变分区表并清除用户数据。流程需要在手机上确认解锁，并在 OrangeFox 中手动 Format Data。请另行备份个人数据。记录中的流程保留 GBL、EFISP 和 OrangeFox，保持 Bootloader 解锁；不代表 OPPO 官方支持。

CLI 将准备、状态查看、预览与明确确认后的执行分开。它只从全新的国行 Android 安装开始；没有接管已转欧设备的选项。执行模式必须显式指定 Platform Tools 目录，并将确认绑定到设备序列号和当前阶段：

```sh
python3 change.py prepare --rom PATH --gbl-apk PATH \
  --recovery-img PATH --recovery-zip PATH --out runs/convert
python3 change.py doctor --platform-tools PATH
python3 change.py status runs/convert
python3 change.py run runs/convert                 # 仅预览
python3 change.py run runs/convert --platform-tools PATH --execute \
  --serial ANDROID_SERIAL --ack-erase ANDROID_SERIAL
python3 change.py resume runs/convert --platform-tools PATH --execute \
  --serial CURRENT_SERIAL --ack-stage CURRENT_STATE
```

命令行与行为仍处于实验阶段，可能调整。`--execute` 会执行真实设备操作；预览和基于模拟设备的测试都不等于实机验证。程序只会在检查状态后从预期的人工等待阶段恢复；正在执行的操作中断后会进入 `review_required`。没有重置或强制继续选项。工具不会自动重试写入、格式化、停止系统服务或应用 `adbd` 变通操作。转换过程仍包含人工步骤。

## 文档

| 页面 | 内容 |
| --- | --- |
| [转版流程](docs/CONVERSION.zh-CN.md) | 精确的历史案例、工具、人工步骤与停止条件 |
| [CLI 分阶段操作](docs/CLI.zh-CN.md) | 每个阶段的完整命令与人工检查点 |
| [设计与限制](docs/DESIGN.zh-CN.md) | 工作流边界、预期阶段与信任限制 |
| [故障处理](docs/TROUBLESHOOTING.zh-CN.md) | 退出码、阶段处理与异常响应 |
| [来源与溯源](docs/SOURCES.zh-CN.md) | 维护者、发布者、XDA 与格式参考链接 |
| [验证记录](docs/VALIDATION.zh-CN.md) | 实机观察结果与尚未验证的部分 |
| [发布说明](docs/RELEASING.zh-CN.md) | 严格源码导出与可公开分享的文件 |

各页面均可切换中英文。后续 `CPH2841_16.0.10.500(EX01)` OTA 的审计流程见[国行转欧版 OTA updater](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater)。

## 外部组件

本项目不包含固件、GBL APK、OrangeFox 镜像或 ZIP、Android Platform Tools 或设备备份。请从维护者或发布者处获取，并在有发布摘要时核对。第三方声明和项目许可见 [THIRD_PARTY_NOTICES.zh-CN.md](THIRD_PARTY_NOTICES.zh-CN.md) 与 [LICENSE](LICENSE)。

## 免责声明

本项目为独立社区项目，与 OPPO、GBL、OrangeFox 或 Google 无官方关系。转版可能导致设备无法使用并永久清除数据。请严格遵循对应设备和版本的上游说明；任何提示、镜像、分区布局或校验结果与记录不一致时都应停止。
