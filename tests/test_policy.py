import copy
import struct
import unittest
from pathlib import Path
from unittest.mock import Mock

from changer.core import ReviewRequired, read_json
from changer import policy


def layout(eu=False):
    end = 5378795 if eu else 5188331
    rows = read_json(Path(policy.__file__).with_name("hardware.json"))["sda_fixed_partitions"]
    rows.update({"14": dict(start=385772, end=end, code="FFFF", name="super"),
                 "15": dict(start=end+1, end=124070906, code="A03A", name="userdata")})
    table = "\n".join(f"{number} {row['start']} {row['end']} 1.0 GiB {row['code']} {row['name']}" for number, row in rows.items())
    return {"sector_bytes": 4096, "device_bytes": 124070912 * 4096,
            "table": table,
            "super_device": "/dev/block/sda14", "userdata_device": "/dev/block/sda15",
            "verify": "No problems found.", "partitions": {
                "14": dict(start=385772, end=end, name="super", type="89A12DE1-5E41-4CB3-8B4C-B1441EB5DA38", attributes="0000000000000000"),
                "15": dict(start=end + 1, end=124070906, name="userdata", type="1B81E7E6-F50D-419B-A739-2AEEF8DA3335", attributes="0000000000000000")}}


def metadata(arb=0):
    data = bytearray(256)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<Q", data, 32, 64)
    struct.pack_into("<HH", data, 54, 56, 1)
    struct.pack_into("<II6Q", data, 64, 0, 0, 128, 0, 0, 100, 0, 0)
    struct.pack_into("<5I", data, 128, 1, 0, 0, 12, 0)
    struct.pack_into("<3I", data, 164, 3, 0, arb)
    return bytes(data)


class PolicyTests(unittest.TestCase):
    def test_exact_cn_and_eu_layouts(self):
        policy.check_layout(layout())
        policy.check_layout(layout(True), eu=True)
        with self.assertRaises(ReviewRequired):
            policy.check_layout(layout(True))

    def test_geometry_guid_capacity_and_attribute_changes_are_rejected(self):
        edits = [("sector_bytes", 512), ("device_bytes", 1024), ("super_device", "/dev/block/sdb14")]
        for key, value in edits:
            candidate = layout()
            candidate[key] = value
            with self.subTest(key=key), self.assertRaises(ReviewRequired):
                policy.check_layout(candidate)
        for key, value in [("start", 1), ("end", 124070905), ("type", "unknown"), ("attributes", "0000000000000001")]:
            candidate = layout()
            candidate["partitions"]["15"][key] = value
            with self.subTest(key=key), self.assertRaises(ReviewRequired):
                policy.check_layout(candidate)

    def test_oem_metadata_is_not_a_downgrade_bypass(self):
        self.assertEqual(policy.xbl_metadata(metadata()), (3, 0, 0))
        for value in (metadata(1), metadata()[:150], b"not ELF"):
            with self.assertRaises(ReviewRequired):
                policy.xbl_metadata(value)

    def test_other_physical_partition_changes_or_extra_entries_rejected(self):
        for table in (layout()["table"] + "\n16 1 2 1 GiB FFFF surprise",
                      layout()["table"].replace("persist", "renamed")):
            changed = layout()
            changed["table"] = table
            with self.assertRaisesRegex(ReviewRequired, "GPT inventory"):
                policy.check_layout(changed)

    def test_unparsed_extra_gpt_entry_is_not_ignored(self):
        changed = layout()
        changed["table"] += "\n16 1 2 1 GiB FFFF name with spaces"
        with self.assertRaisesRegex(ReviewRequired, "Unrecognized"):
            policy.check_layout(changed)

    def test_installer_completion_requires_fresh_log_and_abl_no(self):
        before = "Recovery boot\nold Installation complete\n"
        good = before + "Keeping the current ABL\nInstallation complete\n"
        policy.check_install_log(before, good)
        for bad in (before, "new boot\n" + good, before + "Installation complete\n",
                    good + "ABL will be flashed\n", good + "ERROR: writer failed\n"):
            with self.assertRaises(ReviewRequired):
                policy.check_install_log(before, bad)

    def test_format_success_must_belong_to_both_new_formatter_invocations(self):
        before = "Info: format successful\n"
        userdata = "I:mkfs_f2fs command: /system/bin/make_f2fs /dev/block/sda15 118692107\nInfo: format successful\n"
        metadata_log = "I:mkfs_f2fs command: /system/bin/make_f2fs /dev/block/sda10 16380\nInfo: format successful\n"
        policy.check_format_log(before, before + userdata + metadata_log)
        for bad in (before + userdata, before + metadata_log,
                    before + userdata.replace("Info: format successful\n", "") + metadata_log):
            with self.assertRaises(ReviewRequired):
                policy.check_format_log(before, bad)

    def test_stale_kernel_partition_sizes_rejected(self):
        device = Mock()
        device.partition_size.return_value = policy.CN_SUPER
        with self.assertRaisesRegex(ReviewRequired, "fresh Recovery"):
            policy.check_cached_layout(device, eu=True)

    def test_already_eu_android_rejected_before_conversion(self):
        device = Mock()
        device.mode.return_value = "android"
        device.props.return_value = {"ro.product.model": "CPH2841", "ro.build.display.id": policy.EU_VERSION}
        device.shell.side_effect = [policy.KERNEL, str(124070912 * 8)]
        with self.assertRaises(ReviewRequired):
            policy.check_android(device)


if __name__ == "__main__":
    unittest.main()
