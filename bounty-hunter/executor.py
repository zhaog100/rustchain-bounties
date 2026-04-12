#!/usr/bin/env python3
"""Code Executor - Implementation automation"""

import os
import subprocess
from typing import Dict, List


class CodeExecutor:
    def __init__(self, config: dict):
        self.workspace = config.get('workspace', '/tmp/bounty-work')
        os.makedirs(self.workspace, exist_ok=True)
        
    async def implement(self, bounty: Dict) -> List[str]:
        """Implement the solution for a bounty"""
        changes = []
        
        bounty_type = self._detect_bounty_type(bounty)
        
        if bounty_type == 'mcp_server':
            changes = await self._implement_mcp_server(bounty)
        elif bounty_type == 'agent':
            changes = await self._implement_agent(bounty)
        elif bounty_type == 'telegram_bot':
            changes = await self._implement_telegram_bot(bounty)
        else:
            changes = await self._implement_generic(bounty)
        
        return changes
    
    def _detect_bounty_type(self, bounty: Dict) -> str:
        """Detect what type of implementation is needed"""
        title = (bounty['title'] or '').lower()
        body = (bounty['body'] or '').lower()
        
        if 'mcp' in title or 'mcp' in body:
            return 'mcp_server'
        elif 'agent' in title or 'autonomous' in body:
            return 'agent'
        elif 'telegram' in title or 'telegram' in body:
            return 'telegram_bot'
        else:
            return 'generic'
    
    async def _implement_mcp_server(self, bounty: Dict) -> List[str]:
        """Implement MCP Server"""
        print("   Implementing MCP Server...")
        return ['mcp_server.py', 'requirements.txt']
    
    async def _implement_agent(self, bounty: Dict) -> List[str]:
        """Implement Autonomous Agent"""
        print("   Implementing Autonomous Agent...")
        return ['agent.py', 'main.py', 'requirements.txt']
    
    async def _implement_telegram_bot(self, bounty: Dict) -> List[str]:
        """Implement Telegram Bot"""
        print("   Implementing Telegram Bot...")
        return ['bot.py', 'requirements.txt']
    
    async def _implement_generic(self, bounty: Dict) -> List[str]:
        """Generic implementation"""
        print("   Implementing generic solution...")
        return ['solution.py']
    
    async def run_tests(self, files: List[str]) -> bool:
        """Run tests on modified files"""
        result = subprocess.run(['python', '-m', 'pytest'], capture_output=True)
        return result.returncode == 0
