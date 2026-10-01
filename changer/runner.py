"""Journaled human/host handoffs; an interrupted action is never replayed."""
import os
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import zipfile

from .core import ReviewRequired, atomic_json, canonical_hash, read_json, require, sha256_file
from .device import Device, _bounded_process_output
from . import policy


INSTRUCTIONS = {
    "prepared": "Preview only. Back up personal data. Run with --execute --serial SERIAL --ack-erase SERIAL and --platform-tools DIR to start on stock CN403 Android.",
    "waiting_gbl": "On the phone open the installed GBL app, obtain Temporary root, type FLASH and require FLASH_VERIFY_OK. Use stock OPPO Recovery Format Data. Reboot and hold Volume Up immediately after vibration to enter GBL. Resume with --serial FASTBOOT_SERIAL --ack-stage waiting_gbl. All personal data is erased.",
    "waiting_unlock": "Confirm bootloader unlock on the phone. Return to GBL if necessary; do not start Android. Resume with the bound fastboot serial and --ack-stage waiting_unlock.",
    "waiting_recovery": "Wait for OrangeFox Recovery ADB. Resume with the original Android ADB serial and --ack-stage waiting_recovery. Full firmware and GPT backup runs before further flashing.",
    "waiting_ofox_sideload": "In OrangeFox enable ADB Sideload. Resume with the original ADB serial and --ack-stage waiting_ofox_sideload to install the matching OrangeFox ZIP.",
    "waiting_ofox_recovery": "Wait for the OrangeFox installer to reboot Recovery. Resume with the original ADB serial and --ack-stage waiting_ofox_recovery.",
    "waiting_rom_sideload": "Disable automatic reboot; enable OrangeFox ADB Sideload. Resume with --ack-stage waiting_rom_sideload. During installation press Volume Up to continue, then Volume Down for Flash ABL=NO. Keep USB connected; never boot Android on an error.",
    "waiting_install_result": "Keep the phone in Recovery and exit sideload if needed. Resume with --ack-stage waiting_install_result to collect fresh installer evidence. Host download progress is not proof of success.",
    "waiting_fresh_recovery": "Wait for the requested Recovery reboot. Resume with --ack-stage waiting_fresh_recovery to verify the new GPT, 100 firmware writes and every defined sparse super extent.",
    "waiting_format": "In this Recovery session: Menu -> Partitions management -> Static partitions -> Data -> Format Data -> type yes. Require success. Do not boot System. Resume with --ack-stage waiting_format.",
    "waiting_formatted_recovery": "Wait for the requested Recovery reboot after formatting. Resume with --ack-stage waiting_formatted_recovery; the tool checks /data before starting System.",
    "waiting_android": "Complete Android setup, enable USB debugging and authorize this computer. Resume with the original ADB serial and --ack-stage waiting_android for EU403 verification.",
    "complete": "Conversion verified. Keep the bootloader unlocked. Use the separate OTA updater for later reviewed OTA versions.",
    "review_required": "STOP. Preserve this directory and the phone state; do not blindly retry, reset the journal, format, relock, or boot Android. Review the saved error, command logs, and any recovery evidence manually. There is no automatic reset or recovery command.",
}


