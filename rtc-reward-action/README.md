# RTC Reward Action

[![GitHub Marketplace](https://img.shields.io/badge/marketplace-RTC%20Reward%20Action-blue?logo=github)](https://github.com/marketplace/actions/rtc-reward-action)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically award **RTC tokens** to contributors when their pull requests are merged. Turn any GitHub repository into a bounty platform!

## ✨ Features

- 🪙 **Automatic Crypto Rewards** — Pay contributors RTC tokens on PR merge
- 🔧 **Configurable Amount** — Set custom RTC amount per merge
- 💼 **Wallet Detection** — Reads wallet from PR body or `.rtc-wallet` file
- 🧪 **Dry-Run Mode** — Test without actual transfers
- 💬 **Auto Comments** — Posts payment confirmation on PR
- 🛡️ **Duplicate Prevention** — Never pay twice for the same PR
- 📦 **Easy Integration** — One YAML file, zero setup

## 🚀 Usage

### Basic Example

```yaml
# .github/workflows/rtc-reward.yml
name: RTC Rewards

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

### Advanced Configuration

```yaml
- uses: Scottcjn/rtc-reward-action@v1
  with:
    # RustChain node URL (IP or hostname)
    node-url: 'https://50.28.86.131'

    # RTC amount to award per merged PR
    amount: '10'

    # Source wallet for rewards
    wallet-from: 'community-fund'

    # Admin key for transfer API (store as secret!)
    admin-key: ${{ secrets.RTC_ADMIN_KEY }}

    # Dry-run mode (true/false) - no actual transfers
    dry-run: 'false'

    # Path to .rtc-wallet file in repo
    wallet-file: '.rtc-wallet'
```

## 📝 Contributor Wallet Setup

Contributors can specify their RTC wallet in two ways:

### Option 1: PR Body (Recommended)

In the PR description, add:

```markdown
## RTC Wallet

RTC Wallet: my-username

---

[rest of PR description]
```

### Option 2: `.rtc-wallet` File

Create a `.rtc-wallet` file in the repository root:

```
my-username
```

Or with explicit format:

```
RTC Wallet: my-username
```

If neither is provided, the action defaults to using the contributor's GitHub username.

## 🔐 Security

### Required Secrets

Add this to your GitHub repository secrets (`Settings → Secrets and variables → Actions`):

```
RTC_ADMIN_KEY=your-admin-key-here
```

### Safety Limits

- Maximum reward per PR: **10,000 RTC** (hardcoded limit)
- Duplicate payment protection: ✅ Enabled
- Dry-run mode available for testing: ✅

## 🧪 Testing

Before going live, test with dry-run mode:

```yaml
- uses: Scottcjn/rtc-reward-action@v1
  with:
    node-url: https://50.28.86.131
    amount: '5'
    wallet-from: project-fund
    admin-key: ${{ secrets.RTC_ADMIN_KEY }}
    dry-run: 'true'  # ← Enable dry-run
```

This will simulate the transfer without moving actual tokens.

## 📊 Example Output

When a PR is merged, the action posts a comment like:

```
**RTC Reward Sent** ✅

| Field | Value |
|-------|-------|
| Amount | **5 RTC** |
| Recipient | `contributor-username` |
| From | `project-fund` |
| Memo | PR #123 in owner/repo — RTC Reward |
| pending_id | `abc123xyz` |

Transfer confirmed on RustChain.
```

## 🏗️ Architecture

```
PR Merged
    ↓
GitHub Action Triggered
    ↓
Read Wallet (PR body or .rtc-wallet file)
    ↓
Call RustChain VPS /wallet/transfer API
    ↓
Post Confirmation Comment
    ↓
Done! ✅
```

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

## 🤝 Contributing

Contributions welcome! To test locally:

```bash
# Build and test the Docker image
docker build -t rtc-reward-action .

# Run with test environment variables
docker run -e GITHUB_TOKEN=... -e PR_NUMBER=... rtc-reward-action
```

## 📞 Support

- **Issues**: https://github.com/Scottcjn/rtc-reward-action/issues
- **RustChain Docs**: https://github.com/Scottcjn/rustchain-bounties
- **Discord**: [Join RustChain Discord](https://discord.gg/rustchain)

---

**Made with ❤️ for the RustChain community**
