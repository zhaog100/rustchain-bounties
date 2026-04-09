"""
RIP-302 Agent Economy Data Models
Typed dataclasses for RustChain blockchain entities.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Transaction:
    """Represents a RustChain transaction."""
    tx_hash: str
    from_address: str
    to_address: str
    amount: int
    fee: int = 0
    timestamp: int = 0
    signature: str = ""
    status: str = "pending"
    block_height: Optional[int] = None
    nonce: Optional[int] = None
    memo: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        return cls(
            tx_hash=data.get("tx_hash", data.get("hash", "")),
            from_address=data.get("from", ""),
            to_address=data.get("to", ""),
            amount=data.get("amount", 0),
            fee=data.get("fee", 0),
            timestamp=data.get("timestamp", 0),
            signature=data.get("signature", ""),
            status=data.get("status", "pending"),
            block_height=data.get("block_height"),
            nonce=data.get("nonce"),
            memo=data.get("memo", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_hash": self.tx_hash,
            "from": self.from_address,
            "to": self.to_address,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "status": self.status,
            "block_height": self.block_height,
            "nonce": self.nonce,
            "memo": self.memo,
        }


@dataclass
class Block:
    """Represents a RustChain block."""
    height: int
    hash: str
    previous_hash: str = ""
    timestamp: int = 0
    proposer: str = ""
    num_transactions: int = 0
    epoch: Optional[int] = None
    attestations: int = 0
    size_bytes: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        return cls(
            height=data.get("height", 0),
            hash=data.get("hash", ""),
            previous_hash=data.get("previous_hash", ""),
            timestamp=data.get("timestamp", 0),
            proposer=data.get("proposer", ""),
            num_transactions=data.get("num_transactions", 0),
            epoch=data.get("epoch"),
            attestations=data.get("attestations", 0),
            size_bytes=data.get("size_bytes", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "hash": self.hash,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "proposer": self.proposer,
            "num_transactions": self.num_transactions,
            "epoch": self.epoch,
            "attestations": self.attestations,
            "size_bytes": self.size_bytes,
        }


@dataclass
class Wallet:
    """Represents a RustChain wallet."""
    address: str
    balance: int = 0
    nonce: int = 0
    public_key: str = ""
    label: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Wallet":
        return cls(
            address=data.get("address", ""),
            balance=data.get("balance", 0),
            nonce=data.get("nonce", 0),
            public_key=data.get("public_key", ""),
            label=data.get("label", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "balance": self.balance,
            "nonce": self.nonce,
            "public_key": self.public_key,
            "label": self.label,
        }


@dataclass
class Bounty:
    """Represents a RustChain bounty (RIP-302 Agent Economy)."""
    id: int
    title: str
    reward: str
    status: str = "open"
    difficulty: str = "standard"
    labels: List[str] = field(default_factory=list)
    assignee: Optional[str] = None
    description: str = ""
    created_at: Optional[str] = None
    url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bounty":
        return cls(
            id=data.get("id", data.get("number", 0)),
            title=data.get("title", ""),
            reward=data.get("reward", ""),
            status=data.get("status", "open"),
            difficulty=data.get("difficulty", "standard"),
            labels=data.get("labels", []),
            assignee=data.get("assignee"),
            description=data.get("description", data.get("body", "")),
            created_at=data.get("created_at"),
            url=data.get("url", data.get("html_url", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "reward": self.reward,
            "status": self.status,
            "difficulty": self.difficulty,
            "labels": self.labels,
            "assignee": self.assignee,
            "description": self.description,
            "created_at": self.created_at,
            "url": self.url,
        }


@dataclass
class MinerInfo:
    """Represents a RustChain miner."""
    id: str
    public_key: str = ""
    address: str = ""
    status: str = "active"
    hardware: str = ""
    power: float = 0.0
    epoch: Optional[int] = None
    attested: bool = False
    bounty_multiplier: float = 1.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MinerInfo":
        return cls(
            id=data.get("id", data.get("miner_id", "")),
            public_key=data.get("public_key", ""),
            address=data.get("address", ""),
            status=data.get("status", "active"),
            hardware=data.get("hardware", ""),
            power=data.get("power", 0.0),
            epoch=data.get("epoch"),
            attested=data.get("attested", False),
            bounty_multiplier=data.get("bounty_multiplier", 1.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "public_key": self.public_key,
            "address": self.address,
            "status": self.status,
            "hardware": self.hardware,
            "power": self.power,
            "epoch": self.epoch,
            "attested": self.attested,
            "bounty_multiplier": self.bounty_multiplier,
        }


@dataclass
class Epoch:
    """Represents a RustChain epoch."""
    number: int
    start_time: int = 0
    end_time: Optional[int] = None
    total_miners: int = 0
    total_bounties: int = 0
    rewards_distributed: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Epoch":
        return cls(
            number=data.get("number", data.get("epoch_number", 0)),
            start_time=data.get("start_time", 0),
            end_time=data.get("end_time"),
            total_miners=data.get("total_miners", 0),
            total_bounties=data.get("total_bounties", 0),
            rewards_distributed=data.get("rewards_distributed", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_miners": self.total_miners,
            "total_bounties": self.total_bounties,
            "rewards_distributed": self.rewards_distributed,
        }
