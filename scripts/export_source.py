#!/usr/bin/env python3
"""Export only the explicitly allowlisted public source files."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import tarfile


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "release-files.txt"


def listed_files() -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for line_no, raw in enumerate(ALLOWLIST.read_text(encoding="utf-8").splitlines(), 1):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        rel = PurePosixPath(value)
        if rel.is_absolute() or ".." in rel.parts or "." in rel.parts or "\\" in value:
            raise ValueError(f"unsafe allowlist path at line {line_no}: {value!r}")
        canonical = rel.as_posix()
        if canonical in seen:
            raise ValueError(f"duplicate allowlist path at line {line_no}: {canonical}")
        seen.add(canonical)

        source = ROOT.joinpath(*rel.parts)
        current = ROOT
        for part in rel.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"symbolic links are not allowed: {canonical}")
        if not source.is_file():
            raise ValueError(f"allowlisted file is missing or not regular: {canonical}")
        if not source.resolve().is_relative_to(ROOT):
            raise ValueError(f"allowlisted path escapes repository: {canonical}")
        rows.append((canonical, source))
    if not rows:
        raise ValueError("release-files.txt contains no files")
    return rows


def export(out: Path) -> tuple[Path, Path]:
    files = listed_files()
    out = out.expanduser().resolve()
    archive = out.with_suffix(out.suffix + ".tar.gz")
    if out.exists() or archive.exists():
        raise FileExistsError(f"refusing to overwrite {out} or {archive}")
    if out == ROOT or ROOT in out.parents:
        raise ValueError("output directory must be outside the repository")
    if out in ROOT.parents:
        raise ValueError("output directory cannot contain the repository")

    out.mkdir(parents=True)
    manifest_lines: list[str] = []
    for relative, source in files:
        destination = out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination, follow_symlinks=False)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        manifest_lines.append(f"{digest}  {relative}\n")
    (out / "SOURCE-MANIFEST.sha256").write_text("".join(manifest_lines), encoding="utf-8")

    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=Path(out.name) / path.relative_to(out), recursive=False)
    return out, archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path,
                        help="new output directory; a .tar.gz is created beside it")
    args = parser.parse_args()
    try:
        directory, archive = export(args.out)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Exported {directory}")
    print(f"Archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
