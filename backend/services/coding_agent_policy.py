"""Hard limits for the SEO coding agent.

This policy is intentionally conservative. A generated patch is untrusted input
until it passes every check here and `git apply --check` in the sandbox.
"""

from pathlib import PurePosixPath
import re


ALLOWED_EXTENSIONS = {".html", ".htm", ".md", ".mdx"}
MAX_FILES = 5
MAX_ADDED_LINES = 160
MAX_REMOVED_LINES = 160
FORBIDDEN_PATH_PARTS = {".git", "node_modules", "dist", "build", "vendor"}
FORBIDDEN_CONTENT = re.compile(
    r"(<script\b|</script>|javascript:|\bon(?:click|load|error|submit)\s*=|"
    r"<style\b|</style>|\b(import|require)\s*\(|\b(const|let|var|function)\s+)",
    re.IGNORECASE,
)


class CodingPolicyError(ValueError):
    pass


def validate_patch(patch: str, allowed_paths: set[str] | None = None) -> dict:
    if not patch.strip():
        raise CodingPolicyError("The coding agent produced an empty patch.")
    lines = patch.splitlines()
    files = []
    added = removed = 0
    current_file = None
    for line in lines:
        if line.startswith("+++ b/"):
            current_file = line[6:]
            files.append(current_file)
            path = PurePosixPath(current_file)
            if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                raise CodingPolicyError(f"Only HTML/content files may change: {current_file}")
            if any(part in FORBIDDEN_PATH_PARTS for part in path.parts):
                raise CodingPolicyError(f"Generated/vendor files may not change: {current_file}")
            if allowed_paths is not None and current_file not in allowed_paths:
                raise CodingPolicyError(f"Test mode may only change approved homepage files: {current_file}")
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
            if FORBIDDEN_CONTENT.search(line[1:]):
                raise CodingPolicyError("The patch contains script, event-handler, CSS, or code logic.")
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
            if FORBIDDEN_CONTENT.search(line[1:]):
                raise CodingPolicyError("The patch removes protected script, event-handler, CSS, or code logic.")
    if len(set(files)) > MAX_FILES:
        raise CodingPolicyError(f"A coding task may change at most {MAX_FILES} files.")
    if added > MAX_ADDED_LINES or removed > MAX_REMOVED_LINES:
        raise CodingPolicyError("The generated diff is larger than the SEO change budget.")
    if not files:
        raise CodingPolicyError("The patch did not contain a file header.")
    return {"files": sorted(set(files)), "added_lines": added, "removed_lines": removed}


def validate_repository_file(path: str, content: str) -> None:
    """Run a cheap sandbox assertion on changed content before commit."""
    if PurePosixPath(path).suffix.lower() in {".html", ".htm"}:
        if FORBIDDEN_CONTENT.search(content):
            raise CodingPolicyError(f"Protected executable content was found in {path}.")
