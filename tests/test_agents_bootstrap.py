from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "agents_bootstrap.py"


class AgentsBootstrapTests(unittest.TestCase):
    def run_cli(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--repo", str(repo)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_init_writes_mirrored_files_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            repo.joinpath("pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")

            result = self.run_cli(repo, "init", "--yes")

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = repo.joinpath("AGENTS.md").read_text(encoding="utf-8")
            claude = repo.joinpath("CLAUDE.md").read_text(encoding="utf-8")
            manifest = json.loads(repo.joinpath(".agents/manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(agents, claude)
            self.assertIn("## Python", agents)
            self.assertNotIn("## TypeScript", agents)
            self.assertEqual(manifest["status"], "installed")
            self.assertEqual(manifest["languages"], ["python"])

    def test_typescript_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            repo.joinpath("package.json").write_text("{\"scripts\": {}}\n", encoding="utf-8")
            repo.joinpath("src").mkdir()
            repo.joinpath("src/index.ts").write_text("export const value = 1;\n", encoding="utf-8")

            result = self.run_cli(repo, "init", "--yes")

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = repo.joinpath("AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("## TypeScript", agents)
            self.assertNotIn("## Python", agents)

    def test_decline_writes_only_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)

            result = self.run_cli(repo, "init", "--decline")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(repo.joinpath("AGENTS.md").exists())
            manifest = json.loads(repo.joinpath(".agents/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "declined")

    def test_reference_is_inlined(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            reference = repo / "extra.md"
            reference.write_text("## Local Rule\n- Keep it small.\n", encoding="utf-8")

            result = self.run_cli(repo, "init", "--yes", "--reference", str(reference))

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = repo.joinpath("AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("## Additional Reference", agents)
            self.assertIn("## Local Rule", agents)

    def test_custom_set_path_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            repo = base / "repo"
            custom_set = base / "custom-set"
            repo.mkdir()
            custom_set.mkdir()
            custom_set.joinpath("metadata.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "name": "custom-set",
                        "core": "core.md",
                        "languageBlocks": {
                            "python": "python.md",
                        },
                    }
                ),
                encoding="utf-8",
            )
            custom_set.joinpath("core.md").write_text("# Custom Core\n", encoding="utf-8")
            custom_set.joinpath("python.md").write_text("## Python\n- Custom Python rule.\n", encoding="utf-8")
            repo.joinpath("pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")

            result = self.run_cli(repo, "init", "--yes", "--set", str(custom_set))

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = repo.joinpath("AGENTS.md").read_text(encoding="utf-8")
            manifest = json.loads(repo.joinpath(".agents/manifest.json").read_text(encoding="utf-8"))
            self.assertIn("# Custom Core", agents)
            self.assertIn("- Custom Python rule.", agents)
            self.assertEqual(manifest["set"], str(custom_set))

    def test_check_reports_missing_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)

            result = self.run_cli(repo, "check")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Manifest: missing", result.stdout)


if __name__ == "__main__":
    unittest.main()
