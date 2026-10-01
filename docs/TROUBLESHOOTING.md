# Troubleshooting and exception handling

English | [简体中文](TROUBLESHOOTING.zh-CN.md) | [Project home](../README.md)

This guide explains what the CLI's result means and how to preserve evidence when it stops. It does not provide a universal repair recipe. A failed check can indicate that the phone or a write is already in a different state from the reviewed path.

## Before starting

The host must run Linux and Python 3.11 or newer. Windows and macOS hosts are unsupported in this release.

- Work only with the exact `PMA110`, 512 GB, project `25021`, CN403 build, and pinned artifacts in this repository. This project does not support all OPPO devices or all PMA110/PMA120 configurations.
- Keep a separate personal-data backup. Unlock and both Format Data steps erase user data. The tool's pre-conversion backup excludes `userdata` and is not a personal-data backup.
- Have the exact Platform Tools 37.0.1 installed in a directory containing `adb` and `fastboot`, and at least 50% battery before execution. Backups also require host disk space for all selected partitions plus a 1 GiB reserve.
- Authorize USB debugging on the phone before the first command. When beginning, connect only the target phone and use its current serial. GBL fastboot can present a different serial from Android/Recovery ADB.
- Read the instructions shown by `status` at every stage. Keep the phone, USB cable, and host stable while a command runs.

`prepare` performs local file verification and does not contact the phone. It checks each required input's pinned size and SHA-256, then inspects the conversion ZIP and sparse `super` image. Local basenames do not affect verification. Do not edit pins or replace files to make a mismatch pass. `doctor` checks the host Platform Tools only; it does not inspect a phone.

## Exit codes and run state

| Result | Meaning | Response |
| --- | --- | --- |
| Exit `0` | `prepare`, `doctor`, `status`, or a command that completed successfully | Read the JSON result; for a completed conversion confirm `stage` and `status` are both `complete`. |
| Exit `3` | Expected checkpoint: the executed stage returned to a human-wait state | Read the printed instructions and `status`. Perform only the requested manual action, then run `resume` with the exact current `--ack-stage` and the correct serial. |
| Exit `2` | Validation or execution stopped with an error | Preserve the run directory and phone state. Read the `STOP:` message and `status`; if state is `review_required`, no CLI command can reset or bypass it. Arrange manual, device-specific review. |
| Exit `130` | The host process received Ctrl-C | Do not rerun the operation. The journal may still say `executing`; a later invocation deliberately marks it `review_required` rather than replaying the action. |

An unexpected disconnect or timeout during a write, sideload, backup, or readback can leave partial work. The safe interpretation is “completion unknown,” even if the command log shows some output. A successfully returning host command is not by itself proof that the Recovery installer succeeded.

`run` without `--execute` is a preview. It does not send device commands. `resume` only acknowledges the exact current wait stage; it is not a general retry command. For the GBL handoff, supply the current GBL fastboot serial. During `waiting_unlock`, use the bound GBL serial. Recovery and Android stages use the original ADB serial.

## Stop conditions and next steps

