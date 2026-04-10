"""AI-powered bounty evaluation and scoring."""

import re
import logging

log = logging.getLogger("evaluator")

RTC_TO_USD = 0.10


class Evaluator:
    def __init__(self, cfg):
        self.cfg = cfg

    def _extract_amount(self, issue: dict) -> float:
        """Extract RTC amount from title/body."""
        text = f"{issue.get('title', '')} {issue.get('body', '')}"
        # Match patterns like "50 RTC", "100 RTC", "$200"
        rtc_match = re.search(r'(\d+)\s*RTC', text, re.IGNORECASE)
        if rtc_match:
            return float(rtc_match.group(1))
        usd_match = re.search(r'\$(\d+)', text)
        if usd_match:
            return float(usd_match.group(1)) / RTC_TO_USD
        return 0

    def _estimate_complexity(self, issue: dict) -> str:
        """Estimate task complexity from description."""
        text = f"{issue.get('title', '')} {issue.get('body', '')}".lower()
        if any(w in text for w in ["simple", "quick", "article", "write", "document"]):
            return "easy"
        if any(w in text for w in ["build", "create", "implement", "bot", "extension"]):
            return "medium"
        if any(w in text for w in ["autonomous", "agent", "framework", "integration"]):
            return "hard"
        return "medium"

    def evaluate(self, issue: dict) -> dict:
        """Score a bounty issue (0-100)."""
        amount = self._extract_amount(issue)
        complexity = self._estimate_complexity(issue)

        # Amount score (40%)
        amount_score = min(amount / 100 * 40, 40)

        # Complexity score (30%) — prefer medium
        complexity_scores = {"easy": 25, "medium": 30, "hard": 15}
        complexity_score = complexity_scores.get(complexity, 20)

        # Competition score (20%) — unknown from issue data
        competition_score = 10  # neutral

        # Time score (10%) — estimate from complexity
        time_scores = {"easy": 10, "medium": 7, "hard": 3}
        time_score = time_scores.get(complexity, 5)

        total = amount_score + complexity_score + competition_score + time_score

        verdict = "SKIP" if total < self.cfg.min_score else "CLAIM"

        return {
            "total": round(total, 1),
            "amount": amount,
            "amount_score": round(amount_score, 1),
            "complexity": complexity,
            "complexity_score": complexity_score,
            "competition_score": competition_score,
            "time_score": time_score,
            "verdict": verdict,
        }
