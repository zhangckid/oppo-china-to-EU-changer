import hashlib
import importlib.util
from pathlib import Path
import re
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("source_export", ROOT / "scripts/export_source.py")
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class ReleaseTests(unittest.TestCase):
    def test_real_allowlist_is_complete_and_export_is_self_contained(self):
        entries = dict(EXPORT.listed_files())
        self.assertIn("release-files.txt", entries)
        for directory in ("changer", "tests", "scripts"):
            for path in (ROOT / directory).glob("*.py"):
                self.assertIn(path.relative_to(ROOT).as_posix(), entries)
        for name in entries:
            self.assertNotIn(name.split("/")[0], {"runs", "backup", "private", "downloads", "artifacts", "dist"})
            self.assertNotRegex(name, r"\.(?:img|apk|zip|log|jsonl|bin)$")
        with tempfile.TemporaryDirectory() as temp:
            out, archive = EXPORT.export(Path(temp) / "public-source")
            self.assertEqual({p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()},
                             set(entries) | {"SOURCE-MANIFEST.sha256"})
            for row in (out / "SOURCE-MANIFEST.sha256").read_text().splitlines():
                sha, name = row.split("  ", 1)
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), sha)
            with tarfile.open(archive) as source:
                self.assertEqual(len(source.getmembers()), len(entries) + 1)
                self.assertTrue(all(member.isfile() and not member.issym() for member in source))

    def test_private_sibling_is_not_exported_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            repo.mkdir()
            (repo / "allowed.txt").write_text("public")
            (repo / "private.json").write_text("private test evidence")
            allow = repo / "release-files.txt"
            allow.write_text("allowed.txt\n")
            with patch.object(EXPORT, "ROOT", repo), patch.object(EXPORT, "ALLOWLIST", allow):
                # Match the documented ../releases style, not just a canonical
                # absolute path; '..' must resolve before containment checks.
                out, _ = EXPORT.export(repo / ".." / "out")
                self.assertFalse((out / "private.json").exists())
                with self.assertRaises(FileExistsError):
                    EXPORT.export(out)
                (repo / "link.txt").symlink_to(repo / "private.json")
                allow.write_text("link.txt\n")
                with self.assertRaises(ValueError):
                    EXPORT.listed_files()
                allow.write_text("../private.json\n")
                with self.assertRaises(ValueError):
                    EXPORT.listed_files()

    def test_all_bilingual_markdown_links_resolve_locally(self):
        files = [ROOT / "README.md", ROOT / "README.zh-CN.md", *sorted((ROOT / "docs").glob("*.md"))]
        self.assertTrue(files)
        for file in files:
            text = file.read_text()
            companion = file.with_name(file.name.replace(".zh-CN.md", ".md") if file.name.endswith(".zh-CN.md")
                                       else file.stem + ".zh-CN.md")
            self.assertTrue(companion.is_file(), f"Missing language companion: {file}")
            self.assertIn(companion.name, text, f"Missing language switch: {file}")
            for destination in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                if re.match(r"(?:https?://|mailto:|#)", destination):
                    continue
                relative = unquote(destination.split("#", 1)[0])
                self.assertTrue((file.parent / relative).exists(), f"Broken local link in {file}: {destination}")


if __name__ == "__main__":
    unittest.main()
