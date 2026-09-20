"""Isolated Git worktree operations for the coding agent."""

import asyncio
import os
import shutil
import shlex
import subprocess
import tempfile
import base64
import json
import tarfile
import logging
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from services.coding_agent_policy import validate_repository_file

logger = logging.getLogger(__name__)


class SandboxError(RuntimeError):
    pass


class GitSandbox:
    def __init__(self, repo_path: str, branch: str, preview_root: str | None = None, token: str | None = None):
        self.source = repo_path
        self.repo_path: Path | None = None
        self.branch = branch
        self.token = token
        self.root: Path | None = None
        self.keep_root = False
        self.preview_root = Path(preview_root).resolve() if preview_root else None
        self._clone_root: Path | None = None

    async def __aenter__(self):
        return await asyncio.to_thread(self._enter)

    async def __aexit__(self, exc_type, exc, tb):
        await asyncio.to_thread(self._exit)

    def _run(self, *args, cwd=None, check=True, input_text=None):
        result = subprocess.run(
            ["git", *args], cwd=str(cwd or self.root or self.repo_path),
            text=True, capture_output=True, check=False,
            input=input_text,
            env={key: value for key, value in os.environ.items() if key != "GIT_ASKPASS"},
        )
        if check and result.returncode:
            raise SandboxError(result.stderr.strip() or result.stdout.strip() or "Git command failed.")
        return result.stdout

    def _enter(self):
        self.repo_path = self._checkout_source()
        if not (self.repo_path / ".git").exists():
            raise SandboxError("The configured repository is not a Git checkout.")
        if self.preview_root:
            self.preview_root.mkdir(parents=True, exist_ok=True)
            self.root = self.preview_root / f"{self.branch.replace('/', '-')}-{next(tempfile._get_candidate_names())}"
        else:
            self.root = Path(tempfile.mkdtemp(prefix="seo-coding-"))
        self._run("worktree", "add", "--detach", str(self.root), self.branch, cwd=self.repo_path)
        return self

    def _checkout_source(self) -> Path:
        candidate = Path(self.source)
        if candidate.exists():
            return candidate.resolve()
        if not self.source.startswith(("https://", "http://")):
            raise SandboxError("The selected repository source is not available.")
        logger.info("coding_sandbox.git.clone.start branch=%s", self.branch)
        self._clone_root = Path(tempfile.mkdtemp(prefix="seo-coding-source-"))
        destination = self._clone_root / "repository"
        remote = self.source
        if self.token and "github.com" in remote.lower():
            parsed = urlsplit(remote)
            remote = f"{parsed.scheme}://x-access-token:{self.token}@{parsed.netloc}{parsed.path}"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", self.branch, remote, str(destination)],
            text=True, capture_output=True, check=False,
        )
        if result.returncode:
            message = (result.stderr or result.stdout or "Git clone failed.").replace(self.token or "", "***")
            raise SandboxError(message.strip())
        logger.info("coding_sandbox.git.clone.success branch=%s", self.branch)
        return destination

    async def verify_remote(self, owner: str, repo: str) -> None:
        await asyncio.to_thread(self._verify_remote, owner, repo)

    def _verify_remote(self, owner: str, repo: str) -> None:
        remote = self._run("remote", "get-url", "origin").strip().lower()
        expected = f"{owner}/{repo}".strip("/").lower().removesuffix(".git")
        normalized = remote.removesuffix("/").removesuffix(".git")
        if normalized.endswith(expected):
            return
        raise SandboxError("The configured checkout does not match the selected GitHub repository.")

    def _exit(self):
        if self.root and not self.keep_root:
            subprocess.run(["git", "worktree", "remove", "--force", str(self.root)], cwd=str(self.repo_path), capture_output=True)
            shutil.rmtree(self.root, ignore_errors=True)
            self.root = None
        if self._clone_root:
            shutil.rmtree(self._clone_root, ignore_errors=True)
            self._clone_root = None

    async def files_for_context(self, limit: int = 30) -> dict[str, str]:
        return await asyncio.to_thread(self._files_for_context, limit)

    def _files_for_context(self, limit):
        assert self.root
        paths = []
        for extension in ("*.html", "*.htm", "*.md", "*.mdx"):
            paths.extend(self.root.rglob(extension))
        result = {}
        for path in sorted(paths)[:limit]:
            if ".git" not in path.parts and "node_modules" not in path.parts:
                result[str(path.relative_to(self.root)).replace("\\", "/")] = path.read_text(encoding="utf-8", errors="replace")[:20000]
        return result

    async def apply_and_test(self, patch: str, branch_name: str, keep_preview: bool = False) -> dict:
        return await asyncio.to_thread(self._apply_and_test, patch, branch_name, keep_preview)

    def _apply_and_test(self, patch, branch_name, keep_preview=False):
        assert self.root
        self._run("apply", "--check", "--whitespace=error", "-", cwd=self.root, check=True, input_text=patch)
        process = subprocess.run(["git", "apply", "--whitespace=error", "-"], cwd=str(self.root), input=patch, text=True, capture_output=True)
        if process.returncode:
            raise SandboxError(process.stderr.strip() or "Git rejected the patch.")
        status = self._run("status", "--short", cwd=self.root)
        diff = self._run("diff", "--no-ext-diff", "--binary", cwd=self.root)
        self._run("diff", "--check", cwd=self.root)
        changed_files = [line[6:] for line in patch.splitlines() if line.startswith("+++ b/")]
        for relative_path in changed_files:
            validate_repository_file(
                relative_path,
                (self.root / relative_path).read_text(encoding="utf-8", errors="replace"),
            )
        self._run("checkout", "-b", branch_name, cwd=self.root)
        self._run("add", "--", *[line[6:] for line in patch.splitlines() if line.startswith("+++ b/")], cwd=self.root)
        self._run("commit", "-m", "seo: apply approved content update", cwd=self.root)
        commit = self._run("rev-parse", "HEAD", cwd=self.root).strip()
        self.keep_root = keep_preview
        return {
            "status": status, "diff": diff, "commit": commit, "branch": branch_name,
            "preview_path": str(self.root) if keep_preview else "",
            "sandbox_tests": {"git_diff_check": "passed", "protected_content_scan": "passed"},
        }

    async def publish_branch(self, patch: str, branch_name: str, token: str | None = None) -> dict:
        return await asyncio.to_thread(self._publish_branch, patch, branch_name, token)

    def _publish_branch(self, patch, branch_name, token=None):
        result = self._apply_and_test(patch, branch_name, keep_preview=False)
        remote = self._run("remote", "get-url", "origin", cwd=self.root).strip()
        env = {key: value for key, value in os.environ.items() if key != "GIT_ASKPASS"}
        askpass = None
        try:
            if token and "github.com" in remote.lower():
                askpass = self.root / ".git" / "seo-agent-askpass.bat"
                askpass.write_text(
                    "@echo off\r\n"
                    "echo %GIT_PASSWORD%\r\n",
                    encoding="utf-8",
                )
                env["GIT_ASKPASS"] = str(askpass)
                env["GIT_TERMINAL_PROMPT"] = "0"
                env["GIT_USERNAME"] = "x-access-token"
                env["GIT_PASSWORD"] = token
                parsed = urlsplit(remote if "://" in remote else f"https://{remote}")
                if parsed.scheme in {"http", "https"}:
                    remote = f"{parsed.scheme}://x-access-token@{parsed.netloc}{parsed.path}"
            process = subprocess.run(
                ["git", "push", remote, f"{branch_name}:{branch_name}"],
                cwd=str(self.root), text=True, capture_output=True, env=env,
            )
            if process.returncode:
                message = (process.stderr or process.stdout or "Git push failed.").replace(token or "", "***")
                raise SandboxError(message.strip())
        finally:
            if askpass:
                askpass.unlink(missing_ok=True)
        return result | {"pushed": True}


