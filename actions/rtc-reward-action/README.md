# 🏆 RTC Reward Action

A GitHub Action that automatically awards **RTC tokens** to contributors when their pull request is merged.

Turn **any GitHub repository** into a bounty platform. Maintainers add one YAML file, contributors earn crypto for merged PRs — zero setup beyond the action.

## Features

- ✅ **Auto-detect merged PRs** — triggers on `pull_request.closed` events
- ✅ **Flexible wallet extraction** — reads from PR body, `.rtc-wallet` file, or PR comments
- ✅ **Dry-run mode** — test without sending real transactions
- ✅ **Retry logic** — exponential backoff for network failures (3 attempts)
- ✅ **Template comments** — customizable success/dry-run/skip messages
- ✅ **Zero Docker overhead** — pure Node.js action, fast cold start (< 5s)
- ✅ **No external dependencies at runtime** — uses native `https` module

## Quick Start

### 1. Add to your workflow

```yaml
# .github/workflows/rtc-reward.yml
name: RTC Reward
on:
  pull_request:
    types: [closed]

jobs:
  reward:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: zhaog100/rtc-reward-action@v1
        with:
          node-url: https://50.28.86.131
          amount: 5
          wallet-from: ${{ secrets.RTC_TREASURY_WALLET }}
          admin-key: ${{ secrets.RTC_ADMIN_KEY }}
          dry-run: false # set true for testing
```

### 2. Set repository secrets

| Secret | Description |
|--------|-------------|
| `RTC_TREASURY_WALLET` | Project wallet that sends rewards |
| `RTC_ADMIN_KEY` | Admin private key for signing |

### 3. Contributors add their wallet

Contributors include their wallet in the PR body:

```markdown
## My Changes
...

wallet: RTC00a1347cc03c2aea1d6b35df16178fad4e9d6712
```

Or create a `.rtc-wallet` file in the repo root containing just the address.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `node-url` | No | `https://50.28.86.131` | RustChain node URL |
| `amount` | No | `5` | RTC to award per merge |
| `wallet-from` | **Yes** | — | Treasury wallet address |
| `admin-key` | **Yes** | — | Admin private key |
| `dry-run` | No | `false` | Simulate without sending |
| `github-token` | No | `${{ github.token }}` | Token for PR comments |
| `pr-body-pattern` | No | auto | Custom regex for wallet extraction |
| `comment-on-success` | No | template | Success comment template |
| `comment-on-dryrun` | No | template | Dry-run comment template |
| `comment-on-skip` | No | template | Skip (no wallet) comment |

## Outputs

| Output | Description |
|--------|-------------|
| `transaction-hash` | The tx hash of the reward transfer |
| `wallet` | Contributor's wallet address |
| `amount` | Amount of RTC awarded |
| `pr-number` | PR number that triggered the action |
| `skipped` | `true` if no wallet was found |
| `dry-run` | `true` if dry-run mode was active |

## Wallet Extraction

The action searches for the contributor's wallet in this order:

1. **PR body** — matches patterns like `wallet: RTC...`, `RTC00...`, code blocks
2. **`.rtc-wallet` file** — reads from the PR's head commit
3. **PR comments** — scans comments for wallet addresses

Supported wallet formats:
- `wallet: RTC00a1347cc03c2aea1d6b35df16178fad4e9d6712`
- `Wallet: RTC00a1347cc03c2aea1d6b35df16178fad4e9d6712`
- ``` `RTC00a1347cc03c2aea1d6b35df16178fad4e9d6712` ```
- YAML: `wallet: RTC00...`

## License

MIT

## Bounty

This action was created for [RustChain Bounty #2864](https://github.com/Scottcjn/rustchain-bounties/issues/2864) — *Create a GitHub Action That Awards RTC for Merged Pull Requests* (20 RTC).

**Author wallet:** (provide your wallet here)
