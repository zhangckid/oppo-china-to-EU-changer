from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import Mock, patch

from changer.core import ReviewRequired, atomic_json, canonical_hash, execution_lock, read_json, sha256_file
from changer import policy
from changer.cli import main
from changer.runner import Runner, create_run, load_state, save_state, status
from tests.test_policy import layout, metadata


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / "run"
        inputs = {}
        for name in ("rom", "gbl_apk", "recovery_img", "recovery_zip"):
            path = self.root / name
            path.write_bytes(name.encode())
            inputs[name] = {"path": str(path), "size": path.stat().st_size, "sha256": sha256_file(path)}
        capacities = read_json(Path(policy.__file__).with_name("hardware.json"))["firmware_capacities"]
        self.capacities = capacities
        self.manifest = {"inputs": inputs, "images": {
            name[:-2]: {"size": 4096, "sha256": "1" * 64}
            for name in capacities if name.endswith("_a")},
            "super": {"extents": [
                {"offset": 0, "length": 4096, "sha256": "2" * 64, "kind": "raw"},
                {"offset": 4096, "length": 4096, "sha256": None, "kind": "dont_care"}]}}
        create_run(self.run, self.manifest)
        self.device = Mock()
        self.device.mode.return_value = "android"
        self.info = {name: {"path": "/fake/" + name, "sha256": "fake", "version": "37.0.1"}
                     for name in ("adb", "fastboot")}
        self.tools_patch = patch("changer.runner.tools_info", return_value=self.info)
        self.tools_patch.start()
        self.addCleanup(self.tools_patch.stop)
        self.addCleanup(patch.stopall)

    def runner(self):
        return Runner(self.run, device_factory=lambda *args: self.device)

    def set_stage(self, stage, **extra):
        state = load_state(self.run)
        state.update(stage=stage, status="waiting", adb_serial="TEST_ADB", fastboot_serial="TEST_GBL",
                     recovery_boot_id="boot-1", **extra)
        save_state(self.run, state)

    def execute(self, stage="prepared"):
        serial = "TEST_GBL" if stage in {"waiting_gbl", "waiting_unlock"} else "TEST_ADB"
        with redirect_stdout(io.StringIO()):
            return self.runner().execute(command="run" if stage == "prepared" else "resume", serial=serial,
                    platform_tools="/fake", ack_erase=serial if stage == "prepared" else None,
                    ack_stage=None if stage == "prepared" else stage)

    def test_preview_and_status_never_construct_device_or_execute_tools(self):
        with patch("changer.runner.Device", side_effect=AssertionError("device accessed")), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(main(["run", str(self.run)]), 0)
            self.assertEqual(main(["resume", str(self.run)]), 0)
            self.assertEqual(main(["status", str(self.run)]), 0)

    def test_prepare_refuses_existing_directory(self):
        with self.assertRaises(ReviewRequired):
            create_run(self.run, self.manifest)

    def test_acknowledgments_are_required_and_do_not_advance_state(self):
        with self.assertRaises(ReviewRequired):
            self.runner().execute(command="run", serial="TEST_ADB", platform_tools="/fake")
        self.device.adb.assert_not_called()
        self.assertEqual(status(self.run)["stage"], "prepared")

    def test_manifest_and_journal_changes_rejected(self):
        data = copy.deepcopy(self.manifest)
        data["inputs"]["rom"]["sha256"] = "0" * 64
        atomic_json(self.run / "manifest.json", data)
        with self.assertRaises(ReviewRequired):
            self.runner()
        envelope = read_json(self.run / "state.json")
        envelope["state"]["stage"] = "complete"
        atomic_json(self.run / "state.json", envelope)
        with self.assertRaises(ReviewRequired):
            load_state(self.run)

    def test_interrupted_intent_is_terminal_and_never_replayed(self):
        self.set_stage("waiting_rom_sideload")
        state = load_state(self.run)
        state.update(status="executing", action="sideload_cn2eu_rom")
        save_state(self.run, state)
        with self.assertRaisesRegex(ReviewRequired, "no action will be replayed"):
            self.execute("waiting_rom_sideload")
        self.assertEqual(status(self.run)["stage"], "review_required")
        self.device.sideload.assert_not_called()

    def test_write_intent_is_persisted_before_install_and_interrupt_stops(self):
        patch("changer.runner.policy.check_android", return_value={}).start()
        def interrupt(args, timeout):
            state = load_state(self.run)
            self.assertEqual((state["status"], state["action"]), ("executing", "install_gbl_apk"))
            raise KeyboardInterrupt()
        self.device.adb.side_effect = interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.execute()
        self.assertEqual(status(self.run)["stage"], "review_required")
        self.device.fastboot.assert_not_called()

    def test_changed_artifact_and_wrong_serial_stop_before_flash(self):
        self.set_stage("waiting_rom_sideload")
        self.device.mode.return_value = "sideload"
        Path(self.manifest["inputs"]["rom"]["path"]).write_bytes(b"bad")
        with self.assertRaises(ReviewRequired):
            self.execute("waiting_rom_sideload")
        self.device.sideload.assert_not_called()
        self.set_stage("waiting_unlock")
        with self.assertRaisesRegex(ReviewRequired, "Serial differs"):
            self.runner().execute(command="resume", serial="OTHER_GBL", platform_tools="/fake", ack_stage="waiting_unlock")
        self.device.fastboot.assert_not_called()

    def test_artifact_lease_anchors_original_content_and_detects_changes(self):
        runner = self.runner()
        original = Path(self.manifest["inputs"]["rom"]["path"])
        def replace_external(lease):
            original.rename(original.with_suffix(".old"))
            original.write_bytes(b"unverified replacement")
            self.assertEqual(lease.read_bytes(), b"rom")
        with self.assertRaisesRegex(ReviewRequired, "during transfer"):
            runner.with_artifact("rom", replace_external)
        original.unlink()
        original.with_suffix(".old").rename(original)
        def modify_content(lease):
            original.write_bytes(b"BAD")
        with self.assertRaisesRegex(ReviewRequired, "during transfer"):
            runner.with_artifact("rom", modify_content)
        self.assertFalse(list(self.run.glob(".artifact-*")))

    def test_wrong_recovery_capacity_stops_before_fastboot_flash(self):
        self.set_stage("waiting_unlock")
        self.device.mode.return_value = "fastboot"
        self.device.unlocked.return_value = True
        self.device.fastboot.side_effect = ["is-userspace: no", "current-slot: a", "partition-size:recovery_a: 0x1000"]
        with self.assertRaisesRegex(ReviewRequired, "100 MiB"):
            self.execute("waiting_unlock")
        self.assertFalse(any(c.args[0][0] == "flash" for c in self.device.fastboot.call_args_list))

    def test_sideload_nonzero_never_advances_or_reboots(self):
        self.set_stage("waiting_rom_sideload")
        self.device.mode.return_value = "sideload"
        self.device.sideload.side_effect = ReviewRequired("USB disconnected during write")
        with self.assertRaises(ReviewRequired):
            self.execute("waiting_rom_sideload")
        self.assertEqual(status(self.run)["stage"], "review_required")
        self.device.adb.assert_not_called()

    def test_unchanged_boot_id_blocks_fresh_layout_verification(self):
        self.set_stage("waiting_fresh_recovery")
        self.device.boot_id.return_value = "boot-1"
        with self.assertRaisesRegex(ReviewRequired, "has not rebooted"):
            self.execute("waiting_fresh_recovery")
        self.device.hash_partition.assert_not_called()

    def test_stale_installer_log_and_abl_yes_cannot_reboot(self):
        for tail in ("Installation complete\n", "ABL will be flashed\nInstallation complete\n"):
            self.set_stage("waiting_install_result")
            self.device.mode.return_value = "recovery"
            self.device.boot_id.return_value = "boot-1"
            (self.run / "before-conversion.log").write_text("before\n")
            with patch.object(Runner, "recovery_log", return_value="before\n" + tail), \
                 self.assertRaises(ReviewRequired):
                self.execute("waiting_install_result")
            self.device.adb.assert_not_called()

    def test_readback_mismatch_blocks_format_gate(self):
        self.set_stage("waiting_fresh_recovery")
        self.device.boot_id.return_value = "boot-2"
        self.device.hash_partition.return_value = "0" * 64
        with patch("changer.runner.policy.check_recovery", return_value=layout(True)), \
             patch("changer.runner.policy.check_cached_layout"), patch.object(Runner, "check_capacities"), \
             self.assertRaisesRegex(ReviewRequired, "readback mismatch"):
            self.execute("waiting_fresh_recovery")
        self.device.adb.assert_not_called()
        self.assertEqual(status(self.run)["stage"], "review_required")

    def test_execution_lock_blocks_another_run(self):
        with patch("changer.core.Path.home", return_value=self.root), execution_lock():
            with self.assertRaisesRegex(ReviewRequired, "execution lock"):
                with execution_lock():
                    self.fail("second lock acquired")

    def test_insufficient_backup_space_blocks_partition_streams(self):
        runner = self.runner()
        runner.device = self.device
        self.device.partition_size.return_value = 4096
        with patch.object(Runner, "check_capacities", return_value=self.capacities), \
             patch("changer.runner.shutil.disk_usage", return_value=Mock(free=1)), \
             self.assertRaisesRegex(ReviewRequired, "Insufficient host space"):
            runner.backup()
        self.device.backup_partition.assert_not_called()

    def test_backup_requires_all_107_partitions_and_six_verified_gpts(self):
        runner = self.runner()
        runner.device = self.device
        data = metadata()
        self.device.partition_size.return_value = len(data)
        def backup(name, path):
            path.write_bytes(data)
            sha = sha256_file(path)
            return {"partition": name, "path": str(path), "bytes": len(data), "sha256": sha, "device_sha256": sha}
        self.device.backup_partition.side_effect = backup
        sha = hashlib.sha256(b"gpt fixture").hexdigest()
        self.device.shell.side_effect = lambda command: sha + "  -" if command.startswith("sha256sum") else ""
        self.device.pull.side_effect = lambda remote, local: local.write_bytes(b"gpt fixture")
        package = self.root / "backup-test.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("OTA_FILES_HERE/xbl_config.img", data)
        with patch.object(Runner, "check_capacities", return_value=self.capacities), \
             patch.object(Runner, "artifact", return_value=package), redirect_stdout(io.StringIO()):
            runner.backup()
        manifest = read_json(self.run / "backup/manifest.json")
        self.assertEqual(len(manifest["partitions"]), 107)
        self.assertEqual(len(manifest["gpt"]), 6)
        runner.verify_backup()
        (self.run / "backup/metadata.img").write_bytes(b"corrupt")
        with self.assertRaisesRegex(ReviewRequired, "missing or changed"):
            runner.verify_backup()

    def test_full_host_workflow_with_manual_handoffs_and_defined_super_extent(self):
        """Integration through all checkpoints; mocked reads are not hardware validation."""
        patch("changer.runner.policy.check_android", return_value={}).start()
        patch("changer.runner.policy.check_recovery", side_effect=lambda *a, **kw: layout(kw.get("eu", False))).start()
        patch("changer.runner.policy.check_cached_layout").start()
        patch.object(Runner, "backup", return_value=None).start()
        patch.object(Runner, "verify_backup", return_value=None).start()
        self.device.adb.return_value = "Success"
        self.device.partition_size.side_effect = lambda name: 104857600 if name == "recovery_b" else self.capacities[name]
        self.device.fastboot.side_effect = lambda args, **kw: {"is-userspace": "is-userspace: no", "current-slot": "current-slot: a", "partition-size:recovery_a": "partition-size:recovery_a: 0x6400000"}.get(args[-1], "OKAY")
        self.device.shell.side_effect = lambda cmd: {
            "test ! -s /tmp/openrecoveryscript && echo clear": "clear",
            "twrp get tw_install_reboot": "tw_install_reboot = 0",
            "cat /proc/mounts": "/dev/block/sda15 /data f2fs rw 0 0\n",
            "settings get secure user_setup_complete": "1"}[cmd]
        self.device.hash_partition.side_effect = lambda name, *args: "2" * 64 if name == "super" else "1" * 64
        logs = {
            "before-conversion": "start\n",
            "after-conversion": "start\nKeeping the current ABL\nInstallation complete\n",
            "before-format": "fresh recovery\n",
            "after-format": "fresh recovery\nI:mkfs_f2fs command: make_f2fs /dev/block/sda15 1\nInfo: format successful\nI:mkfs_f2fs command: make_f2fs /dev/block/sda10 1\nInfo: format successful\n"}
        def log(runner, name):
            content = logs[name]
            (runner.root / (name + ".log")).write_text(content)
            return content
        patch.object(Runner, "recovery_log", log).start()
        expected = ["prepared", "waiting_gbl", "waiting_unlock", "waiting_recovery", "waiting_ofox_sideload",
                    "waiting_ofox_recovery", "waiting_rom_sideload", "waiting_install_result", "waiting_fresh_recovery",
                    "waiting_format", "waiting_formatted_recovery", "waiting_android", "complete"]
        for index, stage in enumerate(expected[:-1]):
            self.device.mode.return_value = "fastboot" if stage in {"waiting_gbl", "waiting_unlock"} else (
                "sideload" if stage in {"waiting_ofox_sideload", "waiting_rom_sideload"} else "recovery")
            self.device.unlocked.return_value = stage != "waiting_gbl"
            if stage == "waiting_recovery":
                self.device.boot_id.return_value = "boot-1"
            if stage == "waiting_ofox_recovery":
                self.device.boot_id.return_value = "boot-2"
            if stage == "waiting_fresh_recovery":
                self.device.boot_id.return_value = "boot-3"
            if stage == "waiting_formatted_recovery":
                self.device.boot_id.return_value = "boot-4"
            with self.subTest(stage=stage):
                result = self.execute(stage)
                self.assertEqual(result["stage"], expected[index + 1])
        self.assertEqual(status(self.run)["status"], "complete")
        self.assertEqual(len(read_json(self.run / "readback-firmware.json")), 100)
        self.assertEqual(len(read_json(self.run / "readback-super.json")), 1)
        # Never sideload twice on failure, write ABL, format data, or relock.
        self.assertEqual(self.device.sideload.call_count, 2)
        self.assertEqual([call.args[0] for call in self.device.fastboot.call_args_list if call.args[0][0] == "flash"][0][:2],
                         ["flash", "recovery_a"])


if __name__ == "__main__":
    unittest.main()
