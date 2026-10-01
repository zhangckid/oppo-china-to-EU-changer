import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from changer.cli import main
from changer.runner import create_run, load_state, save_state


class GuideTests(unittest.TestCase):
    def test_guide_reads_journal_without_device_access_or_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run with spaces"
            create_run(root, {})
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            with patch("changer.cli.Runner", side_effect=AssertionError("device execution")), \
                 patch("subprocess.Popen", side_effect=AssertionError("subprocess")):
                for language in ("en", "zh-CN"):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(["guide", str(root), "--language", language]), 0)
                    self.assertIn("prepared", output.getvalue())
                    self.assertIn("docs/CLI", output.getvalue())
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_uncertain_states_do_not_offer_resume_or_phone_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            create_run(root, {})
            for stage, run_status in (("waiting_format", "executing"), ("waiting_format", "running"),
                                      ("review_required", "review_required"), ("waiting_format", "review_required"),
                                      ("complete", "waiting")):
                state = load_state(root)
                state.update(stage=stage, status=run_status)
                save_state(root, state)
                for language in ("en", "zh-CN"):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(["guide", str(root), "--language", language]), 0)
                    text = output.getvalue()
                    self.assertNotIn("--execute", text)
                    self.assertNotIn("--ack-stage", text)
                    self.assertNotIn("Format Data", text)
                    self.assertNotIn("docs/CLI", text)

    def test_corrupt_journal_stops_without_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            create_run(root, {})
            p = root / "state.json"
            corrupted = p.read_bytes().replace(b'"prepared"', b'"complete"')
            p.write_bytes(corrupted)
            with contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(main(["guide", str(root)]), 2)
            self.assertIn("checksum mismatch", error.getvalue())
            self.assertEqual(p.read_bytes(), corrupted)


if __name__ == "__main__":
    unittest.main()
