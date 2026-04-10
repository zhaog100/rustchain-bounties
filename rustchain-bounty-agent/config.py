"""Configuration management."""

from dataclasses import dataclass


@dataclass
class Config:
    wallet: str = "zhaog100"
    min_score: float = 50.0
    poll_interval: int = 300
    target_repo: str = "Scottcjn/rustchain-bounties"
    node_url: str = "https://50.28.86.131"
    rate_limit_per_hour: int = 5000
    max_prs_per_day: int = 10
