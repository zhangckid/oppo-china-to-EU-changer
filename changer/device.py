"""Bounded, serial-scoped ADB/Fastboot access for the conversion runner.

This module deliberately has no automatic reboot, retry, flash, erase, or
format behavior.  All shell commands are assembled from fixed commands and
validated names by the caller.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import selectors
import subprocess
import time
from typing import Any

from .core import ReviewRequired, require, sha256_file


_SERIAL_RE = re.compile(r"[A-Za-z0-9_-]{4,64}\Z")
_NAME_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_OUTPUT_LIMIT = 64 * 1024
_MAX_TIMEOUT = 6 * 60 * 60
_PROTECTED_BACKUP = {"userdata"}
_MAX_PARTITION_BACKUP = 512 * 1024 * 1024
_MAX_SUPER_BACKUP = 32 * 1024 * 1024 * 1024
_POLICY_PROPERTIES = (
    "ro.boot.prjname", "ro.product.model", "ro.product.name", "ro.build.display.id",
    "sys.boot_completed", "ro.boot.slot_suffix", "ro.boot.vbmeta.device_state",
    "ro.boot.flash.locked", "ro.oplus.image.my_region.type",
)


class _BoundedProcessError(ReviewRequired):
    def __init__(self, message: str, stdout: str, stderr: str):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


def _bounded_process_output(proc: subprocess.Popen[bytes], timeout: float,
                           *, progress=None, stall_timeout: float | None = None
                           ) -> tuple[int, str, str]:
    """Drain both output streams without retaining more than the log limit."""
    require(proc.stdout is not None and proc.stderr is not None, "Subprocess pipes are unavailable")
    buffers = {proc.stdout: bytearray(), proc.stderr: bytearray()}
    overflow = False
    selector = selectors.DefaultSelector()
    started = time.monotonic()
    last_progress = started
    progress_value = None
    try:
        progress_value = progress() if progress else None
        selector.register(proc.stdout, selectors.EVENT_READ)
        selector.register(proc.stderr, selectors.EVENT_READ)
        while selector.get_map() or proc.poll() is None:
            now = time.monotonic()
            total_left = timeout - (now - started)
            value = progress() if progress else None
            if value is not None and value > progress_value:
                progress_value, last_progress = value, now
            stall_left = stall_timeout - (now - last_progress) if stall_timeout is not None else total_left
            if total_left <= 0 or stall_left <= 0:
                raise ReviewRequired("Subprocess timed out or stopped making progress")
            for key, _ in selector.select(min(0.5, total_left, stall_left)):
                stream = key.fileobj
                chunk = os.read(stream.fileno(), 8192)
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                buffer = buffers[stream]
                buffer.extend(chunk)
                if len(buffer) > _OUTPUT_LIMIT:
                    overflow = True
                    del buffer[:-_OUTPUT_LIMIT]
        try:
            code = proc.wait(timeout=max(0.001, timeout - (time.monotonic() - started)))
        except subprocess.TimeoutExpired as exc:
            raise ReviewRequired("Subprocess exceeded its total timeout") from exc
        out = buffers[proc.stdout].decode(errors="replace")
        err = buffers[proc.stderr].decode(errors="replace")
        if overflow:
            raise _BoundedProcessError("Subprocess output exceeded the 64 KiB bound", out, err)
        return code, out, err
    except BaseException as exc:
        if isinstance(exc, ReviewRequired) and not hasattr(exc, "stdout"):
            exc.stdout = buffers[proc.stdout].decode(errors="replace")
            exc.stderr = buffers[proc.stderr].decode(errors="replace")
        if proc.poll() is None:
            proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        for stream in buffers:
            if not stream.closed:
                stream.close()
        raise
    finally:
        selector.close()


def parse_props(text: str) -> dict[str, str]:
    """Parse Android's getprop listing; malformed/duplicate keys are rejected."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"\[([^\]\r\n]+)\]: \[(.*)\]", line)
        require(match is not None, f"Malformed getprop line: {line[:160]!r}")
        key, value = match.groups()
        require(key not in result, f"Duplicate getprop key: {key}")
        result[key] = value
    return result


