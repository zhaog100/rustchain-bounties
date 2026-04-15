# RustChain Telegram Bot (@RustChainBot)

🤖 Telegram bot for checking RustChain wallet balances and miner status.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- 💰 **Balance Check** — Check RTC balance for any wallet
- ⛏️ **Miner List** — View active miners
- 📊 **Epoch Info** — Current epoch details
- 💹 **Price Check** — RTC reference rate ($0.10)
- 🛡️ **Rate Limiting** — 1 request per 5 seconds per user
- ⚠️ **Error Handling** — Graceful handling of offline node

## 🚀 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/balance <wallet>` | Check RTC balance | `/balance my-wallet` |
| `/miners` | List active miners | `/miners` |
| `/epoch` | Current epoch info | `/epoch` |
| `/price` | Show RTC reference rate | `/price` |
| `/help` | Show commands | `/help` |
| `/start` | Welcome message | `/start` |

## 📦 Deployment

### Option 1: Docker (Recommended)

```bash
# Build image
docker build -t rustchain-bot .

# Run with environment variables
docker run -d \
  -e TELEGRAM_BOT_TOKEN=your-bot-token \
  -e RUSTCHAIN_NODE=https://50.28.86.131:8099 \
  --name rustchain-bot \
  rustchain-bot
```

### Option 2: Direct Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
export TELEGRAM_BOT_TOKEN=your-bot-token
export RUSTCHAIN_NODE=https://50.28.86.131:8099
python bot.py
```

### Option 3: Railway / Fly.io

1. Create account on [Railway](https://railway.app) or [Fly.io](https://fly.io)
2. Connect your GitHub repo
3. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `RUSTCHAIN_NODE`
4. Deploy!

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `RUSTCHAIN_NODE` | ❌ | `https://50.28.86.131:8099` | RustChain node URL |

## 🤖 Create Your Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions to name your bot
4. Copy the API token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Add to your deployment as `TELEGRAM_BOT_TOKEN`

## 📝 Example Output

### /balance
```
💰 Balance for `my-wallet`

123.4567 RTC

≈ $12.35 USD (at $0.10/RTC)
```

### /miners
```
⛏️ Active Miners

1. `miner-alpha` — online
2. `miner-beta` — online
3. `miner-gamma` — syncing

... and 7 more
```

### /epoch
```
📊 Epoch Info

Epoch: 42
Started: 2026-04-14T00:00:00Z
Ends: 2026-04-15T00:00:00Z
```

### /price
```
💹 RTC Reference Rate

1 RTC = $0.10 USD

Updated: 2026-04-14T17:30:00Z
```

## 🛡️ Rate Limiting

To prevent abuse, each user is limited to **1 request per 5 seconds**. If you exceed this limit:

```
⏳ Please wait 5 seconds between requests.
```

## 🐛 Error Handling

The bot gracefully handles:
- ❌ Node offline → "Node offline"
- ❌ HTTP errors → "HTTP 404"
- ❌ Timeouts → "Timeout"
- ❌ Invalid wallet names → Validation error

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

## 🤝 Contributing

Contributions welcome! To test locally:

```bash
# Run with test token
TELEGRAM_BOT_TOKEN=123456:ABCdef... python bot.py
```

## 📞 Support

- **Issues**: https://github.com/Scottcjn/rustchain-bounties/issues
- **RustChain Docs**: https://github.com/Scottcjn/rustchain-bounties
- **Discord**: [Join RustChain Discord](https://discord.gg/rustchain)

---

**Made with ❤️ for the RustChain community**
