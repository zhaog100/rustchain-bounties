#!/usr/bin/env python3
"""PR Submitter - Pull Request creation"""

import os
import subprocess
from typing import Dict, List


class PRSubmitter:
    def __init__(self, config: dict):
        self.workspace = config.get('workspace', '/tmp/bounty-work')
        self.wallet = config.get('wallet_address', '0x6FCBd5d14FB296933A4f5a515933B153bA24370E')
        
    async def submit(self, bounty: Dict, changes: List[str]) -> str:
        """Submit a pull request"""
        subprocess.run(['git', 'config', 'user.name', 'RustChain Bounty Hunter'])
        subprocess.run(['git', 'config', 'user.email', 'agent@rustchain.ai'])
        
        branch_name = f"bounty/{bounty['id']}-solution"
        subprocess.run(['git', 'checkout', '-b', branch_name], capture_output=True)
        subprocess.run(['git', 'add', '.'], capture_output=True)
        
        commit_msg = f"feat: solution for bounty #{bounty['id']}\n\n{bounty['title']}"
        subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True)
        subprocess.run(['git', 'push', '-u', 'origin', branch_name], capture_output=True)
        
        pr_body = f"""## Bounty Solution - #{bounty['id']}

### Description
Implemented solution for: {bounty['title']}

### Changes
- Added: {', '.join(changes)}

### RTC Wallet
{self.wallet}

---
Submitted by RustChain Bounty Hunter Agent
"""
        
        result = subprocess.run([
            'gh', 'pr', 'create',
            '--title', f"Bounty #{bounty['id']} Solution",
            '--body', pr_body,
            '--base', 'main'
        ], capture_output=True, text=True)
        
        return result.stdout.strip() if result.returncode == 0 else f"PR failed: {result.stderr}"
    
    async def add_bounty_comment(self, bounty_id: int, pr_url: str) -> bool:
        """Add bounty claim comment"""
        comment = f"""## Bounty Claimed! 🎉

Solution submitted via PR: {pr_url}

RTC Wallet: {self.wallet}

---
Submitted by RustChain Bounty Hunter Agent"""
        
        result = subprocess.run([
            'gh', 'issue', 'comment', str(bounty_id),
            '--body', comment
        ], capture_output=True)
        
        return result.returncode == 0
