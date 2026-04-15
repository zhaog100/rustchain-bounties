#!/usr/bin/env python3
"""
RTC Reward Action — GitHub Action for automatically awarding RTC tokens on PR merge.

This action:
1. Checks if PR was merged
2. Reads contributor's RTC wallet from PR body or .rtc-wallet file
3. Calls RustChain VPS transfer API
4. Posts confirmation comment on PR

Usage:
  - uses: Scottcjn/rtc-reward-action@v1
    with:
      node-url: https://50.28.86.131
      amount: 5
      wallet-from: project-fund
      admin-key: ${{ secrets.RTC_ADMIN_KEY }}
"""

import json
import os
import re
import sys
import time
from typing import Optional, Tuple

import requests
from github import Github

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VPS_PORT = 8099
WALLET_PATTERN = re.compile(r'RTC\s*[Ww]allet[:\s]+([a-zA-Z0-9_-]+)', re.IGNORECASE)
ALREADY_PAID_MARKER = "RTC-Reward-Confirmed"

# ---------------------------------------------------------------------------
# Environment Helpers
# ---------------------------------------------------------------------------

def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

def env_required(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        print(f"::error::Missing required environment variable: {name}")
        sys.exit(1)
    return val

def parse_bool(val: str) -> bool:
    return val.lower() in ("true", "1", "yes", "on")

# ---------------------------------------------------------------------------
# GitHub API Helpers
# ---------------------------------------------------------------------------

def get_github_client() -> Github:
    token = env_required("GITHUB_TOKEN")
    return Github(token)

def get_repo(g: Github) -> Tuple:
    repo_name = env_required("REPO")  # e.g., "owner/repo"
    return g.get_repo(repo_name)

def get_pr(repo, pr_number: int):
    return repo.get_pull(pr_number)

def fetch_wallet_from_pr(pr) -> Optional[str]:
    """Extract RTC wallet from PR body."""
    body = pr.body or ""
    match = WALLET_PATTERN.search(body)
    if match:
        return match.group(1)
    return None

def fetch_wallet_from_file(repo, pr, wallet_file_path: str) -> Optional[str]:
    """Read RTC wallet from .rtc-wallet file in the PR."""
    try:
        # Get the file from the base branch
        contents = repo.get_contents(wallet_file_path, ref=pr.base.ref)
        content = contents.decoded_content.decode("utf-8").strip()
        # File might contain just the wallet name or "RTC Wallet: name"
        match = WALLET_PATTERN.search(content)
        if match:
            return match.group(1)
        return content if content else None
    except Exception as e:
        print(f"::warning::Could not read {wallet_file_path}: {e}")
        return None

def check_already_paid(repo, pr_number: int) -> bool:
    """Check if payment was already processed for this PR."""
    comments = pr.get_issue_comments()
    for comment in comments:
        if ALREADY_PAID_MARKER in comment.body:
            return True
    return False

def post_comment(repo, pr_number: int, body: str):
    """Post a comment on the PR."""
    issue = repo.get_issue(pr_number)
    issue.create_comment(body)
    print(f"✓ Posted comment on PR #{pr_number}")

# ---------------------------------------------------------------------------
# RustChain API
# ---------------------------------------------------------------------------

def transfer_rtc(node_url: str, admin_key: str, wallet_from: str,
                 wallet_to: str, amount: float, memo: str, dry_run: bool = False) -> dict:
    """Call the RustChain VPS transfer endpoint."""
    if dry_run:
        print(f"🧪 DRY RUN: Would transfer {amount} RTC from {wallet_from} to {wallet_to}")
        return {"ok": True, "pending_id": "dry-run-" + str(int(time.time())), "dry_run": True}

    # Determine if node_url is IP or includes protocol
    if node_url.startswith("http"):
        base_url = node_url
    else:
        base_url = f"http://{node_url}"

    url = f"{base_url}:{VPS_PORT}/wallet/transfer"

    payload = {
        "from_miner": wallet_from,
        "to_miner": wallet_to,
        "amount_rtc": amount,
        "memo": memo,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Admin-Key": admin_key,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError as e:
        print(f"::error::Cannot reach RustChain node at {url} — {e}")
        return {"ok": False, "error": f"Connection failed: {str(e)}"}
    except requests.exceptions.HTTPError as e:
        print(f"::error::RustChain node returned error: {e.response.status_code} — {e.response.text}")
        return {"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except requests.exceptions.Timeout:
        print(f"::error::Request timed out after 30s")
        return {"ok": False, "error": "Timeout"}

# ---------------------------------------------------------------------------
# Main Logic
# ---------------------------------------------------------------------------

def main() -> None:
    print("🚀 RTC Reward Action starting...")

    # Environment
    node_url = env_required("NODE_URL")
    amount_str = env_required("AMOUNT")
    wallet_from = env_required("WALLET_FROM")
    admin_key = env_required("ADMIN_KEY")
    dry_run = parse_bool(env("DRY_RUN", "false"))
    wallet_file_path = env("WALLET_FILE", ".rtc-wallet")

    pr_number = int(env_required("PR_NUMBER"))
    repo_name = env_required("REPO")
    pr_author = env_required("PR_AUTHOR")
    repo_owner = env_required("REPO_OWNER")

    try:
        amount = float(amount_str)
    except ValueError:
        print(f"::error::Invalid amount: {amount_str}")
        sys.exit(1)

    if amount <= 0:
        print(f"::warning::Amount is {amount} RTC — skipping.")
        return

    if amount > 10000:
        print(f"::error::Amount {amount} RTC exceeds safety limit of 10,000 RTC.")
        sys.exit(1)

    # GitHub setup
    print(f"📋 Processing PR #{pr_number} in {repo_name} (author: {pr_author})")
    g = get_github_client()
    repo = get_repo(g)
    pr = get_pr(repo, pr_number)

    # Check if PR is actually merged
    if not pr.merged:
        print(f"PR #{pr_number} was not merged. Skipping.")
        return

    # Check for duplicate payment
    if check_already_paid(repo, pr_number):
        print(f"✓ Payment already processed (found {ALREADY_PAID_MARKER}). Skipping.")
        return

    # Find contributor's wallet
    wallet = fetch_wallet_from_pr(pr)
    if not wallet:
        wallet = fetch_wallet_from_file(repo, pr, wallet_file_path)
    if not wallet:
        # Fallback: use GitHub username as wallet name
        wallet = pr_author
        print(f"⚠️ No wallet specified, using GitHub username: {wallet}")
    else:
        print(f"✓ Found wallet: {wallet}")

    # Execute transfer
    memo = f"PR #{pr_number} in {repo_name} — RTC Reward"
    print(f"💰 Transferring {amount} RTC from {wallet_from} to {wallet}")

    result = transfer_rtc(node_url, admin_key, wallet_from, wallet, amount, memo, dry_run)

    ok = result.get("ok", False)
    pending_id = result.get("pending_id", result.get("tx_id", "n/a"))
    error = result.get("error", "")

    if not ok:
        print(f"::error::Transfer failed: {error}")
        fail_body = (
            f"**RTC Reward Failed** ❌\n\n"
            f"Attempted to award **{amount} RTC** to `{wallet}` "
            f"but the transfer was rejected:\n\n"
            f"```\n{error}\n```\n\n"
            f"Please process this reward manually.\n\n"
            f"<!-- {ALREADY_PAID_MARKER}:FAILED -->"
        )
        post_comment(repo, pr_number, fail_body)
        sys.exit(1)

    # Success!
    dry_run_badge = " 🧪 (DRY RUN)" if dry_run else ""
    confirm_body = (
        f"**RTC Reward Sent** ✅{dry_run_badge}\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| Amount | **{amount} RTC** |\n"
        f"| Recipient | `{wallet}` |\n"
        f"| From | `{wallet_from}` |\n"
        f"| Memo | {memo} |\n"
        f"| pending_id | `{pending_id}` |\n\n"
        f"Transfer confirmed on RustChain.\n\n"
        f"<!-- {ALREADY_PAID_MARKER} pending_id={pending_id} -->"
    )
    post_comment(repo, pr_number, confirm_body)

    print(f"✅ Payment complete: {amount} RTC to {wallet} (pending_id={pending_id})")

if __name__ == "__main__":
    main()
