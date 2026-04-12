#!/usr/bin/env python3
"""
RustChain Bounty Hunter Agent
Automatically find, evaluate, and claim RustChain bounties.
"""

import os
import argparse
import asyncio
from datetime import datetime

from scanner import BountyScanner
from evaluator import BountyEvaluator
from executor import CodeExecutor
from submitter import PRSubmitter
from tracker import EarningsTracker


class BountyHunterAgent:
    def __init__(self, config: dict):
        self.config = config
        self.scanner = BountyScanner(config)
        self.evaluator = BountyEvaluator(config)
        self.executor = CodeExecutor(config)
        self.submitter = PRSubmitter(config)
        self.tracker = EarningsTracker(config)
        
    async def run(self, bounty_id: int = None):
        """Main agent loop"""
        print(f"🤖 Starting Bounty Hunter Agent - {datetime.now()}")
        
        # Step 1: Scan bounties
        print("\n📋 Step 1: Scanning for open bounties...")
        bounties = await self.scanner.scan_bounties()
        print(f"   Found {len(bounties)} open bounties")
        
        # Step 2: Evaluate bounties
        print("\n🧠 Step 2: Evaluating bounties...")
        for bounty in bounties:
            score = await self.evaluator.evaluate(bounty)
            bounty['score'] = score
            print(f"   {bounty['title'][:50]}... - Score: {score}/10")
        
        # Step 3: Select best bounty
        print("\n🎯 Step 3: Selecting best bounty...")
        best = max(bounties, key=lambda x: x['score'])
        print(f"   Selected: {best['title']}")
        
        # Step 4: Fork repo
        print("\n🍴 Step 4: Forking repository...")
        fork_url = await self.scanner.fork_repo(best)
        print(f"   Forked to: {fork_url}")
        
        # Step 5: Implement solution
        print("\n💻 Step 5: Implementing solution...")
        changes = await self.executor.implement(best)
        print(f"   Made {len(changes)} code changes")
        
        # Step 6: Submit PR
        print("\n📤 Step 6: Submitting PR...")
        pr_url = await self.submitter.submit(best, changes)
        print(f"   PR submitted: {pr_url}")
        
        # Step 7: Track earnings
        print("\n💰 Step 7: Tracking earnings...")
        await self.tracker.record_submission(best, pr_url)
        
        print("\n✅ Bounty submission complete!")
        return pr_url


def main():
    parser = argparse.ArgumentParser(description='RustChain Bounty Hunter')
    parser.add_argument('--bounty-id', type=int, help='Specific bounty ID to claim')
    parser.add_argument('--config', type=str, default='.env', help='Config file')
    args = parser.parse_args()
    
    # Load config
    config = {
        'github_token': os.getenv('GITHUB_TOKEN'),
        'claude_api_key': os.getenv('CLAUDE_API_KEY'),
        'wallet_address': os.getenv('WALLET_ADDRESS', '0x6FCBd5d14FB296933A4f5a515933B153bA24370E'),
        'repo_owner': 'Scottcjn',
        'repo_name': 'rustchain-bounties',
    }
    
    agent = BountyHunterAgent(config)
    asyncio.run(agent.run(args.bounty_id))


if __name__ == '__main__':
    main()
