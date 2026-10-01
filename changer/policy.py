"""The single reviewed device and layout, not a generic OPPO flashing policy."""
import re
import struct
from pathlib import Path

from .core import read_json, require

CN_VERSION = "PMA110_16.0.9.403(CN01)"
EU_VERSION = "CPH2841_16.0.9.403(EX01)"
KERNEL = "6.12.58-android16-6-g7704a1ae279b-ab15213644-4k"
RECOVERY_SHA = "369fb7ef9ec2e69dd884409f3eec5349ceba8dd98e6e460f5d6871cf7246eaa4"
PROTECTED = {
    "abl_a": (278328, "4ad7f1db0c92f0a358e28bf18170a20533011299827d8d9a25cffd2218f1415d"),
    "abl_b": (278328, "4ad7f1db0c92f0a358e28bf18170a20533011299827d8d9a25cffd2218f1415d"),
    "efisp": (1495576, "35560f8e6fd706a3768f26f692467491c90425881a8d80bf237341215c04cac5"),
}
CN_SUPER = 19671285760
EU_SUPER = 20451426304


def exact_props(props, expected):
    for name, value in expected.items():
        require(props.get(name) == value, f"Unexpected {name}: {props.get(name)!r}; expected {value!r}")


def check_android(device, *, eu=False):
    require(device.mode() == "android", "Expected authorized Android ADB")
    props = device.props()
    expected = {"ro.boot.prjname": "25021", "ro.product.model": "CPH2841" if eu else "PMA110",
                "ro.build.display.id": EU_VERSION if eu else CN_VERSION, "sys.boot_completed": "1"}
    if eu:
        expected.update({"ro.product.name": "CPH2841EEA", "ro.boot.slot_suffix": "_a",
                         "ro.boot.vbmeta.device_state": "unlocked",
                         "ro.oplus.image.my_region.type": "EUEX_all"})
    else:
        expected.update({"ro.boot.vbmeta.device_state": "locked", "ro.boot.flash.locked": "1",
                         "ro.boot.slot_suffix": "_a"})
        require(device.shell("uname -r").strip() == KERNEL, "Kernel is outside the GBL APK compatibility pin")
        # Accessible sysfs evidence before temporary root changes the boot chain.
        sectors = device.shell("cat /sys/class/block/sda/size").strip()
        require(sectors.isdigit() and int(sectors) == 124070912 * 8,
                "Requires the reviewed 512GB disk geometry")
    exact_props(props, expected)
    return props


def check_layout(gpt, eu=False):
    require(gpt["sector_bytes"] == 4096, "Physical sector size changed")
    require(gpt["device_bytes"] == 124070912 * 4096, "Physical disk size changed")
    require(gpt["super_device"] == "/dev/block/sda14" and
            gpt["userdata_device"] == "/dev/block/sda15", "Unexpected super/userdata device mapping")
    require("No problems found" in gpt["verify"], "GPT verification did not pass")
    end = 5378795 if eu else 5188331
    table = {}
    for line in gpt["table"].splitlines():
        match = re.fullmatch(r"\s*(\d+)\s+(\d+)\s+(\d+)\s+\S+\s+\S+\s+([A-F0-9]{4})\s+(\S+)\s*", line)
        if re.match(r"^\s*\d+\s", line):
            require(match is not None, "Unrecognized physical GPT table row")
        if match:
            number = match[1]
            require(number not in table, "Duplicate GPT entry")
            table[number] = dict(start=int(match[2]), end=int(match[3]), code=match[4], name=match[5])
    expected_table = read_json(Path(__file__).with_name("hardware.json"))["sda_fixed_partitions"]
    expected_table.update({"14": dict(start=385772, end=end, code="FFFF", name="super"),
                           "15": dict(start=end + 1, end=124070906, code="A03A", name="userdata")})
    require(table == expected_table, "Physical GPT inventory/boundaries changed outside the reviewed layout")
    expected = {
        "14": dict(start=385772, end=end, name="super", type="89A12DE1-5E41-4CB3-8B4C-B1441EB5DA38", attributes="0000000000000000"),
        "15": dict(start=end + 1, end=124070906, name="userdata", type="1B81E7E6-F50D-419B-A739-2AEEF8DA3335", attributes="0000000000000000"),
    }
    for number, fields in expected.items():
        actual = gpt["partitions"].get(number, gpt["partitions"].get(int(number), {}))
        require(all(actual.get(k) == v for k, v in fields.items()), f"Unexpected GPT partition {number}")


