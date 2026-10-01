import hashlib
import json
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from changer.core import ReviewRequired
from changer.device import Device, parse_fastboot_unlocked, parse_gpt, parse_props


def device(tmp_path: Path) -> Device:
    return Device(Path("/tools/adb"), Path("/tools/fastboot"), tmp_path / "commands.jsonl", "SERIAL_1234")


class DeviceParserTests(unittest.TestCase):
    def test_parse_getprop_and_reject_malformed_or_duplicate_lines(self):
        self.assertEqual(parse_props("[ro.bootmode]: [recovery]\n[ro.product.model]: [PMA110512]\n"), {
            "ro.bootmode": "recovery", "ro.product.model": "PMA110512"
        })
        with self.assertRaises(ReviewRequired):
            parse_props("not a getprop row")
        with self.assertRaises(ReviewRequired):
            parse_props("[x]: [one]\n[x]: [two]")


    def test_parse_gpt_requires_unique_complete_fields_and_valid_range(self):
        raw = """First sector: 385772 (at 1.5 GiB)
Last sector: 5378795 (at 21.9 GiB)
Partition GUID code: 89A12DE1-5E41-4CB3-8B4C-B1441EB5DA38 (Linux filesystem)
Partition name: 'super'
Attribute flags: 0000000000000000
"""
        self.assertEqual(parse_gpt(raw), {
            "start": 385772,
            "end": 5378795,
            "type": "89A12DE1-5E41-4CB3-8B4C-B1441EB5DA38",
            "name": "super",
            "attributes": "0000000000000000",
        })
        with self.assertRaises(ReviewRequired):
            parse_gpt(raw.replace("Last sector: 5378795", "Last sector: 385771"))
        with self.assertRaises(ReviewRequired):
            parse_gpt(raw.replace("Partition name: 'super'", ""))
        with self.assertRaises(ReviewRequired):
            parse_gpt(raw.replace("89A12DE1-5E41-4CB3-8B4C-B1441EB5DA38", "not-a-guid"))


    def test_unlocked_uses_dynamic_oem_device_info_output(self):
        self.assertTrue(parse_fastboot_unlocked("(bootloader) Device unlocked: true\n"))
        self.assertFalse(parse_fastboot_unlocked("(bootloader) Device unlocked: false\n"))
        with self.assertRaises(ReviewRequired):
            parse_fastboot_unlocked("(bootloader) Device unlocked: yes\n")
        with self.assertRaises(ReviewRequired):
            parse_fastboot_unlocked("Device unlocked: true\nDevice unlocked: false\n")
        with self.assertRaises(ReviewRequired):
            parse_fastboot_unlocked("(bootloader) Device unlocked: true\n(bootloader) Device unlocked: false\n")

    def test_props_queries_only_the_fixed_policy_allowlist(self):
        text = "".join(f"[{key}]: [value]\n" for key in (
            "ro.boot.prjname", "ro.product.model", "ro.product.name", "ro.build.display.id",
            "sys.boot_completed", "ro.boot.slot_suffix", "ro.boot.vbmeta.device_state",
            "ro.boot.flash.locked", "ro.oplus.image.my_region.type"))
        def fake_shell(command, timeout=60):
            self.assertIn("for key in", command)
            self.assertIn("getprop \"$key\"", command)
            self.assertNotEqual(command.strip(), "getprop")
            return text
        with tempfile.TemporaryDirectory() as temp_dir:
            d = Device(Path("/adb"), Path("/fastboot"), Path(temp_dir) / "props.log", "SERIAL_1234")
            with patch.object(d, "shell", side_effect=fake_shell):
                self.assertEqual(len(d.props()), 9)


class DeviceGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dev = device(self.root)

    def test_rejects_other_or_multiple_transports_before_adb_call(self):
        with patch.object(self.dev, "_run", return_value=(0, "OTHER_SERIAL device\n", "")):
            with self.assertRaisesRegex(ReviewRequired, "Unexpected adb transport"):
                self.dev.adb(["shell", "getprop"])
        with patch.object(self.dev, "_run", return_value=(0, "SERIAL_1234 device\nOTHER_SERIAL device\n", "")):
            with self.assertRaisesRegex(ReviewRequired, "Multiple adb transports"):
                self.dev.adb(["shell", "getprop"])
        with patch.object(self.dev, "_run", return_value=(0, "SERIAL_1234 device\nSERIAL_1234 device\n", "")):
            with self.assertRaisesRegex(ReviewRequired, "Multiple adb transports"):
                self.dev.adb(["shell", "getprop"])
        with patch.object(self.dev, "_run", return_value=(0, "SERIAL_1234 unauthorized\n", "")):
            with self.assertRaisesRegex(ReviewRequired, "authorization"):
                self.dev.adb(["shell", "getprop"])


    def test_command_failure_and_transport_selector_are_rejected(self):
        with patch.object(self.dev, "_transport", side_effect=lambda protocol: "device" if protocol == "adb" else "disconnected"), \
             patch.object(self.dev, "_run", return_value=(1, "", "permission denied")):
            with self.assertRaisesRegex(ReviewRequired, "ADB command failed"):
                self.dev.adb(["shell", "getprop"])
        with self.assertRaisesRegex(ReviewRequired, "may not select a transport"):
            self.dev.adb(["-s", "OTHER_SERIAL", "shell", "id"])


    def _shim(self, source):
        script = self.root / "fake-adb"
        script.write_text(f"#!{sys.executable}\n{source}\n")
        script.chmod(0o755)
        self.dev.adb_path = str(script)
        return script

    def test_incomplete_backup_never_returns_success(self):
        self._shim("import sys; sys.stdout.buffer.write(b'abc')")
        target = self.root / "partial.bin"
        with patch.object(self.dev, "partition_size", return_value=4), \
             patch.object(self.dev, "_exclusive_transport", return_value="device"), \
             patch.object(self.dev, "hash_partition") as device_hash:
            with self.assertRaisesRegex(ReviewRequired, "Short read"):
                self.dev.backup_partition("boot_a", target)
            device_hash.assert_not_called()
        self.assertFalse(target.exists())

    def test_stalled_stream_is_killed_and_partial_file_removed(self):
        self._shim("import time; time.sleep(5)")
        target = self.root / "partial.bin"
        with self.assertRaisesRegex(ReviewRequired, "timed out"):
            self.dev._stream_partition("boot_a", target, 4, timeout=1, stall_timeout=0.1)
        self.assertFalse(target.exists())
        self.assertTrue(self.dev.log.is_file())

    def test_exact_backup_reports_only_after_device_hash_matches(self):
        payload = b"data"
        digest = hashlib.sha256(payload).hexdigest()
        self._shim(f"import sys; sys.stdout.buffer.write({payload!r})")
        target = self.root / "backup.img"
        with patch.object(self.dev, "partition_size", return_value=len(payload)), \
             patch.object(self.dev, "_exclusive_transport", return_value="device"), \
             patch.object(self.dev, "hash_partition", return_value=digest):
            result = self.dev.backup_partition("boot_a", target)
        self.assertEqual(result["bytes"], 4)
        self.assertEqual(result["sha256"], digest)
        self.assertEqual(result["device_sha256"], digest)
        self.assertEqual(target.read_bytes(), payload)

    def test_device_hash_mismatch_does_not_claim_verified_backup(self):
        self._shim("import sys; sys.stdout.buffer.write(b'data')")
        target = self.root / "backup.img"
        with patch.object(self.dev, "partition_size", return_value=4), \
             patch.object(self.dev, "_exclusive_transport", return_value="device"), \
             patch.object(self.dev, "hash_partition", return_value="0" * 64):
            with self.assertRaisesRegex(ReviewRequired, "hash mismatch"):
                self.dev.backup_partition("boot_a", target)

    def test_subprocess_timeout_is_bounded_and_logged(self):
        with self.assertRaisesRegex(ReviewRequired, "timed out"):
            self.dev._run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.1)
        row = json.loads(self.dev.log.read_text().splitlines()[-1])
        self.assertIn("timed out", row["error"])
        self.assertLess(row["duration_seconds"], 3)

    def test_subprocess_output_limit_is_rejected_and_logged_bounded(self):
        with self.assertRaisesRegex(ReviewRequired, "output exceeded"):
            self.dev._run([sys.executable, "-c", "print('x' * 100000)"], timeout=3)
        row = json.loads(self.dev.log.read_text().splitlines()[-1])
        self.assertLessEqual(len(row["stdout"].encode()), 64 * 1024)
        self.assertIn("output exceeded", row["error"])

    def test_fastboot_rc_zero_failure_and_dual_mode_are_rejected(self):
        with patch.object(self.dev, "_transport", side_effect=lambda protocol: "fastboot" if protocol == "fastboot" else "disconnected"), \
             patch.object(self.dev, "_run", return_value=(0, "(bootloader) FAILED (remote: denied)\n", "")):
            with self.assertRaisesRegex(ReviewRequired, "reported failure"):
                self.dev.fastboot(["getvar", "current-slot"])
        with patch.object(self.dev, "_transport", side_effect=lambda protocol: "device" if protocol == "adb" else "fastboot"):
            with self.assertRaisesRegex(ReviewRequired, "Multiple USB transports"):
                self.dev.mode()

    def test_hash_partition_streams_without_device_tempfiles_and_checks_pipefail(self):
        expected = "a" * 64

        def fake_shell(command, timeout=60):
            if command.startswith("blockdev --getsize64"):
                return "300000"
            self.assertIn("set -o pipefail || exit $?", command)
            self.assertNotIn("of=/tmp", command)
            self.assertIn("head -c 278328", command)
            return f"{expected} -"

        with patch.object(self.dev, "shell", side_effect=fake_shell):
            self.assertEqual(self.dev.hash_partition("abl_a", 278328), expected)

    def test_invalid_serial_rejected_at_construction(self):
        with self.assertRaises(ReviewRequired):
            Device(Path("/adb"), Path("/fastboot"), self.root / "log", "bad serial")

    def test_capture_gpt_includes_raw_table_and_resolved_aliases(self):
        super_info = """First sector: 385772 (at 1.5 GiB)
Last sector: 5188331 (at 20 GiB)
Partition GUID code: 89A12DE1-5E41-4CB3-8B4C-B1441EB5DA38 (Linux filesystem)
Partition name: 'super'
Attribute flags: 0000000000000000
"""
        userdata_info = """First sector: 5188332 (at 20 GiB)
Last sector: 124070906 (at 473 GiB)
Partition GUID code: 1B81E7E6-F50D-419B-A739-2AEEF8DA3335 (Linux filesystem)
Partition name: 'userdata'
Attribute flags: 0000000000000000
"""
        def fake_shell(command, timeout=60):
            if "--getss" in command:
                return "4096"
            if "--getsize64" in command:
                return str(124070912 * 4096)
            if "readlink -f" in command:
                return "/dev/block/sda14" if command.endswith("super") else "/dev/block/sda15"
            if "--info=14" in command:
                return super_info
            if "--info=15" in command:
                return userdata_info
            if "--verify" in command:
                return "No problems found. 0 free sectors."
            if "--print" in command:
                return "Disk /dev/block/sda: 124070912 sectors\nNumber Start End Name Code GUID\n"
            raise AssertionError(command)
        with patch.object(self.dev, "shell", side_effect=fake_shell):
            report = self.dev.capture_gpt()
        self.assertEqual(report["super_device"], "/dev/block/sda14")
        self.assertEqual(report["userdata_device"], "/dev/block/sda15")
        self.assertIn("Number Start End", report["table"])


if __name__ == "__main__":
    unittest.main()