class DaytonaSandbox:
    """Hosted sandbox adapter.

    The SDK is imported only when this provider is selected. Repository data
    is uploaded into a disposable Daytona sandbox; no host checkout is used.
    """

    def __init__(self, repo_path: str, branch: str, token: str | None = None):
        self.source = repo_path
        self.repo_path: Path | None = None
        self.branch = branch
        self.token = token
        self.client = None
        self.sandbox = None
        self.root = "/home/daytona/workspace"
        self._archive_path: Path | None = None
        self._clone_root: Path | None = None

    async def __aenter__(self):
        try:
            from daytona import AsyncDaytona, CreateSandboxFromSnapshotParams, DaytonaConfig
            from core.config import settings
            target = settings.DAYTONA_TARGET.strip() or None
            self.client = AsyncDaytona(DaytonaConfig(
                api_key=settings.DAYTONA_API_KEY,
                api_url=settings.DAYTONA_API_URL,
                target=target,
            ))
            name = self._sandbox_name(settings.DAYTONA_SANDBOX_NAME_PREFIX)
            params = CreateSandboxFromSnapshotParams(
                name=name,
                language="python",
                auto_stop_interval=settings.DAYTONA_SANDBOX_AUTO_STOP_MINUTES,
                auto_archive_interval=settings.DAYTONA_SANDBOX_AUTO_ARCHIVE_MINUTES,
                ephemeral=settings.DAYTONA_SANDBOX_EPHEMERAL,
                labels={"seo-agent-purpose": "coding-agent-proposal"},
            )
            self.sandbox = await self.client.create(params)
            logger.info("coding_sandbox.daytona.created name=%s", name)
            await self._exec(f"mkdir -p {shlex.quote(self.root)}", cwd="/home/daytona")
            self.repo_path = await asyncio.to_thread(self._checkout_source)
            archive = await asyncio.to_thread(self._archive)
            await self.sandbox.fs.upload_file(str(archive), "/tmp/seo-repository.tar.gz")
            await self._exec(
                f"tar -xzf /tmp/seo-repository.tar.gz -C {shlex.quote(self.root)}",
                cwd="/home/daytona",
            )
            await self._exec("git config user.email seo-agent@example.invalid")
            await self._exec("git config user.name 'SEO Coding Agent'")
            await self._exec("git reset --hard HEAD")
            logger.info("coding_sandbox.daytona.ready name=%s", name)
            return self
        except ImportError as exc:
            raise SandboxError("Install the optional Daytona provider dependency first.") from exc

    def _sandbox_name(self, prefix: str) -> str:
        safe_branch = "".join(
            character if character.isalnum() or character in {"-", "_"} else "-"
            for character in self.branch
        ).strip("-_")[:48] or "head"
        safe_prefix = "".join(
            character if character.isalnum() or character in {"-", "_"} else "_"
            for character in prefix
        ).strip("-_") or "SEO_agent_sandbox"
        return f"{safe_prefix}-{safe_branch}-{uuid4().hex[:8]}"

    async def __aexit__(self, exc_type, exc, tb):
        if self.client and self.sandbox:
            await self.client.delete(self.sandbox, wait=True)
            logger.info("coding_sandbox.daytona.deleted")
        if self.client:
            await self.client.close()
        if self._archive_path:
            shutil.rmtree(self._archive_path.parent, ignore_errors=True)
            self._archive_path = None
        if self._clone_root:
            shutil.rmtree(self._clone_root, ignore_errors=True)
            self._clone_root = None

    def _checkout_source(self) -> Path:
        candidate = Path(self.source)
        if candidate.exists():
            return candidate.resolve()
        if not self.source.startswith(("https://", "http://")):
            raise SandboxError("The selected repository source is not available.")
        logger.info("coding_sandbox.daytona.clone.start branch=%s", self.branch)
        self._clone_root = Path(tempfile.mkdtemp(prefix="seo-daytona-source-"))
        destination = self._clone_root / "repository"
        remote = self.source
        if self.token and "github.com" in remote.lower():
            parsed = urlsplit(remote)
            remote = f"{parsed.scheme}://x-access-token:{self.token}@{parsed.netloc}{parsed.path}"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", self.branch, remote, str(destination)],
            text=True, capture_output=True, check=False,
        )
        if result.returncode:
            message = (result.stderr or result.stdout or "Git clone failed.").replace(self.token or "", "***")
            raise SandboxError(message.strip())
        logger.info("coding_sandbox.daytona.clone.success branch=%s", self.branch)
        return destination

    def _archive(self):
        assert self.repo_path
        archive_dir = Path(tempfile.mkdtemp(prefix="seo-daytona-upload-"))
        archive = archive_dir / "repository.tar.gz"
        ignored_dirs = {
            ".mypy_cache", ".next", ".pytest_cache", ".ruff_cache", ".venv",
            "__pycache__", "build", "dist", "node_modules",
        }
        ignored_files = {".env", ".env.local", ".env.production"}
        with tarfile.open(archive, "w:gz") as tar:
            for path in self.repo_path.rglob("*"):
                relative = path.relative_to(self.repo_path)
                if any(part in ignored_dirs for part in relative.parts):
                    continue
                if path.name in ignored_files:
                    continue
                tar.add(path, arcname=relative, recursive=False)
        self._archive_path = archive
        return archive

    async def _exec(self, command: str, cwd: str | None = None) -> str:
        response = await self.sandbox.process.exec(command, cwd=cwd or self.root, timeout=120)
        result = getattr(response, "result", "")
        if getattr(response, "exit_code", 0) not in (0, None):
            raise SandboxError(str(result) or "Daytona command failed.")
        return str(result)

    async def verify_remote(self, owner: str, repo: str) -> None:
        remote = (await self._exec("git remote get-url origin")).strip().lower()
        expected = f"{owner}/{repo}".strip("/").lower().removesuffix(".git")
        if not remote.removesuffix("/").removesuffix(".git").endswith(expected):
            raise SandboxError("The uploaded checkout does not match the selected GitHub repository.")

    async def files_for_context(self, limit: int = 30) -> dict[str, str]:
        listing = await self._exec("find . -type f \( -name '*.html' -o -name '*.htm' -o -name '*.md' -o -name '*.mdx' \) | sort | head -30")
        result = {}
        for relative in listing.splitlines()[:limit]:
            relative = relative.removeprefix("./")
            content = await self._exec(f"cat -- {shlex.quote(relative)}")
            result[relative] = content[:20000]
        return result

    async def apply_and_test(self, patch: str, branch_name: str, keep_preview: bool = False) -> dict:
        encoded = base64.b64encode(patch.encode()).decode()
        await self._exec(f"echo {encoded} | base64 -d > /tmp/seo.patch")
        await self._exec("git apply --check --whitespace=error /tmp/seo.patch")
        await self._exec("git apply --whitespace=error /tmp/seo.patch")
        await self._exec("git diff --check")
        changed = [line[6:] for line in patch.splitlines() if line.startswith("+++ b/")]
        for relative in changed:
            content = await self._exec(f"cat -- {shlex.quote(relative)}")
            validate_repository_file(relative, content)
        await self._exec(f"git checkout -b {shlex.quote(branch_name)}")
        await self._exec("git add --all")
        await self._exec("git commit -m 'seo: apply approved content update'")
        commit = (await self._exec("git rev-parse HEAD")).strip()
        diff = await self._exec("git show --format= --no-ext-diff --binary HEAD")
        return {
            "status": "committed in Daytona",
            "diff": diff,
            "commit": commit,
            "branch": branch_name,
            "preview_path": "",
            "sandbox_tests": {"git_diff_check": "passed", "protected_content_scan": "passed"},
        }

    async def publish_branch(self, patch: str, branch_name: str, token: str | None = None) -> dict:
        if token:
            raise SandboxError("Daytona publishing is disabled until repository credentials are mounted as sandbox secrets.")
        raise SandboxError("Production PR publishing requires a local checkout with GitHub credentials.")


def create_sandbox(repo_path: str, branch: str, token: str | None = None):
    from core.config import settings
    if settings.CODING_AGENT_ENVIRONMENT.lower() == "test":
        return GitSandbox(repo_path, branch, preview_root=settings.CODING_AGENT_PREVIEW_ROOT, token=token)
    if settings.CODING_AGENT_SANDBOX_PROVIDER.lower() == "daytona":
        if not settings.DAYTONA_API_KEY:
            raise SandboxError("CODING_AGENT_SANDBOX_PROVIDER=daytona requires DAYTONA_API_KEY.")
        return DaytonaSandbox(repo_path, branch, token=token)
    if settings.CODING_AGENT_SANDBOX_PROVIDER.lower() != "local":
        raise SandboxError("Unknown coding sandbox provider.")
    return GitSandbox(repo_path, branch, token=token)


def create_publish_sandbox(repo_path: str, branch: str, token: str | None = None):
    """Use the host checkout for publishing approved branches.

    Hosted proposal sandboxes intentionally do not receive GitHub credentials.
    The approval step publishes from the configured checkout after the stored
    diff has already passed policy and sandbox validation.
    """
    return GitSandbox(repo_path, branch, token=token)
