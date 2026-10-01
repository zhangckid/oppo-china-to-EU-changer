# Design and trust boundaries

English | [简体中文](DESIGN.zh-CN.md) | [Project home](../README.md)

The conversion combines downloaded artifacts, a host computer, bootloader/Recovery operations, and actions that must be confirmed on the phone. The CLI organizes that work as a checked sequence with pauses for a person. It does not make the community conversion package or firmware intrinsically safe.

## Workflow stages

`prepare` verifies the local inputs and creates a run directory. `status` reports its recorded stage. `run` without execution flags displays a preview. Execute mode uses the configured Platform Tools and a serial-bound erase acknowledgment. Human actions are then represented by explicit wait states:

`waiting_gbl` → `waiting_unlock` → `waiting_recovery` → `waiting_ofox_sideload` → `waiting_ofox_recovery` → `waiting_rom_sideload` → `waiting_install_result` → `waiting_fresh_recovery` → `waiting_format` → `waiting_formatted_recovery` → `waiting_android` → `complete`.

The `resume` command acknowledges the exact current wait state using `--ack-stage`; it checks observed device state before moving on. GBL transport can have a different serial, but the command must receive that current serial and explicitly acknowledge the GBL wait. Recovery and Android stages remain bound to the original ADB serial. The workflow captures Recovery logs before and after conversion and rejects stale installer-completion evidence. Following manual Format Data, it expects a fresh boot identity, a successful format result, and checks for the expected data devices/filesystems before allowing the Android stage.

The stage names describe required checkpoints, not a promise that the new tool has been validated on a physical phone. With `--execute`, this implementation issues real ADB/fastboot commands. The execution sequence remains unvalidated on hardware; mock tests cannot establish that images or commands are safe for a physical device. `prepare`, `doctor`, preview, and simulated tests do not establish device compatibility.

## Implementation map

| Module | Responsibility and checks |
| --- | --- |
| `changer/core.py` | Canonical JSON state, atomic replacement with file/directory sync, process locking, and streaming hashes. The journal checksum detects accidental corruption or edits; it is not authentication and cannot prove that a local operator or malware did not alter both state and checksum. |
| `changer/artifacts.py` | Verifies pinned artifact sizes and SHA-256 values, inspects ROM members and sparse-image structure, and holds verified file descriptors for transfers so replacing a pathname does not silently switch the opened input. |
| `changer/device.py` | Runs bounded ADB/fastboot subprocesses with explicit serial selection, captures limited output, and treats timeouts, disconnects, and non-zero results as errors. |
| `changer/policy.py` | Applies the exact PMA110 profile: model/build and lock checks, GPT and partition identity/capacity checks, protected boot-chain and firmware metadata checks, and fresh Recovery/format-log checks. |
| `changer/runner.py` | Orchestrates the journaled stage sequence, backup/readback checks, explicit human handoffs, and interruption-to-`review_required` handling. It does not force, reset, retry uncertain writes, or roll back. |
| `changer/cli.py` | Exposes `prepare`, `status`, `run`, `resume`, and `doctor`; defaults to preview, requires explicit execution/serial/erase acknowledgments for device operations, and uses exit codes for waits and stops. |
| `scripts/export_source.py` | Builds a share-safe source bundle from the strict, repository-relative `release-files.txt` allowlist; it does not gather run data or firmware artifacts. |

This module map describes code paths, not evidence of successful operation on hardware. The checks reduce known mistakes but do not authenticate the host, binaries, connected device, or community firmware.

