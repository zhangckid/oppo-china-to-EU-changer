# Sources and provenance

English | [简体中文](SOURCES.zh-CN.md) | [Project home](../README.md)

The project combines a private historical device record, exact locally audited artifacts, and public instructions from community maintainers. It is independent work; none of the community pages below is an OPPO conversion service or a guarantee that a file remains suitable for another build.

| Source | What it supports | Scope and trust limits |
| --- | --- | --- |
| [XDA: PMA110/PMA120 CN-to-global ROM thread](https://xdaforums.com/t/rom-pma110-pma120-convert-cn-to-global.4799566/) | Community discussion of the Find X9 Ultra conversion | XDA is a community forum. Its first post and later replies can change; use the thread for context and current discussion, not as a checksum authority. The direct page returned HTTP 403 during this documentation review, so its current contents could not be independently read here. |
| [GBL Chainload App repository](https://github.com/koaaN/x9u-gbl-chainload-app) and [v0.2.1 release](https://github.com/koaaN/x9u-gbl-chainload-app/releases/tag/v0.2.1) | GBL app, supported project/kernel information, temporary-root flow, GBL installation and unlock instructions | Maintainer project/release source. The app is not the ROM converter and does not itself unlock the bootloader. Review the current release instructions before use. |
| [OrangeFox lighthouse device repository](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox) and [v1.1 release](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox/releases/tag/v1.1) | Device-specific Recovery IMG/ZIP and changes | Device maintainer source. This project pins the exact v1.1 artifacts for its recorded case; a different build needs a new review. |
| [CN2EU Convert Flashers directory](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers) and [publisher checksum page](https://roms.danielspringer.at/index.php?view=checksums) | Conversion package download and publisher checksum | Third-party archive and publisher record, not an official OPPO package. The CLI pins the exact `Recovery Flasher F9U CN2EU 16.0.9.403.zip` file; never substitute EU2CN or another build. |
| [Android Platform Tools release page](https://developer.android.com/tools/releases/platform-tools) | Official ADB and fastboot downloads | Google's host tools; the CLI checks for the reviewed 37.0.1 version. |
| [koaaN/arbextract](https://github.com/koaaN/arbextract) | Qualcomm OEM metadata location in `changer/policy.py` | MIT-licensed upstream locator adapted with bounded ELF64 parsing and exact reviewed metadata checks. The full license and revision are recorded in [Third-party notices](../THIRD_PARTY_NOTICES.md). |
| [AOSP libsparse source](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/) | Android sparse-image format reference | Format reference only; this repository does not redistribute AOSP source. |

The recorded hardware case used `PMA110`, project `25021`, kernel `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`, and the exact artifacts listed in [`changer/pins.json`](../changer/pins.json). The public `hardware.json` contains partition capacities, not a private device identity. Pins document artifact identity; they do not certify safety or compatibility beyond the recorded case.

Links and the XDA search result were reviewed on 2026-10-01. Because the XDA page itself blocked automated retrieval, check its current top post and maintainer release pages directly before acting. The project does not copy XDA instructions wholesale and does not treat forum reports as hardware validation of this CLI.
