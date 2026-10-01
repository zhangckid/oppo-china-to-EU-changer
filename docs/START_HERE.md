# Start here

English | [简体中文](START_HERE.zh-CN.md) | [Project home](../README.md)

This is a **technical exploration project**. Actual operation requires Android flashing knowledge, Linux command-line experience, **and AI assistance** to inspect the exact inputs, logs, and next action. This is the project's operating prerequisite, not a promise that AI makes flashing safe. The operator must understand and verify every destructive step. Codex assisted the implementation and documentation; upstream credits are in [Sources](SOURCES.md).

Only **one Find X9 Ultra / X9U, PMA110 512 GB** has historical manual conversion evidence. The new CLI has not completed a hardware conversion. Start with [tested scope and OTA/NFC observations](COMPATIBILITY.md).

## Choose the right route

| Your situation | Start here |
| --- | --- |
| Learning how CN-to-EU conversion works | Read the [historical sequence](CONVERSION.md) and [flowcharts](FLOW.md). No phone connection is needed. |
| Fresh, locked stock CN403, exactly matching the recorded case | Read this page, verify the four inputs, then follow [CLI sections 1–7](CLI.md) one stage at a time. |
| Already converted to EU; built-in OTA fails | Use the separate [OTA updater documentation](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater). Its baseline/profile requirements still apply; do not rerun this converter. |
| Partially flashed, already unlocked/modified, or interrupted without a valid waiting checkpoint | Preserve the current state and read [Troubleshooting](TROUBLESHOOTING.md). The CLI cannot adopt or repair an arbitrary existing state. |
| Another model, capacity, source build, kernel, or host OS | Outside this implementation's scope. A model name alone is not sufficient. |

## Before any phone operation

- A Linux computer with Python **3.11+** and Google Platform Tools **37.0.1**. No pip dependencies. Windows and macOS execution are unsupported.
- The four exact files: CN2EU ROM ZIP, GBL APK, OrangeFox IMG, OrangeFox ZIP. Use the [source links, sizes and SHA-256 table](CONVERSION.md#obtain-and-verify-the-tools).
- A reliable data cable, one connected phone, at least 50% battery, and enough host disk space for the selected-partition backup plus 1 GiB, **in addition to** the downloaded files. The tool calculates the backup requirement at its checkpoint.
- A separate, verified backup of personal data, including anything required to restore accounts. Both formatting and unlocking erase data. The tool's partition backup excludes personal data and is taken after initial modifications.
- The complete manual sequence and stop conditions understood before starting. Keep a second screen available for documentation during phone reboots.

Download or extract the **source project** to a local directory. Open a terminal in the directory containing `change.py`. Keep large downloaded inputs elsewhere. All shell commands in these guides run on the **computer**, unless a step explicitly says to use the phone.

```sh
python3 change.py --help
```

The project needs no installation step. [CLI section 1](CLI.md#1-set-paths-and-verify-host-tools) sets four variables for tools, input directory, run directory, and Android serial. Replace every placeholder with your values; keep quotes around paths containing spaces. Never put an existing run directory into `prepare --out`.

## Your everyday command

After `prepare` creates a run, read its current checkpoint without touching the phone:

```sh
python3 change.py guide runs/convert
python3 change.py guide runs/convert --language zh-CN
```

Use **your actual run directory** in place of `runs/convert`. The guide shows the stage, human action, serial type and numbered CLI section to follow. It reads the local journal only, cannot verify the live phone, and does not advance a checkpoint. `status` retains machine-readable JSON for diagnosis.

| Command/result | What to do |
| --- | --- |
| `doctor` | Check host ADB/fastboot; this does not inspect a phone. |
| `prepare` | Audit inputs offline and create a new record; large file hashing takes time. |
| `guide` or `status` | Read the current local record. These do not acknowledge a stage. |
| `run` / `resume` without `--execute` | Preview only. Nothing is sent to the phone. |
| Executed command exits **3** | Normal manual checkpoint. Read the guide, complete the phone action, then use the matching CLI command. |
| Executed command exits **2** or **130** | Read the exact error and preserve the state. A partially completed action must not be replayed. |
| `review_required`, `running`, or `executing` after the original process ended | Stop for manual review. The guide will withhold the normal next-step instructions. |

A successful `guide` or `status` exits 0 because reading the record succeeded, even if that record says `review_required`. **Always read the stage and status.** Normal wait points do not justify a loop that automatically runs `resume`.

## Recognize the phone mode

| Term | What it means here | How it affects the next step |
| --- | --- | --- |
| Android / ADB | Normal operating system with USB debugging authorized | Starting and final verification use the original Android ADB serial. |
| GBL / bootloader fastboot | Bootloader access installed by the upstream GBL app | It may show a different serial; use the documented GBL handoff. This is not fastbootd. |
| OrangeFox / Recovery | Separate recovery environment | Normal Recovery ADB allows logs, backup and checks. Its Files screen alone is not proof an installer succeeded. |
| ADB Sideload | A Recovery mode for receiving an installer ZIP | Enable it only at the corresponding wait point. Receiving a ZIP is different from finishing its installation. |
| `super` / GPT | Android system container / partition table | The converter changes their layout; do not improvise commands or reuse another capacity's boundaries. |
| Format Data | The specific filesystem-format action in Recovery | A wipe, factory-reset label elsewhere, or deletion of files is not a substitute for the recorded OrangeFox action. |

[Visual checkpoints and available screenshots](SCREENSHOTS.md) provide a screen-by-screen reference. Photos illustrate a state; fresh logs and readback remain necessary.

## Use AI for review, with a human in control

Give the assistant the relevant source links, exact non-sensitive build information, and a redacted error excerpt. A useful request is:

> Read this project's CLI, flow and troubleshooting documents. Compare my exact model, capacity, build, kernel and current journal stage with the documented case. Explain which checks are proven, which are missing, and what the next documented step changes. Start with read-only analysis; if evidence differs or a write may have been interrupted, stop for manual review. Do not invent a force/retry/relock procedure.

Do not upload full run directories, partition backups, serials, IMEIs, account tokens or personal data. AI output is a proposal to inspect; it is not evidence that a command is appropriate. If you cannot explain a proposed write, format or reboot and its prerequisites, do not perform it.

**Next:** [CLI walkthrough](CLI.md) · [Flowcharts](FLOW.md) · [Screenshots](SCREENSHOTS.md) · [Credits and references](SOURCES.md)