| Stage | Device/human action | What the runner checks before proceeding |
| --- | --- | --- |
| `prepared` | Start from the fresh, locked CN403 Android install; acknowledge data erase. | Android model/build/project/kernel/lock state and disk geometry; then install the pinned GBL APK. |
| `waiting_gbl` | In the GBL app obtain temporary root, enter `FLASH`, require its verification success, format data in stock Recovery, reboot, then hold Volume Up after vibration to enter GBL. | GBL bootloader fastboot (not fastbootd), locked state; then request OEM unlock and bootloader unlock. The phone screen still needs human confirmation. |
| `waiting_unlock` | Confirm the unlock on the phone and remain in GBL. | GBL unlocked state; then write the pinned OrangeFox IMG to `recovery_a` and reboot to Recovery. |
| `waiting_recovery` | Wait for OrangeFox ADB. | CN GPT/layout, expected slot and protected boot-chain hashes, Recovery identity and at least 50% battery; then back up the reviewed partitions and GPTs before further flashing. |
| `waiting_ofox_sideload` | Enable OrangeFox ADB Sideload. | Sideload the pinned OrangeFox ZIP. |
| `waiting_ofox_recovery` | Wait for Recovery to return. | Fresh Recovery boot ID, both OrangeFox slots and retained GBL checks, partition capacities, backup hashes, no stale queued script, automatic reboot disabled, and no blocked firmware filesystems mounted; then capture the pre-install Recovery log. |
| `waiting_rom_sideload` | Enable ADB Sideload; on the installer screen press Volume Up to continue and Volume Down for ABL=NO. | Sideload the exact CN2EU ZIP. The CLI prints the package-specific prompt; the user must press the phone buttons. |
| `waiting_install_result` | Keep the phone in Recovery; leave sideload mode if needed, without rebooting. | Pull fresh Recovery log and require a new `Installation complete`, ABL kept, and no install errors; inspect on-disk GPT, then request a fresh Recovery boot. |
| `waiting_fresh_recovery` | Wait for that Recovery boot. | New boot ID, EU GPT/layout and capacities, readback hashes for the firmware images and every defined sparse `super` extent; then capture the before-format log. |
| `waiting_format` | In OrangeFox manually Format Data through the menu and type `yes`; do not boot System. | Require new `mkfs_f2fs` success for data (`sda15`) and metadata (`sda10`) in the fresh log; then request another Recovery boot. |
| `waiting_formatted_recovery` | Wait for Recovery to return after format. | New boot ID, EU Recovery/GPT, and `/data` mounted as F2FS; then request first Android boot. |
| `waiting_android` | Complete setup, enable USB debugging, and authorize the host. | EU model/build/project/region, unlocked state, slot, boot completion, and completed setup. |
| `complete` | Keep the bootloader unlocked. | Final recorded state; use a separate reviewed updater for later OTA work. |

`status` displays the current stage instructions. The tool does not silently handle a stage that was skipped or produces different evidence. Every unexpected mode, identity, layout, hash, log, timeout, and command failure stops the current run. See [Troubleshooting](TROUBLESHOOTING.md) for exit codes and evidence handling.

## Stop and resume policy

The tool may resume only from a recorded expected human-wait state after checking that state against the connected device. If the process is interrupted while performing an operation, it records `review_required`. It offers no reset, force, automatic write retry, rollback, or automatic continuation through an uncertain write. A human must establish the device mode, completed and uncertain operations, backup status, and next safe action independently.

Every destructive stage has an explicit human gate. The CLI cannot confirm the bootloader unlock prompt or press OrangeFox controls on the user's behalf. Format Data is manual. It does not kill the touch service to unmount `/odm`, manage an `adbd` conflict, or choose answers to package prompts on its own.

## Artifact and device boundaries

The host checks local file identities and records operation evidence. Device checks are useful only to the extent that the transport and device report are trustworthy. An installation message or transfer percentage alone is not proof that every target was written correctly. Firmware images and backups stay outside the source release; logs can expose identifiers and must be reviewed before sharing.

The historical manual case made its own backup after GBL installation, the first Format Data, and OrangeFox IMG installation: 121 selected partitions and six GPT copies. This was not a factory-state backup and did not include personal data. Its checks must not be confused with the current CLI's checks. The CLI code implements a 107-partition backup plus six GPT copies, then readback hashes for 100 firmware targets and 290 defined sparse `super` RAW/FILL extents; 19 DONT_CARE extents have undefined contents and are not checked on the phone. The new CLI has not performed any of those backup or readback operations on hardware; its behavior is covered only by mocks.

## Safety assumptions

- The source phone matches the exact recorded model, storage, build, project and kernel.
- The selected ROM, GBL APK and OrangeFox files come from the indicated publishers and have been independently verified.
- The operator has a separate backup of personal data and understands that unlock and format operations erase data.
- The expected GBL, bootloader, OrangeFox and Android modes are identified correctly.
- The user physically confirms each prompt and stops when the screen or device state differs.

If any assumption is false or unverified, do not execute the conversion.
