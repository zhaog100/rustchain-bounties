# 🏆 RTC Reward Action

A GitHub Action that automatically awards RTC tokens to contributors when their PR is merged.

## Usage

Add this to your `.github/workflows/rtc-reward.yml`:

```yaml
name: RTC Reward
on:
  pull_request:
    types: [closed]

jobs:
  reward:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: Scottcjn/rtc-reward-action@v1
        with:
          node-url: https://50.28.86.131
          amount: 5
          wallet-from: project-fund
          admin-key: ${{ secrets.RTC_ADMIN_KEY }}
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `node-url` | RustChain node URL | No | `https://50.28.86.131` |
| `amount` | RTC to award per merge | No | `5` |
| `wallet-from` | Source wallet name | No | `project-fund` |
| `admin-key` | Admin key for signing | Yes | - |
| `dry-run` | Test mode (no transfer) | No | `false` |
| `github-token` | GitHub token for comments | No | `${{ github.token }}` |

## How It Works

1. **Trigger**: Runs when a PR is closed
2. **Check**: Verifies the PR was actually merged
3. **Extract Wallet**: Looks for contributor's RTC wallet in:
   - PR body (pattern: `rtc-wallet: <name>`)
   - `.rtc-wallet` file in repository root
   - Falls back to GitHub username
4. **Transfer**: Sends RTC via RustChain node API
5. **Comment**: Posts a confirmation comment on the PR

## Dry Run Mode

Test your configuration without sending real tokens:

```yaml
with:
  dry-run: true
```

## Security

- Store `admin-key` in GitHub Secrets, never in workflow files
- The action only runs on merged PRs (not on closed-unmerged)
- All transfers are logged to the RustChain blockchain

## License

MIT
