# BCOS v2 GitHub Action

Reusable GitHub Action for [Beacon Certified Open Source](https://rustchain.org/bcos/) scans.

## Quick Start

```yaml
name: BCOS Scan
on:
  pull_request:
    types: [opened, synchronize, reopened, closed]

jobs:
  bcos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: zhaog100/bcos-action@v1
        with:
          tier: L1          # L0, L1, or L2
          reviewer: bcos-ci
          anchor-on-merge: true
          admin-key: ${{ secrets.RTC_ADMIN_KEY }}
```

## What It Does

1. **Scans** your repo with the BCOS v2 engine (trust score 0-100)
2. **Comments** on the PR with score badge + breakdown
3. **Anchors** attestation to RustChain on merge (optional)

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `tier` | `L1` | Required tier: L0/L1/L2 |
| `reviewer` | `bcos-ci` | Reviewer name |
| `node-url` | `https://50.28.86.131` | RustChain node |
| `anchor-on-merge` | `true` | Anchor on PR merge |
| `admin-key` | — | Key for anchoring |
| `fail-on-tier-miss` | `true` | Fail if tier not met |

## Outputs

`trust_score`, `cert_id`, `tier_met`, `tier_achieved`, `report`

## Bounty

Created for [RustChain Bounty #2291](https://github.com/Scottcjn/rustchain-bounties/issues/2291) — *BCOS v2: Reusable GitHub Action for any repo* (25 RTC).

**Wallet:** _(provide your RTC wallet)_
