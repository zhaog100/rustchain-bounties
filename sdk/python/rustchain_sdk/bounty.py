"""
RIP-302 Agent Economy Bounty API
Provides high-level bounty listing, claiming, and submission for the RustChain ecosystem.
"""

from typing import List, Optional, Dict, Any

from .client import RustChainClient
from .models import Bounty


class BountyAPI:
    """
    High-level API for RustChain bounty operations.

    Args:
        client: A RustChainClient instance.

    Example:
        import asyncio
        from rustchain_sdk import RustChainClient
        from rustchain_sdk.bounty import BountyAPI

        async def main():
            client = RustChainClient()
            bounty_api = BountyAPI(client)
            bounties = await bounty_api.list_bounties(status="open")
            for b in bounties:
                print(f"#{b.id}: {b.title} ({b.reward})")
    """

    BOUNTY_REPO = "Scottcjn/rustchain-bounties"

    def __init__(self, client: RustChainClient):
        self._client = client

    async def list_bounties(
        self,
        status: str = "open",
        difficulty: Optional[str] = None,
        limit: int = 50,
    ) -> List[Bounty]:
        """
        List bounties from the RustChain ecosystem.

        Args:
            status: Filter by status ("open", "closed", "all").
            difficulty: Optional difficulty filter ("beginner", "standard", "major", "critical").
            limit: Maximum number of bounties to return.

        Returns:
            List of Bounty objects.
        """
        params: Dict[str, Any] = {"limit": limit}
        if status and status != "all":
            params["status"] = status
        if difficulty:
            params["difficulty"] = difficulty

        result = await self._client._get("/bounties", params=params)
        items = result if isinstance(result, list) else result.get("bounties", [])
        return [Bounty.from_dict(b) for b in items[:limit]]

    async def get_bounty(self, bounty_id: int) -> Bounty:
        """
        Get details for a specific bounty.

        Args:
            bounty_id: The bounty issue number.

        Returns:
            Bounty object.
        """
        result = await self._client._get(f"/bounties/{bounty_id}")
        return Bounty.from_dict(result)

    async def claim_bounty(
        self,
        bounty_id: int,
        wallet_address: str,
        signature: str,
    ) -> Dict[str, Any]:
        """
        Claim a bounty for the given wallet.

        Args:
            bounty_id: The bounty issue number.
            wallet_address: Claimer's wallet address.
            signature: Signed claim message.

        Returns:
            Claim result dict.
        """
        return await self._client._post(
            "/bounties/claim",
            json_data={
                "bounty_id": bounty_id,
                "wallet_address": wallet_address,
                "signature": signature,
            },
        )

    async def submit_bounty(
        self,
        bounty_id: int,
        wallet_address: str,
        pr_url: str,
        evidence: str = "",
        signature: str = "",
    ) -> Dict[str, Any]:
        """
        Submit completed bounty work.

        Args:
            bounty_id: The bounty issue number.
            wallet_address: Submitter's wallet address.
            pr_url: URL to the pull request or proof of work.
            evidence: Additional evidence or notes.
            signature: Signed submission message.

        Returns:
            Submission result dict.
        """
        return await self._client._post(
            "/bounties/submit",
            json_data={
                "bounty_id": bounty_id,
                "wallet_address": wallet_address,
                "pr_url": pr_url,
                "evidence": evidence,
                "signature": signature,
            },
        )

    async def get_bounty_rewards(self, wallet_address: str) -> Dict[str, Any]:
        """
        Get bounty reward history for a wallet.

        Args:
            wallet_address: The wallet address.

        Returns:
            Dict with reward history.
        """
        return await self._client._get(
            "/bounties/rewards",
            params={"address": wallet_address},
        )

    async def get_leaderboard(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get the bounty leaderboard (top earners).

        Args:
            limit: Number of entries.

        Returns:
            List of leaderboard entries.
        """
        result = await self._client._get(
            "/bounties/leaderboard",
            params={"limit": limit},
        )
        return result if isinstance(result, list) else result.get("entries", [])
