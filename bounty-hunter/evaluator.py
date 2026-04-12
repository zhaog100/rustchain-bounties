#!/usr/bin/env python3
"""Bounty Evaluator - AI-powered task evaluation"""

import os
import anthropic
from typing import Dict


class BountyEvaluator:
    def __init__(self, config: dict):
        self.client = anthropic.Anthropic(api_key=config['claude_api_key'])
        self.skills = ['python', 'javascript', 'web', 'api', 'ai', 'data']
        
    async def evaluate(self, bounty: Dict) -> float:
        """Evaluate if we can complete this bounty"""
        prompt = f"""Evaluate this RustChain bounty for our AI agent team:

Title: {bounty['title']}
Description: {bounty['body'][:1000] if bounty['body'] else ''}
Labels: {bounty['labels']}

Rate from 1-10 how suitable this is for us. Consider:
- Technical complexity
- Skill match with Python/JS
- Time estimate
- Payment vs effort

Respond with just the score (1-10)."""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-5c20240514",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )
            score_text = response.content[0].text.strip()
            score = float(score_text) if score_text.replace('.', '').isdigit() else 5.0
            return min(10, max(1, score))
        except Exception as e:
            print(f"   Evaluation error: {e}")
            return 5.0
    
    async def can_complete(self, bounty: Dict) -> tuple:
        """Detailed evaluation"""
        score = await self.evaluate(bounty)
        
        body_lower = (bounty['body'] or '').lower()
        skill_matches = sum(1 for skill in self.skills if skill in body_lower)
        
        return score > 5, skill_matches, score
