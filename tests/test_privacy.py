import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts/check_public_tree.py"
spec = importlib.util.spec_from_file_location("public_check", MODULE)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class PrivacyTests(unittest.TestCase):
    def test_detects_secret_patterns_without_including_values(self):
        values = ["gh" + "p_" + "Z" * 30,
                  ".".join(["192", "168", "42", "17"]),
                  "person" + "@" + "example.invalid",
                  "/" + "home/" + "person/" + "file"]
        for value in values:
            with self.subTest(kind=values.index(value)):
                found = check.findings("README.md", value.encode())
                self.assertTrue(found)
                self.assertNotIn(value, " ".join(found))

    def test_rejects_private_paths_and_binary_artifacts(self):
        self.assertIn("caminho privado", check.findings("reports/dump.json", b"{}"))
        self.assertIn("artefato privado/binário", check.findings("backup.apk", b"PK"))
        self.assertFalse(check.findings("docs/modelo.md", b"TCL 40S615 / C06 / T221T01"))

    @unittest.skipUnless(shutil.which("git"), "Teste do índice requer git")
    def test_staged_scan_sees_secret_even_if_worktree_was_cleaned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            target = root / "note.md"
            target.write_text("gh" + "p_" + "Q" * 30)
            subprocess.run(["git", "-C", str(root), "add", "note.md"], check=True)
            target.write_text("Conteúdo local agora limpo")
            _, staged = check.audit(root, staged=True)
            _, local = check.audit(root, staged=False)
            self.assertTrue(staged)
            self.assertFalse(local)


if __name__ == "__main__":
    unittest.main()
