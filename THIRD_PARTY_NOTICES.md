# Third-party notices

English | [简体中文](THIRD_PARTY_NOTICES.zh-CN.md)

Original source code and documentation in this repository are offered under the [MIT License](LICENSE), except where a file states otherwise. No firmware, recovery image, installer package, mobile application, Android Platform Tools, or device backup is included or relicensed by this project.

The conversion workflow refers to these independently maintained projects and sources:

- [X9 Ultra GBL Chainload App](https://github.com/koaaN/x9u-gbl-chainload-app) and its [v0.2.1 release](https://github.com/koaaN/x9u-gbl-chainload-app/releases/tag/v0.2.1).
- [OrangeFox lighthouse device tree](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox) and its [v1.1 release](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox/releases/tag/v1.1).
- The CN2EU conversion package distributed via [Convert Flashers](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers), with publisher hashes at the [checksum page](https://roms.danielspringer.at/index.php?view=checksums).
- [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools).

## Qualcomm OEM metadata locator

The Qualcomm OEM metadata locator in [`changer/policy.py`](changer/policy.py) is adapted from [koaaN/arbextract](https://github.com/koaaN/arbextract), with bounded ELF64 parsing and the exact reviewed metadata constraints added.

- Upstream copyright: Copyright (c) 2026 Jonas Salo.
- Reviewed upstream revision: [`320efd96ded606b6bbf9c0c9d04ceb35caba32a6`](https://github.com/koaaN/arbextract/tree/320efd96ded606b6bbf9c0c9d04ceb35caba32a6).
- License: MIT; the complete license text is in [`licenses/arbextract-MIT.txt`](licenses/arbextract-MIT.txt), SHA-256 `6abf1960b4c8c83104e7a7c2dc2f2c0d187fd684a6681503f3e9480bad3235bd`.

Android sparse-image structure is implemented for this tool; consult the [AOSP libsparse source](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/) for the upstream format implementation. No AOSP source is redistributed here.

The external projects listed above remain separately maintained. Their software and binary artifacts retain their respective terms. No firmware, APK, Recovery package, or Platform Tools binary is copied into this repository.

OPPO, Find X9 Ultra, Android, Google, GBL, and OrangeFox names and marks belong to their respective owners. This independent project is not endorsed by them.

## Images and authorship

`docs/images/ota-download-failed.png` was captured by Zhang Chen on the reference device and is included unchanged. Depicted OPPO/ColorOS/Android UI and marks remain their owners' property; this project's MIT license does not relicense those third-party visual elements. The `guide-en` and `guide-zh-CN` HTML/PNG files are this project's typeset actual CLI output, not phone-flashing screenshots.

The pinned CN2EU package's `META-INF/com/google/android/update-binary` credits `by koaaN`; Daniel Springer ROM Archive provides distribution and checksums. Those roles are recorded separately, and the upstream installer is not claimed as this project's original work. Zhang Chen is the project author, assisted by Codex. See [Sources, prior work and acknowledgments](docs/SOURCES.md) for the full contribution and reference table.
