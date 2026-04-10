"""PR submission with quality gates."""

import json
import subprocess
import logging

log = logging.getLogger("submitter")


class Submitter:
    def __init__(self, cfg):
        self.cfg = cfg

    def _run(self, cmd: list[str]) -> tuple[bool, str]:
        """Run shell command."""
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return r.returncode == 0, r.stdout.strip() or r.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "timeout"

    def quality_check(self, work_dir: str) -> tuple[bool, list[str]]:
        """Run quality checks on code."""
        issues = []

        # Python lint
        ok, _ = self._run(["python3", "-m", "py_compile", work_dir])
        if not ok:
            issues.append("Python syntax check failed")

        # Check for secrets
        ok, output = self._run(["grep", "-r", "-l", "-E", "(api_key|secret|password)\\s*=", work_dir])
        if ok and output:
            issues.append(f"Potential secrets found in: {output}")

        return len(issues) == 0, issues

    def create_pr(self, repo: str, branch: str, title: str, body: str) -> str:
        """Create a PR via gh CLI."""
        ok, output = self._run([
            "gh", "pr", "create",
            "--repo", repo,
            "--head", branch,
            "--base", "main",
            "--title", title,
            "--body", body,
        ])
        if ok:
            log.info("PR created: %s", output)
            return output
        else:
            log.error("PR creation failed: %s", output)
            return ""