| Message or situation | What it means | What to do |
| --- | --- | --- |
| Size, SHA-256, ZIP contents, sparse image, or firmware inventory differs | The local files do not match the reviewed inputs. No phone command is needed for `prepare`. | Stop. Obtain the exact files from the listed release/publisher and verify again. Never change `pins.json` to accept a different artifact. |
| ADB says `unauthorized`, no authorized device is present, multiple devices are listed, or a different serial appears | The transport is not the one bound to the run, or the phone has not authorized this computer. | Before a new run, authorize the host and connect only the target device. Do not unplug a phone while a device command is active. If the current run entered `review_required`, preserve it and review the current phone state before starting anything else. |
| Platform Tools missing or version differs from 37.0.1 | The reviewed ADB/fastboot host binaries are unavailable. | Run `doctor --platform-tools PATH` after installing the official version. A Tools mismatch before execution is a host setup issue; do not switch binaries mid-run. |
| Wrong mode, wrong GBL fastboot, `fastbootd`, unexpected boot identity, GPT, partition size, slot, lock state, or battery below 50% | The device state differs from the reviewed case or is not ready for the next stage. | Stop. Do not issue manual flash/unlock/reboot commands to force the expected state. Preserve `status` and the visible phone screen for review. |
| Qualcomm `xbl_config` metadata differs from the reviewed `(3, 0, 0)` value, or the image parser reports missing/ambiguous metadata | The exact rollback metadata cannot be confirmed from this firmware image. This is image metadata parsing; it does not read device fuses. | Stop. Do not replace or patch the metadata or alter pins. Obtain exact-case maintainer review for a new package. |
| Multiple USB transports or serial changes at a wait point | More than one device is visible, or transport serial changed. | For a fresh start, connect only the target. At GBL, use the GBL serial as documented. Do not substitute a different Android/Recovery serial after it has been bound. A `review_required` run cannot be rebound. |
| Backup space is insufficient, a backup read fails, or host/device SHA-256 differs | The pre-conversion snapshot is incomplete or inconsistent. | Do not sideload OrangeFox ZIP or the ROM. Keep any partial backup and logs; do not delete the run directory to make a retry possible. Resolve storage/device uncertainty through manual review. |
| `/system`, `/vendor`, `/product`, `/system_ext`, or `/odm` is mounted before ROM sideload | The conversion preflight found a mounted firmware filesystem. In the historical case a touch service held `/odm`. | Do not continue, kill services, force/lazy unmount, or apply an ADB-daemon workaround based on this guide. Record the stage and seek review for the exact Recovery build. The CLI does not alter services automatically. |
| Recovery UI restarted, queued script remains, or Recovery log rotated during install/format | Completion markers may be stale or missing, so the CLI cannot prove what happened. | Do not start the installer or formatter again. Preserve the Recovery screen and run directory; do not treat an old `Installation complete` line as current evidence. |
| OrangeFox prompts for ABL and Volume Down is not selected, or `ABL=YES` is shown | The preserved GBL boot chain is at risk. The reviewed package flow requires ABL **NO**. | Do not choose ABL YES. If already selected, stop the workflow, do not reboot or attempt another flash, and request case-specific review. |
| Sideload reports host completion but install log has no new `Installation complete`, reports an error, or does not confirm ABL was kept | The host transfer does not establish successful installation. | Do not format data or boot Android. Keep Recovery in its current state and save the logs; do not re-sideload on top of uncertain writes. |
| ADB/fastboot command times out, USB disconnects during a command, partition backup/readback is short, or an operation may have started but has no verified result | The operation may have completed partly, even if the host process timed out or ended. | Do not retry, reconnect and replay, reboot, switch slots, or delete partial backup evidence. Preserve the phone's current mode and run directory for manual review. |
| Fresh Recovery check finds GPT, GBL, OrangeFox, firmware, or sparse `super` extent mismatch | A protected component or expected write does not match the exact reviewed hash/layout. | Stop. Do not reboot to Android, relock, change slots, or flash a guessed image. Preserve all evidence and request device-specific recovery guidance. |
| Format Data fails, log evidence is stale, or `/data` is not mounted as F2FS in the fresh Recovery boot | The required manual format is unverified. The checks expect successful `mkfs_f2fs` records for `/dev/block/sda15` and `/dev/block/sda10`, then a fresh Recovery with `/data` mounted. | Do not boot Android or repeat formatting based only on an old message. Preserve current Recovery and logs for review. |
| Android does not reach the expected EU identity/setup, or device enters a boot loop | Final boot verification failed or is unavailable. | Do not relock, repeat the conversion, or flash unreviewed files. Keep the bootloader unlocked, record the visible state and last run stage, and seek experienced, device-specific recovery help. |

## Evidence and privacy

Use `python3 change.py status RUN_DIR` to read the journal. Keep the whole run directory privately: `state.json`, `manifest.json`, `commands.jsonl`, all `*.log`, and backup records help establish what happened. Logs and command files can contain serials, host paths, partition data, and other private details. Review and redact them before posting; do not publish firmware/backups or a complete run directory.

When requesting help, give the exact model/storage, source build, project/kernel, artifact filenames and hashes, current screen/mode, last successful stage, exact error text, and whether a write may have started. Never post a serial, account token, personal backup, or unredacted device logs. If the run is `review_required`, the tool intentionally has no “continue anyway” command.

For XDA and maintainer links, see [Sources and provenance](SOURCES.md). Community discussion can help find a person familiar with the device, but do not copy a procedure for a different model or build.