def parse_gpt(text: str) -> dict[str, Any]:
    """Parse the stable fields emitted by `sgdisk --info=N`."""
    fields = {
        "start": r"^First sector:[ \t]*(\d+)(?:[ \t]+\([^\r\n]*\))?[ \t]*$",
        "end": r"^Last sector:[ \t]*(\d+)(?:[ \t]+\([^\r\n]*\))?[ \t]*$",
        "name": r"^Partition name:\s*'([^'\r\n]*)'\s*$",
        "type": r"^Partition GUID code:[ \t]*([0-9A-Fa-f-]+)(?:[ \t]+\([^\r\n]*\))?[ \t]*$",
        "attributes": r"^Attribute flags:\s*([0-9A-Fa-f]+)\s*$",
    }
    result: dict[str, Any] = {}
    for key, pattern in fields.items():
        matches = re.findall(pattern, text, re.MULTILINE)
        require(len(matches) == 1, f"Cannot uniquely parse GPT field: {key}")
        result[key] = int(matches[0]) if key in {"start", "end"} else matches[0]
    require(result["start"] <= result["end"], "Invalid GPT sector range")
    require(re.fullmatch(r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}", result["type"]) is not None,
            "Invalid GPT partition type GUID")
    require(re.fullmatch(r"[0-9A-Fa-f]{1,16}", result["attributes"]) is not None,
            "Invalid GPT attribute flags")
    return result


def parse_fastboot_unlocked(text: str) -> bool:
    """Parse the dynamic `fastboot oem device-info` response."""
    matches = re.findall(r"(?im)^\s*(?:\(bootloader\)\s*)?Device unlocked:\s*(true|false)\s*$", text)
    require(len(matches) == 1, "Cannot uniquely parse fastboot unlocked state")
    return matches[0].lower() == "true"


def _safe_args(args: list[str], kind: str) -> list[str]:
    require(isinstance(args, list) and all(isinstance(x, str) and "\0" not in x for x in args),
            f"Invalid {kind} arguments")
    # The serial is inserted by this class.  Transport selectors would weaken
    # that guarantee or let an invocation silently choose another device.
    require(not any(x in {"-s", "-d", "-e", "--serial"} or x.startswith("--serial=") for x in args),
            f"{kind} arguments may not select a transport")
    return list(args)


