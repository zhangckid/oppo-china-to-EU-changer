# 第三方声明

[English](THIRD_PARTY_NOTICES.md) | 简体中文

本仓库原创源码和文档依照 [MIT License](LICENSE) 授权，文件另有说明的除外。本项目不包含固件、Recovery 镜像、安装包、手机应用、Android Platform Tools 或设备备份，也不重新授权这些内容。

转版流程引用以下独立维护的项目和来源：

- [X9 Ultra GBL Chainload App](https://github.com/koaaN/x9u-gbl-chainload-app)及其[v0.2.1 发布页](https://github.com/koaaN/x9u-gbl-chainload-app/releases/tag/v0.2.1)。
- [OrangeFox lighthouse 设备树](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox)及其[v1.1 发布页](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox/releases/tag/v1.1)。
- 通过[转换刷机包目录](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers)发布的 CN2EU 包；发布者摘要见[校验和页面](https://roms.danielspringer.at/index.php?view=checksums)。
- [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools)。

## Qualcomm OEM 元数据定位器

[`changer/policy.py`](changer/policy.py) 中的 Qualcomm OEM 元数据定位器改编自 [koaaN/arbextract](https://github.com/koaaN/arbextract)，并增加了有边界的 ELF64 解析和本案例确切的元数据约束。

- 上游版权：Copyright (c) 2026 Jonas Salo。
- 审查过的上游版本：[`320efd96ded606b6bbf9c0c9d04ceb35caba32a6`](https://github.com/koaaN/arbextract/tree/320efd96ded606b6bbf9c0c9d04ceb35caba32a6)。
- 许可：MIT；完整许可文本见 [`licenses/arbextract-MIT.txt`](licenses/arbextract-MIT.txt)，SHA-256 为 `6abf1960b4c8c83104e7a7c2dc2f2c0d187fd684a6681503f3e9480bad3235bd`。

本文工具自行实现 Android sparse 镜像结构解析；格式实现可参考 [AOSP libsparse 源码](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/)。本仓库不再分发 AOSP 源码。

以上外部项目独立维护，相关软件和二进制文件仍受各自条款约束。本仓库未复制固件、APK、Recovery 包或 Platform Tools 二进制。

OPPO、Find X9 Ultra、Android、Google、GBL 和 OrangeFox 名称及标识归各自所有者所有。本独立项目未获其认可或背书。
