#!/usr/bin/env python3
"""
RustChain Autonomous Bounty Hunter Agent
Entry point — scan, evaluate, develop, submit.

Bounty: #2861 (50 RTC)
Wallet: zhaog100
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
log = logging.getLogger("agent")

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from scanner import Scanner
from evaluator import Evaluator
from tracker import Tracker


def cmd_scan(cfg: Config, dry_run: bool = False):
    """Scan for open bounties and evaluate them."""
    scanner = Scanner(cfg)
    evaluator = Evaluator(cfg)
    tracker = Tracker(cfg)

    log.info("Scanning for RustChain bounties...")
    issues = scanner.scan_bounties()
    log.info("Found %d open bounties", len(issues))

    scored = []
    for issue in issues:
        score = evaluator.evaluate(issue)
        scored.append((issue, score))
        log.info("  #%d %s → score=%.1f (%s)", issue["number"], issue["title"][:50], score["total"], score["verdict"])

    scored.sort(key=lambda x: x[1]["total"], reverse=True)

    if dry_run:
        log.info("Dry run — top bounties:")
        for issue, score in scored[:10]:
            log.info("  #%-6d %5.1f pts | %-50s", issue["number"], score["total"], issue["title"][:50])
        return

    # Auto-pick top bounty
    if scored and scored[0][1]["total"] >= cfg.min_score:
        issue, score = scored[0]
        log.info("Auto-picking #%d (%.1f pts): %s", issue["number"], score["total"], issue["title"])
        tracker.add_task(issue, score)
    else:
        log.info("No bounties above threshold (%.1f)", cfg.min_score)


def cmd_auto(cfg: Config):
    """Full autonomous pipeline: scan → evaluate → develop → submit."""
    tracker = Tracker(cfg)

    while True:
        try:
            cmd_scan(cfg, dry_run=False)
            tasks = tracker.get_pending_tasks()
            if not tasks:
                log.info("No tasks to work on, waiting...")
                time.sleep(cfg.poll_interval)
                continue

            task = tasks[0]
            log.info("Working on task #%d: %s", task["issue_number"], task["title"])

            # In a full implementation, this would:
            # 1. Fork the target repo
            # 2. Create a feature branch
            # 3. Generate code using LLM
            # 4. Run tests
            # 5. Submit PR if tests pass
            # For now, we log and track
            tracker.update_status(task["issue_number"], "in_progress")
            log.info("Task #%d marked as in_progress", task["issue_number"])

            time.sleep(cfg.poll_interval)

        except KeyboardInterrupt:
            log.info("Stopped by user")
            break
        except Exception as e:
            log.error("Error in auto loop: %s", e)
            time.sleep(60)


def cmd_stats(cfg: Config):
    """Show earnings statistics."""
    tracker = Tracker(cfg)
    stats = tracker.get_stats()
    print(f"\n📊 Bounty Hunter Stats")
    print(f"  Total tasks:   {stats['total']}")
    print(f"  Pending:       {stats['pending']}")
    print(f"  In progress:   {stats['in_progress']}")
    print(f"  Submitted PRs: {stats['submitted']}")
    print(f"  Merged:        {stats['merged']}")
    print(f"  Earnings:      {stats['earnings_rtc']:.1f} RTC (~${stats['earnings_usd']:.2f} USD)\n")


def main():
    parser = argparse.ArgumentParser(description="RustChain Autonomous Bounty Hunter")
    parser.add_argument("--scan", action="store_true", help="Scan for bounties")
    parser.add_argument("--auto", action="store_true", help="Full autonomous pipeline")
    parser.add_argument("--stats", action="store_true", help="Show earnings stats")
    parser.add_argument("--issue", type=int, help="Target specific issue number")
    parser.add_argument("--repo", default="Scottcjn/rustchain-bounties", help="Target repo")
    parser.add_argument("--dry-run", action="store_true", help="Preview without action")
    parser.add_argument("--min-score", type=float, default=50, help="Minimum score to claim")
    parser.add_argument("--poll-interval", type=int, default=300, help="Seconds between scans")
    args = parser.parse_args()

    cfg = Config(
        wallet=os.environ.get("RTC_WALLET", "zhaog100"),
        min_score=args.min_score,
        poll_interval=args.poll_interval,
        target_repo=args.repo,
    )

    if args.scan:
        cmd_scan(cfg, dry_run=args.dry_run)
    elif args.auto:
        cmd_auto(cfg)
    elif args.stats:
        cmd_stats(cfg)
    elif args.issue:
        log.info("Targeting issue #%d in %s", args.issue, args.repo)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
