#!/usr/bin/env python3
"""BCOS v2 GitHub Action — scan, comment, anchor."""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# ── Config from environment ─────────────────────────────────────
TIER = os.getenv("BCOS_TIER", "L1")
REVIEWER = os.getenv("BCOS_REVIEWER", "bcos-ci")
NODE_URL = os.getenv("BCOS_NODE_URL", "https://50.28.86.131")
REPO_PATH = os.getenv("BCOS_REPO_PATH", os.getcwd())
ENGINE_URL = os.getenv("BCOS_ENGINE_URL", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
ANCHOR_ON_MERGE = os.getenv("BCOS_ANCHOR_ON_MERGE", "true").lower() == "true"
ADMIN_KEY = os.getenv("BCOS_ADMIN_KEY", "")
FAIL_ON_MISS = os.getenv("BCOS_FAIL_ON_TIER_MISS", "true").lower() == "true"
PR_NUMBER = os.getenv("PR_NUMBER", "")
EVENT_ACTION = os.getenv("EVENT_ACTION", "")
PR_MERGED = os.getenv("PR_MERGED", "false").lower() == "true"
REPO_OWNER = os.getenv("REPO_OWNER", "")
REPO_NAME = os.getenv("REPO_NAME", "")
PR_HEAD_SHA = os.getenv("PR_HEAD_SHA", "")
GITHUB_ACTION_PATH = os.getenv("GITHUB_ACTION_PATH", "")

TIER_THRESHOLDS = {"L0": 40, "L1": 60, "L2": 80}
TIER_COLORS = {"L0": "yellow", "L1": "green", "L2": "blue"}
TIER_BADGE_BG = {"L0": "#dfb317", "L1": "#4c1", "L2": "#007ec6"}


def log(msg):
    print(f"::notice::{msg}")


def warning(msg):
    print(f"::warning::{msg}")


def set_output(name, value):
    # GitHub Actions output format
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
        f.write(f"{name}={value}\n")
    # Also print for debugging
    print(f"::set-output name={name}::{value}")


def download_engine():
    """Download bcos_engine.py from RustChain repo or specified URL."""
    engine_path = Path("/tmp/bcos_engine.py")
    if engine_path.exists():
        return str(engine_path)
    
    url = ENGINE_URL
    if not url:
        url = "https://raw.githubusercontent.com/Scottcjn/RustChain/main/tools/bcos_engine.py"
    
    log(f"Downloading BCOS engine from {url}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            engine_path.write_bytes(content)
            log(f"Downloaded {len(content)} bytes")
            return str(engine_path)
    except Exception as e:
        # Fallback: look in the action path
        fallback = Path(GITHUB_ACTION_PATH) / "vendor" / "bcos_engine.py"
        if fallback.exists():
            return str(fallback)
        raise RuntimeError(f"Failed to download BCOS engine: {e}")


def run_bcos_scan(repo_path, tier, reviewer):
    """Run the BCOS engine and return the JSON report."""
    engine = download_engine()
    cmd = [
        sys.executable, engine,
        repo_path,
        "--tier", tier,
        "--reviewer", reviewer,
        "--json"
    ]
    log(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode != 0:
        log(f"BCOS stderr: {result.stderr[:500]}")
    
    # Parse JSON output from stdout
    output = result.stdout.strip()
    if not output:
        # Try to find JSON in stderr
        for line in result.stderr.split("\n"):
            if line.startswith("{"):
                output = line
                break
    
    if not output:
        raise RuntimeError("BCOS engine produced no output")
    
    report = json.loads(output)
    return report


def get_highest_achieved_tier(score):
    """Determine the highest tier achieved based on score."""
    if score >= TIER_THRESHOLDS["L2"]:
        return "L2"
    elif score >= TIER_THRESHOLDS["L1"]:
        return "L1"
    else:
        return "L0"


def generate_cert_id(report, repo_path):
    """Generate a BCOS certificate ID from the report."""
    # Try to get from report, or generate one
    cert_id = report.get("cert_id", "")
    if cert_id:
        return cert_id
    
    # Generate from repo + tier + score
    repo_name = os.path.basename(repo_path)
    score = report.get("trust_score", 0)
    import hashlib
    data = f"{repo_name}-{score}-{TIER}"
    hash_val = hashlib.blake2b(data.encode(), digest_size=4).hexdigest()[:8].upper()
    return f"BCOS-{hash_val}"


def generate_badge_svg(score, tier_achieved):
    """Generate a shields.io-style badge URL."""
    label = "BCOS"
    color = TIER_COLORS.get(tier_achieved, "lightgrey")
    return f"https://img.shields.io/badge/{label}-v2%20{tier_achieved}%20({score})-{color}"


def generate_badge_markdown(cert_id, score, tier_achieved):
    """Generate markdown embed for the badge."""
    badge_url = f"{NODE_URL}/bcos/badge/{cert_id}.svg"
    verify_url = f"{NODE_URL}/bcos/verify/{cert_id}"
    return f"[![BCOS]({badge_url})]({verify_url})"


def format_pr_comment(report, cert_id, score, tier_achieved, tier_met, tier_required):
    """Generate a formatted PR comment with score breakdown."""
    breakdown = report.get("breakdown", report.get("checks", {}))
    
    # Build breakdown table
    rows = []
    for key, data in breakdown.items() if isinstance(breakdown, dict) else []:
        if isinstance(data, dict):
            pts = data.get("score", data.get("points", "?"))
            label = data.get("name", key.replace("_", " ").title())
            rows.append(f"| {label} | {pts} |")
        elif isinstance(data, (int, float)):
            rows.append(f"| {key.replace('_', ' ').title()} | {data} |")
    
    breakdown_table = "\n".join(rows) if rows else "| _Details_ | See report |"
    
    tier_status = "✅ PASS" if tier_met else "❌ FAIL"
    tier_color = "🟢" if tier_met else "🔴"
    
    comment = f"""## 🔍 BCOS v2 Scan Result

| Metric | Value |
|--------|-------|
| **Trust Score** | **{score}/100** |
| **Cert ID** | `{cert_id}` |
| **Tier Achieved** | {tier_color} **{tier_achieved}** |
| **Required Tier** | {TIER} |
| **Tier Status** | {tier_status} |

### Score Breakdown

| Check | Score |
|-------|-------|
{breakdown_table}

---

**Embed badge:** `{generate_badge_markdown(cert_id, score, tier_achieved)}`

<details>
<summary>Full JSON Report</summary>

```json
{json.dumps(report, indent=2)}
```

</details>
"""
    return comment


def post_pr_comment(comment):
    """Post a comment on the PR via GitHub API."""
    if not GITHUB_TOKEN or not PR_NUMBER or not REPO_OWNER or not REPO_NAME:
        warning("Missing GitHub context — skipping PR comment")
        return False
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    body = json.dumps({"body": comment}).encode()
    
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            log(f"PR comment posted: {resp.status}")
            return True
    except urllib.error.HTTPError as e:
        # Check if we already posted a BCOS comment
        if e.code == 422:
            warning(f"Failed to post comment: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        warning(f"Failed to post PR comment: {e}")
        return False


def anchor_attestation(report, cert_id, repo_path):
    """Anchor the BCOS attestation to RustChain."""
    if not ANCHOR_ON_MERGE or not ADMIN_KEY:
        log("Skipping attestation anchoring (anchor-on-merge=false or no admin key)")
        return None
    
    log(f"Anchoring attestation {cert_id} to RustChain...")
    
    # Compute BLAKE2b commitment
    import hashlib
    report_json = json.dumps(report, sort_keys=True)
    commitment = hashlib.blake2b(report_json.encode(), digest_size=32).hexdigest()
    
    # Get git HEAD SHA
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        head_sha = result.stdout.strip()
    except Exception:
        head_sha = PR_HEAD_SHA or "unknown"
    
    payload = {
        "cert_id": cert_id,
        "tier": TIER,
        "trust_score": report.get("trust_score", 0),
        "commitment": commitment,
        "commit_sha": head_sha,
        "repo": f"{REPO_OWNER}/{REPO_NAME}",
    }
    
    url = f"{NODE_URL}/bcos/anchor"
    headers = {
        "Content-Type": "application/json",
        "x-admin-key": ADMIN_KEY
    }
    body = json.dumps(payload).encode()
    
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            tx_hash = result.get("tx_hash", result.get("hash", "unknown"))
            log(f"Attestation anchored: tx={tx_hash}")
            return tx_hash
    except Exception as e:
        warning(f"Failed to anchor attestation: {e}")
        return None


def main():
    try:
        # 1. Run BCOS scan
        report = run_bcos_scan(REPO_PATH, TIER, REVIEWER)
        
        score = report.get("trust_score", 0)
        tier_achieved = get_highest_achieved_tier(score)
        tier_met = score >= TIER_THRESHOLDS.get(TIER, 40)
        cert_id = generate_cert_id(report, REPO_PATH)
        
        # 2. Set outputs
        set_output("trust_score", str(score))
        set_output("cert_id", cert_id)
        set_output("tier_met", str(tier_met).lower())
        set_output("tier_achieved", tier_achieved)
        set_output("report", json.dumps(report))
        
        log(f"BCOS v2 scan complete: score={score}, tier={tier_achieved}, cert={cert_id}")
        
        # 3. Post PR comment
        if PR_NUMBER and EVENT_ACTION in ("opened", "synchronize", "reopened"):
            comment = format_pr_comment(report, cert_id, score, tier_achieved, tier_met, TIER)
            post_pr_comment(comment)
        
        # 4. Anchor on merge
        if PR_MERGED and ANCHOR_ON_MERGE:
            tx_hash = anchor_attestation(report, cert_id, REPO_PATH)
            if tx_hash:
                merge_comment = f"""## 🔒 BCOS Attestation Anchored

Certificate `{cert_id}` has been anchored to RustChain.
Transaction: `{tx_hash}`
"""
                post_pr_comment(merge_comment)
        
        # 5. Exit status
        if tier_met or not FAIL_ON_MISS:
            sys.exit(0)
        else:
            log(f"Tier {TIER} not met (score {score} < {TIER_THRESHOLDS[TIER]})")
            if FAIL_ON_MISS:
                sys.exit(1)
            sys.exit(0)
    
    except Exception as e:
        print(f"::error::BCOS scan failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
