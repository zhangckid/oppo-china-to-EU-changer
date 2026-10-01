# Full CLI walkthrough

English | [简体中文](CLI.zh-CN.md) | [Project home](../README.md)

First-time readers should start with [Start here](START_HERE.md). Keep the [flowcharts](FLOW.md) and [visual checkpoints](SCREENSHOTS.md) alongside this walkthrough. After offline preparation, use `python3 change.py guide "$RUN_DIR"` for readable stage guidance, or add `--language zh-CN`. It reads the journal only; it does not verify the phone or acknowledge execution.

This is the complete command sequence for the one reviewed case. It assumes a fresh, stock CN403 `PMA110` (512 GB, project `25021`, pinned kernel), not a phone already converted to EU. The program can issue real device commands. Its end-to-end workflow has not been used on a phone; the hardware support claim remains unvalidated.

The CLI requires Linux and Python 3.11 or newer and uses only the Python standard library. Windows and macOS hosts are unsupported because the runner uses Linux locking and `/proc` facilities. Device execution requires Google Platform Tools **37.0.1**. Keep the ROM, GBL APK, OrangeFox IMG, and OrangeFox ZIP out of the public source tree. The CLI identifies inputs by pinned size and SHA-256, not by their local filename; use the published file names where possible and verify downloads at their publisher/maintainer source.

Before you begin, back up personal data elsewhere, charge the phone to at least 50%, ensure the host has enough free space for the complete selected-partition backup plus 1 GiB, enable and authorize USB debugging, and connect only this phone. Unlocking and both Format Data steps erase data. The partition backup is not a personal-data backup.

## 1. Set paths and verify host tools

Use your real paths and serial values. These are shell variables for readability; they are not device defaults.

```sh
TOOLS="/absolute/path/to/platform-tools-37.0.1"
INPUTS="/absolute/path/to/verified-inputs"
RUN_DIR="runs/pma110-512g-cn403-to-eu403"
ANDROID_SERIAL="replace-with-the-targets-current-adb-serial"
```

Check the host binaries. This command does not connect to or inspect the phone:

```sh
python3 change.py doctor --platform-tools "$TOOLS"
```

The result must identify both `adb` and `fastboot` as version `37.0.1`. Do not switch tools partway through a run.

## 2. Verify inputs and create a new run

Supply the four reviewed artifacts by their local paths. The destination must not already exist; a run is a permanent evidence record and cannot be overwritten.

```sh
python3 change.py prepare \
  --rom "$INPUTS/Recovery Flasher F9U CN2EU 16.0.9.403.zip" \
  --gbl-apk "$INPUTS/x9u-root-flasher-v0.2.1.apk" \
  --recovery-img "$INPUTS/OrangeFox-R12.0-Unofficial-lighthouse.img" \
  --recovery-zip "$INPUTS/OrangeFox-R12.0-Unofficial-lighthouse.zip" \
  --out "$RUN_DIR"
```

Preparation is offline: it checks the four inputs' pinned sizes and SHA-256 values, the exact ZIP inventory and image sizes, and sparse `super` structure. It can take several minutes. It does not talk to the phone. Any mismatch is a hard stop; do not edit pins or substitute an unreviewed file to bypass validation. Review the resulting run:

```sh
python3 change.py status "$RUN_DIR"
python3 change.py run "$RUN_DIR"
```

The second command is a preview only. It shows the starting instructions without connecting to the phone.

## 3. Start explicitly

On the phone, confirm that the expected stock CN403 Android setup is running. On the host, verify that `"$TOOLS/adb" devices -l` lists exactly this authorized phone and no other transport. Then start the run:

```sh
python3 change.py run "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-erase "$ANDROID_SERIAL"
```

The command rechecks device identity, build, project, kernel, lock state, and storage geometry before installing the pinned GBL app. It normally returns exit code `3` with stage `waiting_gbl`; this means it reached the next human checkpoint. See [Troubleshooting](TROUBLESHOOTING.md) for exit codes and stop handling.

## 4. GBL install and unlock

At `waiting_gbl`, use the installed GBL app on the phone:

1. Obtain temporary root and use the app's `FLASH` action.
2. Wait for `FLASH_VERIFY_OK` (write and readback verification).
3. In stock OPPO Recovery, complete the required Format Data.
4. Reboot; hold Volume Up immediately after the vibration to enter GBL. This is the observed GBL-entry procedure, not a general cold-boot shortcut.
5. On the host, find the current GBL serial with the read-only `"$TOOLS/fastboot" devices` command and set `GBL_SERIAL` to that value. It may differ from the Android ADB serial.

