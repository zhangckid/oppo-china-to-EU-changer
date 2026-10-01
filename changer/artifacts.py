"""Offline, pinned-input and firmware package validation."""
from __future__ import annotations

import hashlib
import json
import os
import struct
import zipfile
import zlib
from pathlib import Path
from typing import BinaryIO

from .core import ReviewRequired, require, sha256_file


_ROOT = Path(__file__).resolve().parent
_PINS = json.loads((_ROOT / "pins.json").read_text(encoding="utf-8"))
# Android sparse image format constants.
_SPARSE_MAGIC = 0xED26FF3A
_RAW, _FILL, _DONT_CARE, _CRC32 = 0xCAC1, 0xCAC2, 0xCAC3, 0xCAC4
_MAX_HEADER = 4096
_HASH_BLOCK = 1024 * 1024
_MAX_SPARSE_CHUNKS = 65536
_EXPECTED_SUPER_EXPANDED = 20451426304


def _pin(name: str) -> dict:
    return _PINS[name]


def _hash_zeros(length: int) -> str:
    h = hashlib.sha256()
    zeroes = bytes(min(_HASH_BLOCK, length))
    while length:
        n = min(length, len(zeroes))
        h.update(zeroes[:n])
        length -= n
    return h.hexdigest()


def _hash_repeated(pattern: bytes, length: int) -> str:
    require(bool(pattern), "sparse FILL pattern is empty")
    h = hashlib.sha256()
    block_len = max(len(pattern), (_HASH_BLOCK // len(pattern)) * len(pattern))
    block = pattern * (block_len // len(pattern))
    while length:
        n = min(length, len(block))
        h.update(block[:n])
        length -= n
    return h.hexdigest()


def _crc_repeat(crc: int, data: bytes, length: int) -> int:
    """Update CRC over repeated data without allocating an expanded chunk."""
    if not data:
        return crc
    reps = max(1, _HASH_BLOCK // len(data))
    block = data * reps
    while length:
        n = min(length, len(block))
        crc = zlib.crc32(block[:n], crc)
        length -= n
    return crc


def _read_exact(stream: BinaryIO, length: int, what: str) -> bytes:
    require(0 <= length <= _MAX_HEADER, f"invalid {what} length")
    data = stream.read(length)
    require(len(data) == length, f"truncated sparse {what}")
    return data


def verify_sparse(stream: BinaryIO, expected_size: int = _EXPECTED_SUPER_EXPANDED) -> dict:
    """Validate Android sparse structure and hash logical written extents.

    DONT_CARE extents have unspecified target contents and no readback digest.
    The logical sparse-image digest zero-fills them for deterministic image
    hashing, matching Android sparse expansion and checksum semantics.
    """
    header = _read_exact(stream, 28, "file header")
    (magic, major, minor, file_hdr_sz, chunk_hdr_sz, block_sz, total_blks,
     total_chunks, image_checksum) = struct.unpack("<I4H4I", header)
    require(magic == _SPARSE_MAGIC, "super.img is not Android sparse format")
    require(major == 1 and minor == 0, "unsupported Android sparse version")
    require(28 <= file_hdr_sz <= _MAX_HEADER, "invalid sparse file header size")
    require(12 <= chunk_hdr_sz <= _MAX_HEADER, "invalid sparse chunk header size")
    require(block_sz > 0 and block_sz % 4 == 0, "invalid sparse block size")
    require(total_chunks <= _MAX_SPARSE_CHUNKS, "sparse image has too many chunks")
    if file_hdr_sz > 28:
        _read_exact(stream, file_hdr_sz - 28, "file header extension")
    expanded_size = total_blks * block_sz
    require(expanded_size == expected_size,
            f"sparse super expanded size is {expanded_size}, expected {expected_size}")

    extents: list[dict] = []
    expanded_offset = 0
    crc = 0
    full_hash = hashlib.sha256()
    for index in range(total_chunks):
        raw_header = _read_exact(stream, chunk_hdr_sz, "chunk header")
        kind, reserved, chunk_blocks, total_sz = struct.unpack("<2H2I", raw_header[:12])
        require(reserved == 0, f"sparse chunk {index} has nonzero reserved field")
        payload_size = total_sz - chunk_hdr_sz
        require(payload_size >= 0, f"sparse chunk {index} has invalid total size")
        extent_size = chunk_blocks * block_sz
        require(extent_size > 0 or kind == _CRC32,
                f"sparse chunk {index} has empty data extent")
        if kind == _RAW:
            require(payload_size == extent_size, f"sparse RAW chunk {index} size mismatch")
            digest = hashlib.sha256()
            remaining = extent_size
            while remaining:
                data = stream.read(min(_HASH_BLOCK, remaining))
                require(bool(data), f"truncated sparse RAW chunk {index}")
                remaining -= len(data)
                digest.update(data)
                full_hash.update(data)
                crc = zlib.crc32(data, crc)
            extent_hash = digest.hexdigest()
        elif kind == _FILL:
            require(payload_size == 4, f"sparse FILL chunk {index} size mismatch")
            pattern = _read_exact(stream, 4, f"FILL payload {index}")
            extent_hash = _hash_repeated(pattern, extent_size)
            crc = _crc_repeat(crc, pattern, extent_size)
            _feed_repeated_hash(full_hash, pattern, extent_size)
        elif kind == _DONT_CARE:
            require(payload_size == 0, f"sparse DONT_CARE chunk {index} has payload")
            extent_hash = None
            crc = _crc_repeat(crc, b"\0", extent_size)
            _feed_zeros(full_hash, extent_size)
        elif kind == _CRC32:
            require(chunk_blocks == 0 and payload_size == 4,
                    f"sparse CRC32 chunk {index} has invalid shape")
            want_crc = struct.unpack("<I", _read_exact(stream, 4, "CRC32 payload"))[0]
            require(crc == want_crc, f"sparse CRC32 chunk {index} mismatch")
            continue
        else:
            raise ReviewRequired(f"sparse chunk {index} has unknown type 0x{kind:04x}")

        extents.append({"offset": expanded_offset, "length": extent_size,
                        "sha256": extent_hash})
        expanded_offset += extent_size
        require(expanded_offset <= expanded_size, "sparse chunks exceed declared image size")

    require(expanded_offset == expanded_size, "sparse chunks do not cover declared image size")
    require(stream.read(1) == b"", "trailing data after sparse image")
    if image_checksum:
        require((crc & 0xffffffff) == image_checksum, "sparse image checksum mismatch")
    return {"expanded_size": expanded_size, "sha256": full_hash.hexdigest(),
            "sha256_semantics": "logical expanded bytes; DONT_CARE is zero-filled",
            "dont_care_policy": "unspecified sparse bytes; excluded from device verification; logical SHA zero-fills these ranges",
            "sparse_chunks": total_chunks, "block_size": block_sz,
            "extents": extents}


def _feed_zeros(h, length: int) -> None:
    zeros = bytes(_HASH_BLOCK)
    while length:
        n = min(length, len(zeros))
        h.update(zeros[:n])
        length -= n


def _feed_repeated_hash(h, pattern: bytes, length: int) -> None:
    reps = max(1, _HASH_BLOCK // len(pattern))
    block = pattern * reps
    while length:
        n = min(length, len(block))
        h.update(block[:n])
        length -= n


def _firmware_sizes() -> dict[str, int]:
    return {str(name): int(size) for name, size in _PINS["firmware_image_sizes"].items()}


def _archive_manifest(zf: zipfile.ZipFile) -> list[str]:
    infos = zf.infolist()
    names = [i.filename for i in infos]
    require(len(names) == len(set(names)), "ROM archive contains duplicate names")
    require(all("\\" not in n and not n.startswith("/") and ".." not in Path(n).parts
                for n in names), "ROM archive contains an unsafe path")
    expected_sizes = _firmware_sizes()
    actual_firmware = {n for n in names if n.startswith("OTA_FILES_HERE/") and n.endswith(".img")}
    require(actual_firmware == set(expected_sizes), "ROM firmware image set differs from reviewed inventory")
    extra_sizes = _PINS["rom_files"]
    expected_names = set(expected_sizes) | set(extra_sizes) | set(_PINS["rom_directories"])
    require(set(names) == expected_names, "ROM archive contains unexpected or missing files")
    for name, expected_length in expected_sizes.items():
        info = zf.getinfo(name)
        require(not info.is_dir() and info.file_size == expected_length,
                f"ROM firmware size mismatch for {name}")
    # Pin the installer and native writer tools by exact path and uncompressed size.
    for name, expected_length in extra_sizes.items():
        info = zf.getinfo(name)
        require(not info.is_dir() and info.file_size == expected_length,
                f"ROM file size mismatch for {name}")
    return sorted(expected_sizes)


def _hash_zip_member(zf: zipfile.ZipFile, name: str) -> str:
    h = hashlib.sha256()
    with zf.open(name, "r") as source:
        while data := source.read(_HASH_BLOCK):
            h.update(data)
    return h.hexdigest()


def _validated_file(name: str, supplied: os.PathLike | str) -> dict:
    path = Path(supplied).expanduser().resolve(strict=True)
    require(path.is_file(), f"{name} is not a regular file")
    pin = _pin(name)
    size = path.stat().st_size
    require(size == pin["size"], f"{name} size does not match reviewed pin")
    digest = sha256_file(path)
    require(digest == pin["sha256"], f"{name} SHA-256 does not match reviewed pin")
    return {"path": str(path), "size": size, "sha256": digest}


def verify_artifacts(rom, gbl_apk, recovery_img, recovery_zip) -> dict:
    """Validate four pinned local files and inventory every reviewed firmware image."""
    inputs = {name: _validated_file(name, path) for name, path in (
        ("rom", rom), ("gbl_apk", gbl_apk), ("recovery_img", recovery_img),
        ("recovery_zip", recovery_zip))}
    try:
        with zipfile.ZipFile(rom, "r") as zf:
            firmware_paths = _archive_manifest(zf)
            firmware = {}
            super_result = None
            for entry in firmware_paths:
                part = Path(entry).stem
                if part in {"abl", "recovery"}:
                    continue
                if part == "super":
                    with zf.open(entry, "r") as source:
                        super_result = verify_sparse(source)
                    continue
                firmware[part] = {"size": zf.getinfo(entry).file_size,
                                  "sha256": _hash_zip_member(zf, entry)}
    except (zipfile.BadZipFile, EOFError, RuntimeError, zlib.error, struct.error) as error:
        raise ReviewRequired(f"Cannot validate ROM archive: {error}") from error
    require(super_result is not None, "reviewed ROM has no super image")
    return {"schema_version": 1, "inputs": inputs,
            "archive_manifest": {"expected_files": firmware_paths,
                                 "firmware_image_count": len(firmware_paths),
                                 "archive_entry_count": len(firmware_paths) + len(_PINS["rom_files"]) + len(_PINS["rom_directories"])},
            "images": firmware, "super": super_result}
