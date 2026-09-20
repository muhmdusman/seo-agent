import asyncio
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from services.coding_agent_sandbox import DaytonaSandbox, GitSandbox


class CodingAgentSandboxTests(unittest.TestCase):
    def test_applies_and_commits_in_isolated_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            (repo / "index.html").write_text("<title>Old</title>\n", encoding="utf-8")
            subprocess.run(["git", "add", "index.html"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
            subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/site.git"], cwd=repo, check=True)

            async def exercise():
                async with GitSandbox(str(repo), "HEAD") as sandbox:
                    await sandbox.verify_remote("acme", "site")
                    result = await sandbox.apply_and_test(
                        "--- a/index.html\n+++ b/index.html\n@@ -1 +1 @@\n-<title>Old</title>\n+<title>New</title>\n",
                        "seo-agent/test",
                    )
                    return result

            result = asyncio.run(exercise())
            self.assertEqual(result["sandbox_tests"]["protected_content_scan"], "passed")
            self.assertEqual((repo / "index.html").read_text(encoding="utf-8"), "<title>Old</title>\n")

    def test_daytona_exec_allows_bootstrap_cwd_override(self):
        calls = []

        class FakeProcess:
            async def exec(self, command, cwd, timeout):
                calls.append({"command": command, "cwd": cwd, "timeout": timeout})
                return SimpleNamespace(exit_code=0, result="ok")

        sandbox = DaytonaSandbox("unused", "main")
        sandbox.sandbox = SimpleNamespace(process=FakeProcess())

        result = asyncio.run(sandbox._exec("mkdir -p /home/daytona/workspace", cwd="/home/daytona"))

        self.assertEqual(result, "ok")
        self.assertEqual(calls, [{
            "command": "mkdir -p /home/daytona/workspace",
            "cwd": "/home/daytona",
            "timeout": 120,
        }])

    def test_daytona_archive_filters_ignored_nested_content(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            (repo / ".git" / "config").write_text(
                "[remote \"origin\"]\n\turl = https://github.com/acme/site.git\n",
                encoding="utf-8",
            )
            (repo / "src" / "node_modules").mkdir(parents=True)
            (repo / "src" / "note.md").write_text("hello\n", encoding="utf-8")
            (repo / "src" / "node_modules" / "bad.md").write_text("ignored\n", encoding="utf-8")
            (repo / ".env").write_text("SECRET=ignored\n", encoding="utf-8")

            sandbox = DaytonaSandbox(str(repo), "main")
            sandbox.repo_path = repo
            archive = sandbox._archive()
            try:
                with tarfile.open(archive, "r:gz") as tar:
                    names = set(tar.getnames())
            finally:
                sandbox._archive_path = archive
                asyncio.run(sandbox.__aexit__(None, None, None))

            self.assertIn("src/note.md", names)
            self.assertIn(".git/config", names)
            self.assertNotIn(".env", names)
            self.assertNotIn("src/node_modules/bad.md", names)


if __name__ == "__main__":
    unittest.main()
