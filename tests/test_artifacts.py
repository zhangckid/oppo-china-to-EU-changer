import hashlib
import io
import struct
import unittest
import zlib

import changer.artifacts as artifacts
from changer.artifacts import _archive_manifest, _firmware_sizes, verify_artifacts, verify_sparse
from changer.core import ReviewRequired


def sparse(chunks, *, block_size=4, checksum=None, declared_blocks=None):
    expanded = b"".join(
        data if data is not None else bytes(block_size * blocks)
        for kind, data, blocks in chunks if kind in (0xCAC1, 0xCAC2, 0xCAC3)
    )
    if declared_blocks is None:
        declared_blocks = sum(blocks for _, _, blocks in chunks)
    header = struct.pack("<I4H4I", 0xED26FF3A, 1, 0, 28, 12, block_size,
                         declared_blocks, len(chunks),
                         zlib.crc32(expanded) & 0xffffffff if checksum is None else checksum)
    output = bytearray(header)
    for kind, payload, blocks in chunks:
        if kind == 0xCAC1:
            body = payload
        elif kind == 0xCAC2:
            body = payload
        elif kind == 0xCAC3:
            body = b""
        else:
            body = payload
        output.extend(struct.pack("<2H2I", kind, 0, blocks, 12 + len(body)))
        output.extend(body)
    return bytes(output)


class VerifySparseTests(unittest.TestCase):
    def test_raw_fill_hole_and_crc_chunks(self):
        # One RAW block, one FILL block, and a skipped block treated as zeros.
        contents = b"ABCD" + b"wxyz" + bytes(4)
        stream_data = sparse([
            (0xCAC1, b"ABCD", 1),
            (0xCAC2, b"wxyz", 1),
            (0xCAC3, None, 1),
        ])
        result = verify_sparse(io.BytesIO(stream_data), expected_size=12)
        self.assertEqual(result["expanded_size"], 12)
        self.assertEqual(result["sha256"], hashlib.sha256(contents).hexdigest())
        self.assertEqual(result["extents"][1]["sha256"], hashlib.sha256(b"wxyz").hexdigest())
        self.assertIsNone(result["extents"][2]["sha256"])
        self.assertEqual(result["dont_care_policy"],
                         "unspecified sparse bytes; excluded from device verification; logical SHA zero-fills these ranges")

    def test_crc_chunk_checks_prior_expanded_data(self):
        data = b"ABCD"
        crc = zlib.crc32(data) & 0xffffffff
        sparse_bytes = sparse([(0xCAC1, data, 1),
                               (0xCAC4, struct.pack("<I", crc), 0)])
        result = verify_sparse(io.BytesIO(sparse_bytes), expected_size=4)
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
        corrupted = bytearray(sparse_bytes)
        corrupted[-4:] = struct.pack("<I", crc ^ 1)
        with self.assertRaises(ReviewRequired):
            verify_sparse(io.BytesIO(corrupted), expected_size=4)

    def test_rejects_wrong_expanded_size_and_trailing_data(self):
        one_block = sparse([(0xCAC1, b"ABCD", 1)])
        with self.assertRaises(ReviewRequired):
            verify_sparse(io.BytesIO(one_block), expected_size=8)
        with self.assertRaises(ReviewRequired):
            verify_sparse(io.BytesIO(one_block + b"x"), expected_size=4)

    def test_rejects_truncated_payload_and_bad_header_checksum(self):
        raw = sparse([(0xCAC1, b"ABCD", 1)])
        with self.assertRaises(ReviewRequired):
            verify_sparse(io.BytesIO(raw[:-1]), expected_size=4)
        bad_checksum = sparse([(0xCAC1, b"ABCD", 1)], checksum=5)
        with self.assertRaises(ReviewRequired):
            verify_sparse(io.BytesIO(bad_checksum), expected_size=4)

    def test_rejects_malformed_headers_chunks_and_oversize_extents(self):
        valid = sparse([(0xCAC1, b"ABCD", 1)])
        bad_magic = bytearray(valid)
        bad_magic[0] = 0
        bad_version = bytearray(valid)
        bad_version[4] = 2
        bad_file_header = bytearray(valid)
        bad_file_header[8:10] = struct.pack("<H", 27)
        bad_chunk_header = bytearray(valid)
        bad_chunk_header[10:12] = struct.pack("<H", 11)
        bad_block_size = bytearray(valid)
        bad_block_size[12:16] = struct.pack("<I", 0)
        bad_reserved = bytearray(valid)
        bad_reserved[30:32] = struct.pack("<H", 1)
        unknown_chunk = sparse([(0xCAFF, b"ABCD", 1)])
        oversized = sparse([(0xCAC1, b"ABCDEFGH", 2)], declared_blocks=1)
        for malformed in (bad_magic, bad_version, bad_file_header, bad_chunk_header,
                          bad_block_size, bad_reserved, unknown_chunk, oversized):
            with self.subTest(malformed=bytes(malformed[:12])):
                with self.assertRaises(ReviewRequired):
                    verify_sparse(io.BytesIO(malformed), expected_size=4)

    def test_rejects_excessive_sparse_chunk_count(self):
        header = struct.pack("<I4H4I", 0xED26FF3A, 1, 0, 28, 12, 4, 1,
                             65537, 0)
        with self.assertRaises(ReviewRequired):
            verify_sparse(io.BytesIO(header), expected_size=4)


