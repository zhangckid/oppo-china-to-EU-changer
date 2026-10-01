# Recorded China-to-EU conversion

English | [简体中文](CONVERSION.zh-CN.md) | [Project home](../README.md)

This document describes one historical conversion of an OPPO Find X9 Ultra from `PMA110_16.0.9.403(CN01)` to `CPH2841_16.0.9.403(EX01)`. It is a record, not a universal guide or an endorsement of conversion. GBL, OrangeFox, and the CN2EU package are community-maintained. Check their current instructions and compatibility before doing anything to a device.

For community discussion see the [XDA PMA110/PMA120 CN-to-global thread](https://xdaforums.com/t/rom-pma110-pma120-convert-cn-to-global.4799566/). Forum posts can change and are not package checksum authorities; provenance and link-access limits are documented in [Sources](SOURCES.md).

## Exact recorded case

- Device: `PMA110`, 512 GB, project `25021`.
- Source build: `PMA110_16.0.9.403(CN01)`.
- Kernel: `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`.
- Target build: `CPH2841_16.0.9.403(EX01)`.
- Conversion package: `Recovery Flasher F9U CN2EU 16.0.9.403.zip`.
- GBL Chainload App: v0.2.1.
- Recovery: OrangeFox R12.0 Unofficial `lighthouse`, v1.1.

These identifiers form one tested historical combination. A matching model name alone is insufficient. This project does not claim support for other storage sizes, source builds, kernels, project IDs, or OPPO models.

## Obtain and verify the tools

Use the publisher or maintainer page to obtain the files. Do not use copies bundled with this repository; no conversion binaries are distributed here.

| Item | Recorded version and source |
| --- | --- |
| GBL Chainload App | [v0.2.1 release](https://github.com/koaaN/x9u-gbl-chainload-app/releases/tag/v0.2.1) and [maintainer instructions](https://github.com/koaaN/x9u-gbl-chainload-app) |
| OrangeFox Recovery | [lighthouse device repository](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox) and [v1.1 release](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox/releases/tag/v1.1) |
| CN2EU package | [Convert Flashers directory](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers) and [publisher checksums](https://roms.danielspringer.at/index.php?view=checksums) |
| ADB and fastboot | [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) |

The CLI checks these exact artifacts by size and SHA-256 (size in bytes); the basename is not an input to verification. Prefer keeping the publisher's original file name so it is easy to identify.

| Local name | Size | SHA-256 |
| --- | ---: | --- |
| `Recovery Flasher F9U CN2EU 16.0.9.403.zip` | 13,346,334,129 | `74c9754740c2587b20cd1b59a665436a62887ff078f6d7b4e79feb07973bf626` |
| `x9u-root-flasher-v0.2.1.apk` | 838,528 | `3d9c6e74cb63c5472e377690d76ae2a960b009d0cc7ed2ccb9d909edf01da46d` |
| `OrangeFox-R12.0-Unofficial-lighthouse.img` | 104,857,600 | `369fb7ef9ec2e69dd884409f3eec5349ceba8dd98e6e460f5d6871cf7246eaa4` |
| `OrangeFox-R12.0-Unofficial-lighthouse.zip` | 59,925,692 | `21f1abaf07492bcd3a8d962de10e24899fc6db3e3c146cdfbeb38231298c792d2` |

Select the CN2EU package, not the reverse EU2CN package. The recorded ZIP was `Recovery Flasher F9U CN2EU 16.0.9.403.zip`; its publisher-listed SHA256 is `74c9754740c2587b20cd1b59a665436a62887ff078f6d7b4e79feb07973bf626`. This digest identifies only that exact archive. Recheck the current publisher list and the actual downloaded file.

## Historical sequence

The following sequence records what was done in the reference case. It may omit details required by a current release of any external tool; follow that project's instructions if they differ. Initial conversion erases data and rewrites the partition layout.

1. Back up personal data separately and verify every downloaded file. Confirm that the source build and kernel exactly match a combination accepted by the GBL and OrangeFox maintainers.
2. Use the GBL app's temporary-root and `FLASH` workflow to install GBL. Wait for its explicit successful write/readback result (`FLASH_VERIFY_OK` in the recorded flow), then complete the stock Recovery **Format Data** step required by its instructions. Installation of the app does not itself unlock the bootloader.
3. Enter GBL using the observed procedure: after reboot, hold Volume Up as soon as the phone vibrates. Do not generalize this to a cold-boot key combination.
4. The recorded unlock commands were `fastboot oem oem-unlock-toggle`, followed by `fastboot flashing unlock`. Confirm the unlock on the phone screen. Unlocking erases user data. Stop if the displayed prompt or device state differs.
5. Install the matching OrangeFox IMG to `recovery_a` from fastboot, then boot into Recovery and install the matching OrangeFox ZIP for both slots. In the recorded case, a partition and GPT backup was made after GBL installation, the first data format, and the Recovery IMG write, but before the OrangeFox ZIP and CN2EU conversion. It was not a pristine factory boot-chain backup and did not include personal data.
6. In OrangeFox, disable automatic reboot and sideload the CN2EU ZIP from a computer using ADB or from USB OTG. Do not stage it in internal storage: this installer changes the userdata boundary. For this package, choose Volume Up to continue and Volume Down for **ABL = NO**, preserving GBL. Treat every installer prompt as package-specific.
7. Wait for the installer's `Installation complete` result, save its full log, and verify GPT, `super`, GBL/ABL, and OrangeFox. A host-side transfer percentage is not proof that the device installer finished. Reboot to a fresh Recovery session for checks.
8. In OrangeFox, manually format data using **Menu → Partitions management → Static partitions → Data → Format Data**, enter `yes`, and confirm completion. A normal wipe is not equivalent. This operation erases data.
9. Boot System, finish initial setup, and verify the displayed and ADB-reported EU identity, including `CPH2841`, `CPH2841EEA`, and the intended build.

The retained boot chain in this case was GBL/ABL content, EFISP, and OrangeFox in both recovery slots. The bootloader remained unlocked. **Do not relock it** as part of this workflow.

## Interrupted attempt and recovery record

The initial installer attempt was manually interrupted at roughly 50% of the `super` write. By then the installer had resized GPT and written 100 firmware targets; `super` was only partly written. The phone was not booted. The operator first audited the phone, GPT, retained boot-chain partitions, installer/helper process state, and Recovery state, then ran the complete conversion ZIP again from that reviewed state. The full package completed and the phone reached Android setup. This was a human-reviewed decision for that exact device and log set; it is not an automated recovery recipe.

The new CLI is not a replay of that manual recovery. With `--execute`, it issues real device commands, but it has not been run against a phone. It does not recover a partially flashed phone or decide that re-running a full package is safe. Its policy is to stop when write completion is uncertain. Do not infer from the manual case that an interrupted tool run can safely be resumed or repeated. A human must inspect the device, logs, completed and uncertain writes, and backups before deciding what to do.

The historical operator also encountered a mounted `/odm` filesystem held by a touch service and an ADB daemon conflict. Both were investigated and handled manually for that session. The CLI has no automatic service-kill or `adbd` workaround. These details are not a recipe to stop services on another phone.

## Stop conditions

Stop and seek device-specific review if the model, storage, build, kernel, prompts, installer version, GPT/partition layout, target image, or checksums differ. Also stop if a flash or readback result is missing or uncertain, a device disconnects during a write, or the Recovery/fastboot mode is not the expected one. Do not substitute `fastbootd` and bootloader fastboot for one another; OrangeFox's userspace fastboot mode and GBL are separate environments.

Never treat these steps as a universal OPPO procedure. No firmware, recovery image, APK, conversion ZIP, or backup is included in this repository.
