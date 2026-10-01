# Validation record

English | [简体中文](VALIDATION.zh-CN.md) | [Project home](../README.md)

This record separates the historical phone conversion from validation of the new CLI. They are different evidence.

## Historical hardware evidence

One OPPO Find X9 Ultra `PMA110` with 512 GB, project `25021`, source `PMA110_16.0.9.403(CN01)`, and kernel `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k` was manually converted to `CPH2841_16.0.9.403(EX01)` using the specified CN2EU package. The first installer attempt was manually stopped at roughly 50% of the `super` write, after GPT resize and 100 firmware-target writes; `super` was partial. The operator did not boot the phone. After auditing the device, GPT, processes, logs, and retained boot-chain partitions, the complete ZIP was run again; the phone reached Android setup. This was a manual decision based on that exact case and is not an automated recovery precedent.

The recorded checks included successful installer completion; GPT/layout and `super` geometry checks; verification that GBL/ABL, EFISP, and both OrangeFox recovery slots remained; and a fresh Recovery session before Format Data. The device later booted into EU Android setup. This evidence applies only to the recorded device and exact inputs. It does not establish that every function works, that OPPO supports the conversion, or that a future build will be compatible.

## New CLI status

The new tool has **not been used to flash a phone**. The exact pinned ROM, GBL APK, OrangeFox IMG and ZIP were checked offline; the 13,346,334,129-byte ROM contained 64 ZIP entries and 53 image members, of which 50 are selected firmware images. The sparse `super` image expands to 20,451,426,304 bytes and has 309 chunks: 290 defined RAW/FILL extents with hashes, plus 19 DONT_CARE extents whose contents are undefined. The checker does not read those 19 ranges from the phone or claim that they match a specific byte pattern. Offline preparation completed without device access or USB commands.

The CLI can issue real ADB/fastboot commands when `--execute` is supplied, but validation of device behavior so far is through mock-backed unit tests only. Tests exercise parsers, stage checks, fake transports, failures, interruption handling, and release export. They cannot prove that hardware responses, Recovery UI steps, or image writes behave as expected on a physical device. Treat any real-device use as experimental; a run can leave the phone in an uncertain state.

No real phone serial, complete private flash logs, firmware images, backups, or user data are included in this repository. The source export allowlist should contain only source, public documentation, and synthetic fixtures.

## Evidence required before changing this status

Before claiming real-device support, maintainers would need to review the final code and separately document controlled hardware validation for the exact model/build/kernel combination. Evidence should include verified input hashes, state checks at every stage, complete unredacted logs retained privately, independent readback of protected boot-chain and written targets, the fresh-Recovery and Format Data checks, and successful Android boot verification. Public reports must redact serials, account details, tokens, and other private data. Testing one configuration would still not establish general OPPO support.

## Historical source material

The private operator record is kept outside this source project. Public conversion package, GBL, and OrangeFox sources are linked in [CONVERSION.md](CONVERSION.md). The later EU500 OTA manual verification is separately documented by the [OTA updater project](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater); it is not evidence that this converter's CLI works.
