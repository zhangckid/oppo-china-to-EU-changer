# Source release procedure

English | [简体中文](RELEASING.zh-CN.md) | [Project home](../README.md)

Public source archives must be built from the reviewed allowlist in [`release-files.txt`](../release-files.txt). The exporter rejects missing files, paths outside the repository, and symbolic links. It copies only listed files, creates a SHA-256 manifest, and writes a `.tar.gz`; it does not upload or publish anything. The output path must be outside this repository, so generated archives cannot enter a later source export by accident.

From the repository root:

```sh
python3 scripts/export_source.py --out ../releases/oppo-china-to-eu-changer
```

Review both the exported directory and archive before attaching them to a release. The allowlist must contain source and public documentation only. Keep ROMs, GBL APKs, OrangeFox images/ZIPs, Platform Tools, device backups, private configuration, serial-bearing logs, and local test outputs out of the archive. Do not add the full operator record from the neighboring private work directory.

The generated `SOURCE-MANIFEST.sha256` records the files copied from the allowlist. It does not authenticate the origin or safety of third-party device images.

Before a release, run the checks in CI, review the validation record and supported-device statement, inspect the allowlist for newly added files, and verify the archive contains no unlisted files or private data. Release tags and uploads are separate maintainer actions.

Documentation images must also be individually allowlisted. Review real-device captures for privacy, provenance and third-party marks; do not add a private photo or log directory wholesale. `docs/images/guide-*.html` are the source for typeset offline terminal output, and their PNGs must not be described as hardware-flash validation. New documents should have English and Chinese counterparts with working language links.