class _ZipInfo:
    def __init__(self, filename, file_size=0):
        self.filename = filename
        self.file_size = file_size

    def is_dir(self):
        return self.filename.endswith("/")


class _ZipListing:
    def __init__(self, infos):
        self._infos = infos
        self._by_name = {info.filename: info for info in infos}

    def infolist(self):
        return self._infos

    def getinfo(self, name):
        return self._by_name[name]


class ArchiveManifestTests(unittest.TestCase):
    def test_reviewed_input_sha256_pins_are_64_lowercase_hex(self):
        for name in ("rom", "gbl_apk", "recovery_img", "recovery_zip"):
            digest = artifacts._PINS[name]["sha256"]
            with self.subTest(name=name):
                self.assertRegex(digest, r"\A[0-9a-f]{64}\Z")

    def _listing(self):
        sizes = _firmware_sizes()
        infos = [_ZipInfo(name, size) for name, size in sizes.items()]
        infos.extend(_ZipInfo(name) for name in artifacts._PINS["rom_directories"])
        infos.extend(_ZipInfo(name, size) for name, size in artifacts._PINS["rom_files"].items())
        return infos

    def test_accepts_exact_reviewed_firmware_set(self):
        manifest = _archive_manifest(_ZipListing(self._listing()))
        self.assertEqual(set(manifest), set(_firmware_sizes()))
        self.assertEqual(len(_firmware_sizes()), 53)

    def test_rejects_extra_firmware_and_duplicate_members(self):
        infos = self._listing()
        with self.assertRaises(ReviewRequired):
            _archive_manifest(_ZipListing(infos + [_ZipInfo("OTA_FILES_HERE/extra.img", 4)]))
        with self.assertRaises(ReviewRequired):
            _archive_manifest(_ZipListing(infos + [infos[0]]))

    def test_rejects_missing_metadata_wrong_size_and_unsafe_paths(self):
        infos = self._listing()
        with self.assertRaises(ReviewRequired):
            _archive_manifest(_ZipListing([i for i in infos
                if i.filename != "META-INF/com/google/android/updater-script"]))
        first = infos[0]
        with self.assertRaises(ReviewRequired):
            _archive_manifest(_ZipListing([_ZipInfo(first.filename, first.file_size + 1)] + infos[1:]))
        with self.assertRaises(ReviewRequired):
            _archive_manifest(_ZipListing(infos + [_ZipInfo("OTA_FILES_HERE/../escape")]))

    def test_bad_zip_is_reported_as_review_required(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        with TemporaryDirectory() as directory:
            bad_zip = Path(directory) / "not-a-zip"
            bad_zip.write_bytes(b"not a zip")
            with patch.object(artifacts, "_validated_file", return_value={"path": "x", "size": 1,
                                                                            "sha256": "0" * 64}):
                with self.assertRaisesRegex(ReviewRequired, "Cannot validate ROM archive"):
                    verify_artifacts(bad_zip, "apk", "recovery", "recovery.zip")

    def test_file_pin_accepts_arbitrary_filename_but_rejects_size_or_hash_mismatch(self):
        import hashlib
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        payload = b"reviewed content"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "renamed-input.bin"
            path.write_bytes(payload)
            pin = {"rom": {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}}
            with patch.object(artifacts, "_PINS", pin):
                self.assertEqual(artifacts._validated_file("rom", path)["sha256"], pin["rom"]["sha256"])
                pin["rom"]["size"] += 1
                with self.assertRaises(ReviewRequired):
                    artifacts._validated_file("rom", path)


if __name__ == "__main__":
    unittest.main()
