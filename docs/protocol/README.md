# RustChain Protocol Documentation

## Overview

RustChain is a Proof-of-Antiquity (PoA) blockchain that rewards miners for proving they operate real hardware over time. The protocol uses hardware fingerprinting, attestation epochs, and a UTXO-based transaction model.

## Core Concepts

### 1. Proof-of-Antiquity (RIP-PoA)

Unlike Proof-of-Work or Proof-of-Stake, RIP-PoA proves that:
- A real physical device has been continuously online
- The device passes hardware fingerprint checks
- The attestation was submitted within the correct epoch

**Attestation Flow:**
```
Health Check → Hardware Detection → Fingerprint Checks → Challenge → Submit → Enroll → Balance Check → Sleep
```

### 2. Epoch System

- **Epoch Duration**: 10 minutes (600 seconds)
- Miners must submit one attestation per epoch
- Missed epochs reduce mining rewards
- Epochs are numbered sequentially from genesis

### 3. Hardware Fingerprinting

The miner performs 6 fingerprint checks:

| Check | Purpose |
|-------|---------|
| Anti-Emulation | Detect VMs/hypervisors |
| Cache Timing | Verify physical CPU cache behavior |
| Clock Drift | Measure hardware clock stability |
| Instruction Jitter | Detect emulation through timing |
| SIMD Identity | Verify genuine CPU instruction sets |
| Thermal Drift | Check real thermal variation patterns |

### 4. UTXO Model

RustChain uses a UTXO (Unspent Transaction Output) model:
- Each transaction consumes inputs and creates outputs
- Double-spend prevention through consensus
- UTXO database tracks all unspent outputs

### 5. Miner Enrollment

New miners must:
1. Generate a keypair
2. Submit hardware attestation
3. Receive miner ID from the network
4. Begin regular attestation cycle

### 6. Reward Distribution

- Miners earn RTC for each valid attestation
- Rewards accumulate in the epoch pot
- Distribution proportional to uptime
- Bonus rewards for longest streaks

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Node health check |
| `/epoch` | GET | Current epoch info |
| `/attest/challenge` | GET | Get attestation challenge |
| `/attest/submit` | POST | Submit attestation |
| `/enroll` | POST | Enroll new miner |
| `/balance/{address}` | GET | Wallet balance |
| `/miner/{address}/status` | GET | Miner status |
| `/bounties` | GET | Open bounties |

## Network Architecture

```
Miner ←→ Node ←→ API Gateway ←→ Users/Bots/SDKs
                ↕
           UTXO Database
```

### Node Configuration
- Default URL: `https://50.28.86.131`
- Self-signed TLS (miner accepts invalid certs)
- RESTful API over HTTPS

## Token Economics

- **RTC (RustChain Token)**: Native currency
- **Earning**: Mining attestation + bounty completion
- **Bounty Rewards**: 1-200 RTC per task
- **Approximate Value**: ~$0.10 USD per RTC

## SDKs and Tools

- **Rust Miner**: Native miner with full fingerprinting
- **Python SDK**: API client for developers
- **VS Code Extension**: Dashboard for miners
- **Telegram Bot**: Mobile monitoring
- **MCP Server**: AI agent integration

## Security Model

- Hardware fingerprints prevent Sybil attacks
- Epoch timing prevents replay attacks
- UTXO model prevents double-spending
- Nonce-based challenge-response for attestation

## Glossary

| Term | Definition |
|------|-----------|
| RIP | RustChain Improvement Proposal |
| PoA | Proof-of-Antiquity |
| Epoch | 10-minute attestation window |
| Attestation | Proof of continuous hardware presence |
| UTXO | Unspent Transaction Output |
| RTC | RustChain Token |

---

*Last updated: 2026-04-09*