class Device:
    def __init__(self, adb: Path, fastboot: Path, log: Path, serial: str):
        require(isinstance(serial, str) and _SERIAL_RE.fullmatch(serial) is not None,
                "Invalid device serial")
        self.adb_path = str(Path(adb).resolve())
        self.fastboot_path = str(Path(fastboot).resolve())
        self.log = Path(log)
        self.serial = serial

    def _record(self, command: list[str], code: int | None, out: str, err: str,
                started: float, error: str | None = None) -> None:
        self.log.parent.mkdir(parents=True, exist_ok=True)
        row = {"command": command, "exit": code, "duration_seconds": round(time.monotonic() - started, 3),
               "stdout": out[-_OUTPUT_LIMIT:], "stderr": err[-_OUTPUT_LIMIT:]}
        if error:
            row["error"] = error[:1000]
        with self.log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _run(self, command: list[str], timeout: int) -> tuple[int, str, str]:
        require(isinstance(timeout, (int, float)) and 0 < timeout <= _MAX_TIMEOUT,
                "Command timeout outside allowed bounds")
        started = time.monotonic()
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        except OSError as exc:
            self._record(command, None, "", "", started, str(exc))
            raise ReviewRequired(f"Could not run {Path(command[0]).name}: {exc}") from exc
        try:
            code, out, err = _bounded_process_output(proc, timeout)
        except BaseException as exc:
            self._record(command, None, getattr(exc, "stdout", ""), getattr(exc, "stderr", ""), started, str(exc))
            if isinstance(exc, ReviewRequired):
                raise ReviewRequired(f"Command failed or timed out: {Path(command[0]).name}: {exc}") from exc
            raise
        self._record(command, code, out, err, started)
        return code, out, err

    @staticmethod
    def _single_device_rows(text: str, protocol: str) -> list[list[str]]:
        rows = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("List of devices") or stripped.startswith("* daemon"):
                continue
            parts = stripped.split()
            if protocol == "adb" and len(parts) >= 2:
                rows.append(parts[:2])
            elif protocol == "fastboot" and len(parts) >= 1:
                rows.append(parts[:2])
            else:
                raise ReviewRequired(f"Malformed {protocol} transport listing")
        return rows

    def _transport(self, protocol: str) -> str:
        executable = self.adb_path if protocol == "adb" else self.fastboot_path
        argv = [executable, "devices"]
        if protocol == "adb":
            argv.append("-l")
        code, out, err = self._run(argv, 15)
        require(code == 0, f"{protocol} devices failed: {err.strip()[:300]}")
        rows = self._single_device_rows(out, protocol)
        require(len(rows) <= 1, f"Multiple {protocol} transports connected")
        if rows:
            require(rows[0][0] == self.serial,
                    f"Unexpected {protocol} transport connected; disconnect other devices")
            if protocol == "adb":
                state = rows[0][1]
                require(state != "unauthorized", "ADB authorization required on phone")
                require(state in {"device", "recovery", "sideload"}, f"Unknown ADB state: {state}")
            else:
                require(len(rows[0]) == 2 and rows[0][1] == "fastboot", "Unknown Fastboot transport state")
            return rows[0][1] if protocol == "adb" else "fastboot"
        return "disconnected"

    def adb(self, args: list[str], timeout: int = 60) -> str:
        safe = _safe_args(args, "ADB")
        state = self._exclusive_transport("adb")
        require(state != "disconnected", "No authorized ADB transport")
        require(state != "sideload" or (safe and safe[0] == "shell"), "ADB sideload transport is restricted")
        code, out, err = self._run([self.adb_path, "-s", self.serial, *safe], timeout)
        require(code == 0, f"ADB command failed ({safe[:3]}): {(err + out).strip()[-600:]}")
        return out.strip()

    def shell(self, command: str, timeout: int = 60) -> str:
        require(isinstance(command, str) and command and len(command) <= 4096
                and not any(char in command for char in "\0\r\n"),
                "Invalid ADB shell command")
        return self.adb(["shell", command], timeout)

    def fastboot(self, args: list[str], timeout: int = 60) -> str:
        safe = _safe_args(args, "Fastboot")
        state = self._exclusive_transport("fastboot")
        require(state != "disconnected", "No authorized Fastboot transport")
        code, out, err = self._run([self.fastboot_path, "-s", self.serial, *safe], timeout)
        require(code == 0, f"Fastboot command failed ({safe[:3]}): {(err + out).strip()[-600:]}")
        result = (out + err).strip()
        require(re.search(r"(?im)^\s*(?:\(bootloader\)\s*)?(?:FAILED\b|fastboot:\s*error:|error:\s*)", result) is None,
                f"Fastboot reported failure despite exit code 0 ({safe[:3]}): {result[-600:]}")
        return result

    def _exclusive_transport(self, protocol: str) -> str:
        state = self._transport(protocol)
        other_protocol = "fastboot" if protocol == "adb" else "adb"
        other_state = self._transport(other_protocol)
        require(not (state != "disconnected" and other_state != "disconnected"),
                "Multiple USB transports detected")
        return state

    def mode(self) -> str:
        adb_state = self._transport("adb")
        fastboot_state = self._transport("fastboot")
        require(not (adb_state != "disconnected" and fastboot_state != "disconnected"),
                "Multiple USB transports detected")
        if fastboot_state == "fastboot":
            return "fastboot"
        if adb_state == "disconnected":
            return "disconnected"
        if adb_state == "sideload":
            return "sideload"
        bootmode = self.shell("getprop ro.bootmode").strip().lower()
        require(bootmode in {"", "normal", "recovery"}, f"Unknown Android boot mode: {bootmode!r}")
        require(not (adb_state == "recovery" and bootmode == "normal"),
                "Conflicting ADB and ro.bootmode recovery state")
        return "recovery" if bootmode == "recovery" or adb_state == "recovery" else "android"

    def props(self) -> dict[str, str]:
        keys = " ".join(_POLICY_PROPERTIES)
        command = (f"for key in {keys}; do value=$(getprop \"$key\") || exit $?; "
                   "printf '[%s]: [%s]\\n' \"$key\" \"$value\"; done")
        return parse_props(self.shell(command))

    def boot_id(self) -> str:
        value = self.shell("cat /proc/sys/kernel/random/boot_id").strip()
        require(re.fullmatch(r"[0-9a-fA-F-]{16,64}", value) is not None, "Invalid kernel boot ID")
        return value

    def unlocked(self) -> bool:
        return parse_fastboot_unlocked(self.fastboot(["oem", "device-info"], timeout=30))

    def sideload(self, path: Path, timeout: int = 5400) -> str:
        source = Path(path)
        require(source.is_file() and source.stat().st_size > 0, "Sideload package missing or empty")
        # Keep Runner's /proc-backed lease intact. Resolving symlinks here would
        # reopen the replaceable external pathname after verification.
        source = source.absolute()
        require(self._exclusive_transport("adb") == "sideload", "Device is not in ADB sideload mode")
        code, out, err = self._run([self.adb_path, "-s", self.serial, "sideload", str(source)], timeout)
        require(code == 0, f"ADB sideload host process failed: {(err + out).strip()[-600:]}")
        # The caller must inspect recovery/install state; a host-side exit code
        # alone is not evidence that the package was accepted.
        return (out + err).strip()

    def pull(self, remote: str, local: Path) -> dict[str, Any]:
        require(isinstance(remote, str) and remote.startswith("/") and "\0" not in remote
                and len(remote) <= 1024, "Invalid remote pull path")
        target = Path(local)
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists() and not target.is_symlink(), f"Pull destination already exists: {target}")
        staging = target.with_name(f".{target.name}.{secrets.token_hex(12)}.pulltmp")
        require(not staging.exists() and not staging.is_symlink(), "Pull staging path collision")
        argv = [self.adb_path, "-s", self.serial, "pull", remote, str(staging)]
        require(self._exclusive_transport("adb") in {"device", "recovery"}, "ADB pull requires Android or recovery")
        started = time.monotonic()
        try:
            proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            def current_size() -> int:
                try:
                    size = staging.stat().st_size
                    require(size <= 64 * 1024 * 1024, "Pulled evidence exceeds the 64 MiB limit")
                    return size
                except FileNotFoundError:
                    return 0
            code, out, err = _bounded_process_output(proc, 5400, progress=current_size, stall_timeout=120)
        except BaseException as exc:
            self._record(argv, None, getattr(exc, "stdout", ""), getattr(exc, "stderr", ""), started, str(exc))
            staging.unlink(missing_ok=True)
            if isinstance(exc, ReviewRequired):
                raise ReviewRequired(f"ADB pull failed or timed out: {exc}") from exc
            raise
        if code != 0 or not staging.is_file():
            failure = f"ADB pull failed: {(err + out).strip()[-500:]}"
            self._record(argv, code, out, err, started, failure)
            staging.unlink(missing_ok=True)
            raise ReviewRequired(failure)
        self._record(argv, code, out, err, started)
        size = staging.stat().st_size
        if size > 64 * 1024 * 1024:
            staging.unlink(missing_ok=True)
            raise ReviewRequired("Pulled evidence exceeds the 64 MiB limit")
        digest = sha256_file(staging)
        try:
            os.link(staging, target)
        except OSError as exc:
            staging.unlink(missing_ok=True)
            raise ReviewRequired(f"Could not safely publish pulled file at {target}: {exc}") from exc
        staging.unlink(missing_ok=True)
        return {"path": str(target), "bytes": size, "sha256": digest}

    def partition_size(self, name: str) -> int:
        require(_NAME_RE.fullmatch(name) is not None, "Invalid partition name")
        raw = self.shell(f"blockdev --getsize64 /dev/block/by-name/{name}").strip()
        require(raw.isdigit() and int(raw) > 0, f"Invalid partition size: {name}")
        return int(raw)

    def hash_partition(self, name: str, length: int | None = None, offset: int = 0) -> str:
        require(_NAME_RE.fullmatch(name) is not None, "Invalid partition name")
        size = self.partition_size(name)
        length = size - offset if length is None else length
        require(isinstance(offset, int) and isinstance(length, int) and offset >= 0 and length > 0
                and offset + length <= size, "Partition hash range is invalid")
        device = f"/dev/block/by-name/{name}"
        if offset == 0 and length == size:
            command = f"sha256sum {device}"
            output_name = device
        elif offset == 0 and length % 4096:
            command = f"set -o pipefail || exit $?; head -c {length} {device} | sha256sum"
            output_name = "-"
        else:
            require(offset % 4096 == 0 and length % 4096 == 0,
                    "dd partition hash extents must be 4096-byte aligned")
            command = (f"set -o pipefail || exit $?; dd if={device} bs=4096 "
                       f"skip={offset // 4096} count={length // 4096} 2>/dev/null | sha256sum")
            output_name = "-"
        output = self.shell(command, timeout=5400)
        match = re.fullmatch(r"([0-9a-f]{64})\s+" + re.escape(output_name), output.strip())
        require(match is not None, f"Invalid partition hash result: {name}")
        return match[1]

    def _stream_partition(self, name: str, target: Path, size: int,
                          timeout: int = 5400, stall_timeout: int = 120) -> str:
        require(_NAME_RE.fullmatch(name) is not None and isinstance(size, int) and size > 0,
                "Invalid partition stream request")
        require(0 < timeout <= _MAX_TIMEOUT and 0 < stall_timeout <= _MAX_TIMEOUT,
                "Partition stream timeout outside allowed bounds")
        remote = f"/dev/block/by-name/{name}"
        argv = [self.adb_path, "-s", self.serial, "exec-out", "dd", f"if={remote}", "bs=1048576"]
        started = time.monotonic()
        hasher = hashlib.sha256()
        count = 0
        proc = None
        error_buffer = bytearray()
        error_overflow = False
        created = False
        try:
            with target.open("xb") as output:
                created = True
                proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
                require(proc.stdout is not None and proc.stderr is not None, "Partition stream pipes are unavailable")
                last_progress = time.monotonic()
                with selectors.DefaultSelector() as selector:
                    selector.register(proc.stdout, selectors.EVENT_READ)
                    selector.register(proc.stderr, selectors.EVENT_READ)
                    while selector.get_map() or proc.poll() is None:
                        now = time.monotonic()
                        total_left = timeout - (now - started)
                        stall_left = stall_timeout - (now - last_progress)
                        remaining = min(total_left, stall_left)
                        if remaining <= 0:
                            raise ReviewRequired(f"Partition stream timed out: {name}")
                        if not selector.get_map():
                            time.sleep(min(0.2, remaining))
                            continue
                        for key, _ in selector.select(min(0.5, remaining)):
                            stream = key.fileobj
                            if stream is proc.stdout:
                                limit = min(1024 * 1024, size - count) if count < size else 1
                            else:
                                limit = 8192
                            chunk = os.read(stream.fileno(), limit)
                            if not chunk:
                                selector.unregister(stream)
                                stream.close()
                                if stream is proc.stdout and count != size:
                                    raise ReviewRequired(f"Short read while backing up {name}: {count} of {size} bytes")
                                continue
                            if stream is proc.stderr:
                                error_buffer.extend(chunk)
                                if len(error_buffer) > _OUTPUT_LIMIT:
                                    error_overflow = True
                                    del error_buffer[:-_OUTPUT_LIMIT]
                                continue
                            if count >= size:
                                raise ReviewRequired(f"Overlong read while backing up {name}")
                            output.write(chunk)
                            hasher.update(chunk)
                            count += len(chunk)
                            last_progress = time.monotonic()
                remaining = min(timeout - (time.monotonic() - started),
                                stall_timeout - (time.monotonic() - last_progress))
                require(remaining > 0, f"Partition stream timed out: {name}")
                output.flush()
                os.fsync(output.fileno())
                try:
                    code = proc.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    raise ReviewRequired(f"ADB stream did not terminate: {name}")
                err = error_buffer.decode(errors="replace")
                require(not error_overflow, f"Partition stream stderr exceeded the bounded output limit: {name}")
                require(code == 0, f"ADB stream failed for {name}: {err[-500:]}")
        except BaseException as exc:
            if proc is not None and proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            if proc is not None:
                for stream in (proc.stdout, proc.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()
            self._record(argv, None, f"streamed {count} of {size} bytes",
                         error_buffer.decode(errors="replace"), started, str(exc))
            if created:
                target.unlink(missing_ok=True)
            raise
        self._record(argv, 0, f"streamed {count} bytes sha256={hasher.hexdigest()}", "", started)
        return hasher.hexdigest()

    def backup_partition(self, name: str, dest: Path) -> dict[str, Any]:
        require(_NAME_RE.fullmatch(name) is not None and name not in _PROTECTED_BACKUP,
                "Protected or invalid partition backup request")
        size = self.partition_size(name)
        if name == "super":
            size_limit = _MAX_SUPER_BACKUP
        elif name == "metadata":
            size_limit = 128 * 1024 * 1024
        else:
            size_limit = _MAX_PARTITION_BACKUP
        require(size <= size_limit,
                f"Partition too large for bounded backup: {name} ({size} bytes)")
        target = Path(dest)
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists() and not target.is_symlink(), f"Backup destination already exists: {target}")
        require(self._exclusive_transport("adb") in {"device", "recovery"},
                "Partition backup requires Android or recovery")
        host_hash = self._stream_partition(name, target, size)
        require(target.stat().st_size == size and sha256_file(target) == host_hash,
                f"Host backup stream verification failed: {name}")
        device_hash = self.hash_partition(name, size)
        require(device_hash == host_hash, f"Partition backup hash mismatch: {name}")
        return {"partition": name, "path": str(target), "bytes": size,
                "sha256": host_hash, "device_sha256": device_hash}

    def capture_gpt(self) -> dict[str, Any]:
        device = "/dev/block/sda"
        sector_raw = self.shell(f"blockdev --getss {device}").strip()
        size_raw = self.shell(f"blockdev --getsize64 {device}").strip()
        require(sector_raw.isdigit() and int(sector_raw) > 0 and size_raw.isdigit() and int(size_raw) > 0,
                "Invalid physical disk geometry")
        paths = {}
        for label in ("super", "userdata"):
            paths[label] = self.shell(f"readlink -f /dev/block/by-name/{label}").strip()
        require(paths == {"super": "/dev/block/sda14", "userdata": "/dev/block/sda15"},
                f"Unexpected GPT partition devices: {paths}")
        partitions = {}
        for number in (14, 15):
            partitions[number] = parse_gpt(self.shell(f"sgdisk --info={number} {device}"))
        verify = self.shell(f"sgdisk --verify {device}")
        require("No problems found" in verify, "GPT verification failed")
        table = self.shell(f"sgdisk --print {device}")
        return {"device": device, "sector_bytes": int(sector_raw), "device_bytes": int(size_raw),
                "super_device": paths["super"], "userdata_device": paths["userdata"],
                "resolved": paths, "partitions": partitions, "verify": verify, "table": table}