```sh
GBL_SERIAL="replace-with-current-gbl-fastboot-serial"
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$GBL_SERIAL" --ack-stage waiting_gbl
```

The CLI checks that this is GBL bootloader fastboot and then sends the OEM-unlock toggle and bootloader-unlock request. It cannot confirm the phone prompt for you. Confirm the bootloader unlock physically on the phone. Remain in GBL and continue with the same GBL serial:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$GBL_SERIAL" --ack-stage waiting_unlock
```

The CLI checks the unlocked state, writes the pinned OrangeFox IMG to `recovery_a`, and requests Recovery reboot. The next stage uses the original `ANDROID_SERIAL`, not the GBL serial.

## 5. Recovery, backup, and OrangeFox ZIP

At `waiting_recovery`, wait until OrangeFox Recovery ADB is available. Resume with the original Android ADB serial:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_recovery
```

The CLI validates the CN GPT/layout, the protected GBL components, OrangeFox identity, capacity, and battery, then makes a fresh host backup of the selected firmware partitions and GPTs before more flashing. This backup is made after GBL install, the stock Format Data, and the Recovery IMG write; it is not a factory-state backup and excludes `userdata`.

At `waiting_ofox_sideload`, use the OrangeFox UI to enable **ADB Sideload**, then run:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_ofox_sideload
```

Wait for the OrangeFox ZIP to finish and Recovery to return. At `waiting_ofox_recovery`, use the same serial:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_ofox_recovery
```

Before the conversion package is allowed, the CLI verifies a fresh Recovery boot, both OrangeFox slots, protected GBL state, capacity and backup hashes, an empty Recovery script queue, automatic Recovery reboot disabled, and no mounted firmware filesystems. It also saves the pre-install Recovery log. If any check fails, stop; the detailed response table is in [Troubleshooting](TROUBLESHOOTING.md).

## 6. Sideload and verify the CN2EU installer

At `waiting_rom_sideload`, enable OrangeFox **ADB Sideload** and run:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_rom_sideload
```

During this exact installer, press Volume Up to continue, then Volume Down for **ABL = NO**. Never select ABL = YES; that would not preserve the expected GBL chain. Keep USB attached. Wait for the installer itself to complete.

At `waiting_install_result`, make sure the phone is in ordinary Recovery ADB rather than sideload mode, and do not reboot it. Then run:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_install_result
```

The CLI compares Recovery log contents from before and after installation. It requires a new `Installation complete` marker, confirmation that current ABL was kept, no installer error, and the expected on-disk GPT. A computer-side transfer percentage or successful ADB process exit is insufficient. On success, the CLI requests a fresh Recovery boot.

At `waiting_fresh_recovery`, wait for that reboot and resume:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_fresh_recovery
```

It checks the fresh kernel's EU GPT/layout and capacity, every recorded firmware target readback, and every defined RAW/FILL sparse `super` extent. DONT_CARE extents are not claimed as written/read back. It also captures the before-format log.

## 7. Format Data and boot EU Android

At `waiting_format`, do this manually in OrangeFox: **Menu → Partitions management → Static partitions → Data → Format Data**, type `yes`, and wait for completion. Do not boot System. Then resume from the same Recovery session:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_format
```

The tool requires fresh log evidence that both `/dev/block/sda15` (data) and `/dev/block/sda10` (metadata) were formatted successfully. It requests another Recovery reboot. At `waiting_formatted_recovery`, wait for the reboot and run:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_formatted_recovery
```

The CLI confirms the fresh Recovery/GPT and `/data` mounted as F2FS, then requests the first Android boot. Complete the Android setup, enable USB debugging, authorize the host, and resume at `waiting_android`:

```sh
python3 change.py resume "$RUN_DIR" \
  --platform-tools "$TOOLS" --execute \
  --serial "$ANDROID_SERIAL" --ack-stage waiting_android
python3 change.py status "$RUN_DIR"
```

The tool records `complete` only after it verifies the EU model/build/project/region, unlocked state, expected slot, boot completion, and completed setup. Keep the bootloader unlocked; later EU OTA upgrades are a separate workflow.

## If any stage stops

Do not repeat the last command or make an unreviewed change to the phone. Read the exact state and instructions:

```sh
python3 change.py status "$RUN_DIR"
```

If the stage is `review_required`, the tool intentionally has no resume, reset, or force command. Preserve the run directory, current phone screen/mode, and any possible partial writes. Review [Troubleshooting](TROUBLESHOOTING.md) and [Validation limits](VALIDATION.md). The run directory contains private paths, serials, Recovery logs, and backups; do not post it publicly without a careful privacy review.