def tools_info(directory):
    root = Path(directory).expanduser().resolve()
    result = {}
    for name in ("adb", "fastboot"):
        path = root / name
        require(path.is_file() and os.access(path, os.X_OK), f"Missing executable: {path}")
        proc = subprocess.Popen([str(path), "version" if name == "adb" else "--version"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        code, stdout, stderr = _bounded_process_output(proc, 15)
        require(code == 0, f"Cannot read {name} version")
        version = stdout + stderr
        require(re.search(r"\b37\.0\.1(?:-|\b)", version) is not None,
                f"Only reviewed Platform Tools 37.0.1 is supported: {name}")
        result[name] = {"path": str(path), "sha256": sha256_file(path), "version": version.strip()}
    return result


def create_run(directory, manifest):
    directory = Path(directory).resolve()
    require(not directory.exists(), "Run directory already exists; never overwrite previous evidence")
    directory.mkdir(parents=True, mode=0o700)
    atomic_json(directory / "manifest.json", manifest)
    state = {"schema": 1, "stage": "prepared", "status": "waiting",
             "manifest_sha256": canonical_hash(manifest), "history": []}
    save_state(directory, state)
    return state


def save_state(directory, state):
    atomic_json(Path(directory) / "state.json", {"state": state, "sha256": canonical_hash(state)})


def load_state(directory):
    envelope = read_json(Path(directory) / "state.json")
    require(isinstance(envelope, dict) and "state" in envelope, "Invalid journal envelope")
    state = envelope["state"]
    require(envelope.get("sha256") == canonical_hash(state), "Journal checksum mismatch; manual edits are not supported")
    require(state.get("schema") == 1 and state.get("stage") in INSTRUCTIONS, "Unknown journal schema or stage")
    require(state.get("status") in {"waiting", "running", "executing", "review_required", "complete"}, "Invalid journal status")
    return state


def status(directory):
    state = load_state(directory)
    instructions = INSTRUCTIONS[state["stage"]]
    if state["status"] in {"executing", "running"}:
        instructions = "An action is recorded as in progress. Keep the current process running. If it ended, preserve the device state for manual review; the next execution will refuse to replay this action."
    return {"stage": state["stage"], "status": state["status"],
            "instructions": instructions, "error": state.get("error"),
            "failed_stage": state.get("failed_stage"), "last_action": state.get("action")}


class Runner:
    def __init__(self, directory, device_factory=Device):
        self.root = Path(directory).resolve()
        self.state = load_state(self.root)
        self.manifest = read_json(self.root / "manifest.json")
        require(canonical_hash(self.manifest) == self.state["manifest_sha256"], "Prepared manifest changed")
        self.device_factory = device_factory

    def save(self):
        save_state(self.root, self.state)

    def action(self, name, function):
        # This must reach stable storage before invoking a mutating command.
        self.state.update(status="executing", action=name)
        self.save()
        result = function()
        self.state["history"].append({"action": name, "finished_at": time.time()})
        self.state.update(status="running", action=None)
        self.save()
        return result

    def wait(self, stage):
        self.state.update(stage=stage, status="waiting", action=None)
        self.save()

    def artifact(self, key):
        item = self.manifest["inputs"][key]
        path = Path(item["path"])
        require(path.is_file() and path.stat().st_size == item["size"], f"Artifact size changed: {key}")
        require(sha256_file(path) == item["sha256"], f"Artifact SHA-256 changed: {key}")
        return path

    def with_artifact(self, key, consume):
        """Hash and lease one open file for the complete host transfer.

        A private symlink keeps the extension expected by adb install while
        anchoring opens to our original Linux file descriptor. Replacing the
        external pathname cannot redirect this transfer. In-place changes are
        detected by fstat before/after; a concurrent writer remains outside the
        trusted-host assumptions and can still make an in-flight write uncertain.
        """
        item = self.manifest["inputs"][key]
        path = Path(item["path"])
        suffix = {"rom": ".zip", "gbl_apk": ".apk", "recovery_img": ".img", "recovery_zip": ".zip"}[key]
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
            require(before.st_size == item["size"], f"Artifact size changed: {key}")
            digest = hashlib.sha256()
            remaining = item["size"]
            while remaining:
                block = source.read(min(4 * 1024 * 1024, remaining))
                require(block, f"Artifact became shorter while verifying: {key}")
                digest.update(block)
                remaining -= len(block)
            require(source.read(1) == b"", f"Artifact grew while verifying: {key}")
            require(digest.hexdigest() == item["sha256"], f"Artifact SHA-256 changed: {key}")
            require(stamp(os.fstat(source.fileno())) == stamp(before), f"Artifact changed while verifying: {key}")
            handle = Path(f"/proc/{os.getpid()}/fd/{source.fileno()}")
            require(handle.is_file(), "Linux /proc file-descriptor access is required for stable artifact transfers")
            with tempfile.TemporaryDirectory(prefix=".artifact-", dir=self.root) as temporary:
                lease = Path(temporary) / ("verified" + suffix)
                lease.symlink_to(handle)
                result = consume(lease)
                require(stamp(os.fstat(source.fileno())) == stamp(before),
                        f"Artifact changed during transfer: {key}; write outcome requires manual review")
                return result

    def recovery_log(self, name):
        # Private evidence: do not include in source archives or bug reports.
        destination = self.root / (name + ".log")
        self.device.pull("/tmp/recovery.log", destination)
        require(destination.stat().st_size <= 64 * 1024 * 1024, "Unexpected recovery log size")
        return destination.read_text(errors="replace")

    def same_boot(self):
        require(self.device.boot_id() == self.state["recovery_boot_id"], "Recovery unexpectedly rebooted; saved preflight is stale")

    def fresh_boot(self):
        current = self.device.boot_id()
        require(current != self.state["recovery_boot_id"], "Recovery has not rebooted; kernel GPT may be stale")
        self.state["recovery_boot_id"] = current
        self.save()

    def execute(self, *, command, serial, platform_tools, ack_erase=None, ack_stage=None):
        require(self.state["stage"] != "review_required", INSTRUCTIONS["review_required"])
        if self.state["status"] in {"executing", "running"}:
            self.state["failed_stage"] = self.state["stage"]
            self.state.update(stage="review_required", status="review_required",
                              error="Previous invocation stopped between journal checkpoints; no action will be replayed")
            self.save()
            raise ReviewRequired(self.state["error"])
        require(self.state["stage"] != "complete", "Run already complete")
        stage = self.state["stage"]
        # Missing acknowledgments are usage errors, not a reason to rewrite a valid waiting journal.
        if stage == "prepared":
            require(command == "run" and ack_erase == serial, "Start requires run and --ack-erase matching --serial")
        else:
            require(command == "resume" and ack_stage == stage, f"Resume requires --ack-stage {stage}")
        info = tools_info(platform_tools)
        if "tools" in self.state:
            require(info == self.state["tools"], "Platform Tools changed since this run started")
        else:
            self.state["tools"] = info
        self.device = self.device_factory(Path(info["adb"]["path"]), Path(info["fastboot"]["path"]),
                                          self.root / "commands.jsonl", serial)
        try:
            if stage == "prepared":
                self.state["adb_serial"] = serial
            elif stage == "waiting_gbl":
                # Explicit human handoff binds GBL's different USB serial once.
                require(self.device.mode() == "fastboot", "Expected GBL fastboot for the acknowledged handoff")
                self.state["fastboot_serial"] = serial
            else:
                expected = self.state["fastboot_serial"] if stage == "waiting_unlock" else self.state["adb_serial"]
                require(serial == expected, "Serial differs from the transport bound to this run")
            self.save()
            getattr(self, "step_" + stage)()
        except BaseException as error:
            self.state.update(stage="review_required", status="review_required", failed_stage=stage,
                              error=str(error) or type(error).__name__)
            self.save()
            # Log collection cannot turn a failed action into success and is
            # deliberately not a reboot, retry, or additional flash operation.
            try:
                if self.device.mode() == "recovery":
                    self.recovery_log("failure-recovery")
            except Exception:
                pass
            raise
        return status(self.root)

    def step_prepared(self):
        atomic_json(self.root / "android-before.json", policy.check_android(self.device))
        self.artifact("gbl_apk")
        # Resolve/validate all remaining files before even installing the APK.
        for key in ("recovery_img", "recovery_zip", "rom"):
            self.artifact(key)
        output = self.action("install_gbl_apk", lambda: self.with_artifact("gbl_apk",
            lambda path: self.device.adb(["install", str(path)], timeout=180)))
        require(re.search(r"^Success\s*$", output, re.M), "GBL APK install did not report Success")
        self.wait("waiting_gbl")

    def gbl_mode(self):
        require(self.device.mode() == "fastboot", "Expected GBL fastboot")
        require(re.search(r"is-userspace:\s*no\b", self.device.fastboot(["getvar", "is-userspace"])),
                "Expected bootloader fastboot, not fastbootd")
        require(re.search(r"current-slot:\s*a\b", self.device.fastboot(["getvar", "current-slot"])),
                "The reviewed conversion requires active slot A")

    def step_waiting_gbl(self):
        self.gbl_mode()
        require(not self.device.unlocked(), "Fresh GBL stage expected a locked bootloader; review previous unlock activity")
        print("Watch the phone and confirm bootloader unlock when prompted. This erases personal data.", flush=True)
        self.action("enable_oem_unlock", lambda: self.device.fastboot(["oem", "oem-unlock-toggle"]))
        self.action("request_bootloader_unlock", lambda: self.device.fastboot(["flashing", "unlock"], timeout=180))
        self.wait("waiting_unlock")

    def step_waiting_unlock(self):
        self.gbl_mode()
        require(self.device.unlocked(), "GBL dynamic device-info does not confirm unlocked")
        capacity = self.device.fastboot(["getvar", "partition-size:recovery_a"])
        match = re.findall(r"(?:\(bootloader\)\s*)?partition-size:recovery_a:\s*(0x[0-9a-fA-F]+|[0-9]+)\s*(?:\r?\n|$)", capacity)
        require(len(match) == 1 and int(match[0], 16 if match[0].startswith("0x") else 10) == 104857600,
                "GBL did not confirm the reviewed 100 MiB recovery_a capacity; no Recovery image was flashed")
        self.action("flash_recovery_a", lambda: self.with_artifact("recovery_img",
            lambda path: self.device.fastboot(["flash", "recovery_a", str(path)], timeout=300)))
        self.action("reboot_to_first_orangefox", lambda: self.device.fastboot(["reboot", "recovery"]))
        self.wait("waiting_recovery")

    def check_capacities(self):
        capacities = read_json(Path(__file__).with_name("hardware.json"))["firmware_capacities"]
        expected = {part + "_" + slot for part in self.manifest["images"] for slot in ("a", "b")}
        require(set(capacities) == expected and len(expected) == 100, "Prepared firmware inventory differs from the reviewed targets")
        for name, size in capacities.items():
            require(self.device.partition_size(name) == size, f"Firmware partition capacity changed: {name}")
        return capacities

    def backup(self):
        destination = self.root / "backup"
        require(not destination.exists(), "Backup directory already exists; no partial backup reuse")
        destination.mkdir(mode=0o700)
        names = sorted(self.check_capacities()) + ["abl_a", "abl_b", "recovery_a", "recovery_b", "efisp", "super", "metadata"]
        sizes = {name: self.device.partition_size(name) for name in names}
        require(shutil.disk_usage(self.root).free >= sum(sizes.values()) + 1024 ** 3,
                "Insufficient host space for full pre-conversion firmware backup plus 1 GiB reserve")
        records = []
        for index, name in enumerate(names, 1):
            print(f"Backing up {index}/{len(names)}: {name}", flush=True)
            item = self.device.backup_partition(name, destination / (name + ".img"))
            require(item["bytes"] == sizes[name], f"Backup size changed: {name}")
            records.append(item)
            atomic_json(destination / "partitions.json", records)
        gpts = []
        for letter in "abcdef":
            disk = "sd" + letter
            remote = "/tmp/changer-" + disk + ".gpt"
            self.device.shell(f"sgdisk --backup={remote} /dev/block/{disk}")
            expected = self.device.shell(f"sha256sum {remote}").split()[0]
            local = destination / (disk + ".gpt")
            self.device.pull(remote, local)
            require(local.stat().st_size > 0 and sha256_file(local) == expected, f"GPT backup hash mismatch: {disk}")
            gpts.append({"disk": disk, "path": str(local), "sha256": expected})
        policy.xbl_metadata((destination / "xbl_config_a.img").read_bytes())
        with zipfile.ZipFile(self.artifact("rom")) as package:
            policy.xbl_metadata(package.read("OTA_FILES_HERE/xbl_config.img"))
        manifest = {"partitions": records, "gpt": gpts, "scope": "Post-GBL and post-first-format; not a factory or personal-data backup"}
        atomic_json(destination / "manifest.json", manifest)
        self.state["backup_manifest_sha256"] = canonical_hash(manifest)
        self.save()

    def verify_backup(self):
        manifest = read_json(self.root / "backup/manifest.json")
        require(canonical_hash(manifest) == self.state["backup_manifest_sha256"], "Backup manifest changed")
        for item in manifest["partitions"] + manifest["gpt"]:
            path = Path(item["path"])
            require(path.is_file() and sha256_file(path) == item["sha256"], f"Backup is missing or changed: {path.name}")

    def step_waiting_recovery(self):
        gpt = policy.check_recovery(self.device, both=False)
        policy.check_cached_layout(self.device)
        require(self.device.partition_size("recovery_b") == 104857600, "Unexpected recovery_b capacity before OrangeFox ZIP")
        self.state["recovery_boot_id"] = self.device.boot_id()
        atomic_json(self.root / "gpt-before.json", gpt)
        self.action("backup_pre_conversion_firmware_and_gpt", self.backup)
        self.wait("waiting_ofox_sideload")

    def step_waiting_ofox_sideload(self):
        require(self.device.mode() == "sideload", "Enable OrangeFox ADB Sideload on the phone first")
        self.action("sideload_orangefox_zip", lambda: self.with_artifact("recovery_zip",
            lambda path: self.device.sideload(path, timeout=600)))
        self.wait("waiting_ofox_recovery")

    def step_waiting_ofox_recovery(self):
        self.fresh_boot()
        policy.check_recovery(self.device)
        policy.check_cached_layout(self.device)
        self.check_capacities()
        self.verify_backup()
        require(self.device.shell("test ! -s /tmp/openrecoveryscript && echo clear").strip() == "clear",
                "Recovery has a queued script; do not retry after a UI crash")
        setting = self.device.shell("twrp get tw_install_reboot")
        require(re.search(r"tw_install_reboot\s*=\s*0\b", setting), "Disable Recovery automatic reboot before conversion")
        mounts = self.device.shell("cat /proc/mounts")
        # The upstream installer handles normal /data unmounts. Mounted dynamic
        # filesystems have caused a touch-service hold in the real case.
        blocked = {"/system_root", "/system", "/system_ext", "/vendor", "/product", "/odm"}
        require(not any(len(line.split()) >= 2 and line.split()[1] in blocked for line in mounts.splitlines()),
                "A firmware filesystem is mounted; unmount manually and audit holders before starting a new run. No service will be killed automatically")
        self.recovery_log("before-conversion")
        self.wait("waiting_rom_sideload")

    def step_waiting_rom_sideload(self):
        require(self.device.mode() == "sideload", "Enable OrangeFox ADB Sideload on the phone first")
        print("Phone prompts: Volume Up CONTINUE; then Volume Down ABL=NO. Never select ABL=YES.", flush=True)
        self.action("sideload_cn2eu_rom", lambda: self.with_artifact("rom",
            lambda path: self.device.sideload(path, timeout=5400)))
        self.wait("waiting_install_result")

    def step_waiting_install_result(self):
        require(self.device.mode() == "recovery", "Return to Recovery ADB without rebooting")
        self.same_boot()
        after = self.recovery_log("after-conversion")
        policy.check_install_log((self.root / "before-conversion.log").read_text(errors="replace"), after)
        # Read GPT on disk now, but don't demand updated kernel block sizes until
        # the fresh Recovery boot; the upstream installer writes by disk offset.
        atomic_json(self.root / "gpt-after-install.json", policy.check_recovery(self.device, eu=True))
        self.action("reboot_after_conversion", lambda: self.device.adb(["reboot", "recovery"]))
        self.wait("waiting_fresh_recovery")

    def verify_written_images(self):
        records = []
        for part, image in sorted(self.manifest["images"].items()):
            for slot in ("a", "b"):
                name = part + "_" + slot
                print(f"Verifying {name}", flush=True)
                actual = self.device.hash_partition(name, image["size"])
                require(actual == image["sha256"], f"Firmware readback mismatch: {name}")
                records.append({"partition": name, "bytes": image["size"], "sha256": actual})
                atomic_json(self.root / "readback-firmware.json", records)
        extents = []
        for index, extent in enumerate(self.manifest["super"]["extents"]):
            if extent["sha256"] is None:
                continue
            print(f"Verifying super extent {index + 1}", flush=True)
            actual = self.device.hash_partition("super", extent["length"], extent["offset"])
            require(actual == extent["sha256"], f"super readback mismatch at offset {extent['offset']}")
            extents.append({**extent, "actual_sha256": actual})
            atomic_json(self.root / "readback-super.json", extents)
        require(extents, "No defined super extents verified")

    def step_waiting_fresh_recovery(self):
        self.fresh_boot()
        atomic_json(self.root / "gpt-fresh.json", policy.check_recovery(self.device, eu=True))
        policy.check_cached_layout(self.device, eu=True)
        self.check_capacities()
        self.verify_written_images()
        self.recovery_log("before-format")
        self.wait("waiting_format")

    def step_waiting_format(self):
        require(self.device.mode() == "recovery", "Expected Recovery after manual Format Data")
        self.same_boot()
        after = self.recovery_log("after-format")
        policy.check_format_log((self.root / "before-format.log").read_text(errors="replace"), after)
        policy.check_cached_layout(self.device, eu=True)
        self.action("reboot_after_format", lambda: self.device.adb(["reboot", "recovery"]))
        self.wait("waiting_formatted_recovery")

    def step_waiting_formatted_recovery(self):
        self.fresh_boot()
        policy.check_recovery(self.device, eu=True)
        policy.check_cached_layout(self.device, eu=True)
        mounts = self.device.shell("cat /proc/mounts").splitlines()
        require(any(len(row.split()) >= 3 and row.split()[1:3] == ["/data", "f2fs"] for row in mounts),
                "Formatted /data is not mounted as f2fs in fresh Recovery")
        self.action("first_eu_android_boot", lambda: self.device.adb(["reboot"]))
        self.wait("waiting_android")

    def step_waiting_android(self):
        result = policy.check_android(self.device, eu=True)
        require(self.device.shell("settings get secure user_setup_complete").strip() == "1", "Complete Android setup first")
        atomic_json(self.root / "android-after.json", result)
        self.state.update(stage="complete", status="complete", action=None)
        self.save()
