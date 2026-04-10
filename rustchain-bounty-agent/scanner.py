"""GitHub bounty scanner using gh CLI."""

import json
import subprocess
import logging

log = logging.getLogger("scanner")

EXCLUDE_REPOS = ["solfoundry", "aporthq", "illbnm"]

class Scanner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.repo = cfg.target_repo

    def _gh(self, args: list[str]) -> list[dict]:
        """Run gh command and return JSON."""
        cmd = ["gh"] + args + ["--json", "number,title,url,body,labels,assignees,createdAt"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                log.warning("gh error: %s", result.stderr[:200])
                return []
            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            log.warning("gh failed: %s", e)
            return []

    def scan_bounties(self) -> list[dict]:
        """Scan for open bounty issues."""
        issues = self._gh([
            "issue", "list",
            "--repo", self.repo,
            "--state", "open",
            "--label", "bounty",
            "--limit", "50",
        ])

        # Filter: no assignee, has bounty label
        filtered = []
        for i in issues:
            assignees = i.get("assignees", [])
            if assignees:
                continue
            labels = [l.get("name", "") for l in i.get("labels", [])]
            if "bounty" not in labels and "BOUNTY" not in str(i.get("title", "")).upper():
                continue
            filtered.append(i)

        log.info("Scanned %d issues, %d unassigned bounties", len(issues), len(filtered))
        return filtered