def check_recovery(device, *, eu=False, both=True):
    require(device.mode() == "recovery", "Expected OrangeFox Recovery ADB")
    require(device.shell("id -u").strip() == "0", "Recovery shell is not root")
    props = device.props()
    exact_props(props, {"ro.boot.prjname": "25021", "ro.boot.vbmeta.device_state": "unlocked",
                        "ro.boot.slot_suffix": "_a"})
    require(props.get("ro.boot.flash.locked", "") in ("", "0"), "Recovery reports a locked device")
    gpt = device.capture_gpt()
    check_layout(gpt, eu)
    for name, (size, sha) in PROTECTED.items():
        require(device.hash_partition(name, size) == sha, f"GBL preservation check failed: {name}")
    for name in (("recovery_a", "recovery_b") if both else ("recovery_a",)):
        require(device.partition_size(name) == 104857600, f"Recovery capacity changed: {name}")
        require(device.hash_partition(name) == RECOVERY_SHA, f"OrangeFox hash mismatch: {name}")
    battery = device.shell("cat /sys/class/power_supply/battery/capacity").strip()
    require(battery.isdigit() and 50 <= int(battery) <= 100, "Battery must be at least 50%")
    return gpt


def check_cached_layout(device, eu=False):
    expected = EU_SUPER if eu else CN_SUPER
    require(device.partition_size("super") == expected, "Kernel super size differs from the reviewed GPT; fresh Recovery required")
    start = 5378796 if eu else 5188332
    require(device.partition_size("userdata") == (124070906 - start + 1) * 4096,
            "Kernel userdata size differs from GPT")


def xbl_metadata(data):
    """Read bounded Qualcomm OEM metadata in this pinned ELF64 xbl_config image.

    This is image metadata only; it does not read hardware rollback fuses.
    Layout reference: koaaN/arbextract (credited in THIRD_PARTY_NOTICES).
    """
    require(len(data) >= 64 and data[:6] == b"\x7fELF\x02\x01", "Expected little-endian ELF64 xbl_config")
    table = struct.unpack_from("<Q", data, 32)[0]
    stride, count = struct.unpack_from("<HH", data, 54)
    require(stride >= 56 and 0 < count <= 64 and table + count * stride <= len(data), "Invalid ELF program headers")
    found = set()
    for index in range(count):
        kind, _, offset, _, _, size, _, _ = struct.unpack_from("<II6Q", data, table + index * stride)
        if kind != 0 or size < 48:
            continue
        require(offset + size <= len(data), "Truncated ELF metadata segment")
        for relative in range(0, min(4096, size - 47), 4):
            at = offset + relative
            version, common, qti, oem, hashes = struct.unpack_from("<5I", data, at)
            if not (1 <= version <= 10 and common <= 4096 and 12 <= oem <= 16384 and hashes <= 16384):
                continue
            md = at + 36 + common + qti
            if md + oem > offset + size:
                continue
            major, minor, arb = struct.unpack_from("<3I", data, md)
            if 1 <= major <= 10 and minor <= 100 and arb <= 100:
                found.add((major, minor, arb))
    require(found == {(3, 0, 0)}, f"xbl_config OEM metadata is outside the reviewed (3, 0, 0): {found}")
    return (3, 0, 0)


def check_install_log(before, after):
    require(after.startswith(before), "Recovery log rotated or restarted during sideload; manual review required")
    tail = after[len(before):]
    require("Installation complete" in tail, "Fresh installer completion marker missing")
    require("Keeping the current ABL" in tail and "ABL will be flashed" not in tail,
            "Installer did not confirm ABL=NO")
    require(not re.search(r"(?:ERROR:|Error installing zip|Failed streaming super|Sparse super writer failed)", tail),
            "Installer reported an error")
    return tail


def check_format_log(before, after):
    require(after.startswith(before), "Recovery log changed before Format Data verification")
    tail = after[len(before):]
    # The known UI flow formats userdata and metadata. Match each formatter's
    # own success before the next formatter, never an unrelated stale success.
    for name in ("sda15", "sda10"):
        pattern = rf"I:mkfs_f2fs command: [^\n]*/dev/block/{name}\b[^\n]*\n(?:(?!I:mkfs_f2fs command:).)*?Info: format successful"
        require(re.search(pattern, tail, re.S) is not None, f"Fresh successful Format Data evidence missing for {name}")
    return tail
