# RTC Reward GitHub Action

Award RTC tokens to contributors when PRs are merged or issues are completed.

## Usage

```yaml
name: Reward Bounty
on:
  pull_request:
    types: [closed]

jobs:
  reward:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: rustchain/rtc-reward@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          rtc-amount: 25
          rpc-url: https://api.rustchain.io/v1
```

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| github-token | ✅ | GitHub token |
| rtc-amount | ✅ | RTC to award |
| wallet-address | ❌ | Recipient (auto-detected) |
| rpc-url | ❌ | RustChain API URL |
| reason | ❌ | Reward reason |
