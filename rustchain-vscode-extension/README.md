# RustChain Dashboard for VS Code

🌾 **RustChain wallet balance, miner status, and bounty board in your editor sidebar**

[![Version](https://img.shields.io/vscode-marketplace/v/rustchain-dashboard.svg)](https://marketplace.visualstudio.com/items?itemName=rustchain.rustchain-dashboard)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- 💰 **Wallet Balance** — Real-time RTC balance in status bar
- ⛏️ **Miner Status** — See active miners at a glance
- 🎁 **Bounty Browser** — Browse open bounties without leaving your editor
- ⏱️ **Epoch Timer** — Countdown to next epoch settlement
- 🔄 **Auto-Refresh** — Configurable refresh interval (default: 60s)

## 📦 Installation

### From VSIX (Development)

```bash
# Clone and install dependencies
git clone https://github.com/Scottcjn/rustchain-bounties
cd rustchain-bounties/rustchain-vscode
npm install

# Build extension
npm run compile

# Package
vsce package

# Install in VS Code
code --install-extension rustchain-dashboard-1.0.0.vsix
```

### From Marketplace (Coming Soon)

```bash
# Install from VS Code Marketplace
# Search for "RustChain Dashboard"
```

## 🚀 Usage

1. **Open VS Code** (or Cursor/Windsurf)
2. **Click RustChain icon** in activity bar (left sidebar)
3. **Set your wallet name**:
   - Click "💰 Set Wallet" in status bar
   - Or open settings: `rustchain.walletName`
4. **View your balance** — Auto-refreshes every 60 seconds

### Commands

| Command | Description |
|---------|-------------|
| `RustChain: Refresh Data` | Manually refresh all data |
| `RustChain: Set Wallet Name` | Configure your wallet |
| `RustChain: Claim Bounty` | Open bounty board |

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `rustchain.nodeUrl` | `https://50.28.86.131:8099` | RustChain node URL |
| `rustchain.walletName` | `""` | Your wallet name |
| `rustchain.refreshInterval` | `60` | Auto-refresh interval (seconds) |

## 📸 Screenshots

### Sidebar Views
- **Wallet Balance**: Shows RTC balance + USD value
- **Miner Status**: Green/red indicators for online/offline miners
- **Open Bounties**: Clickable list of current bounties
- **Epoch Timer**: Current epoch + countdown

### Status Bar
- Click to set wallet
- Shows balance when configured
- Tooltip with detailed info

## 🔧 Development

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch mode
npm run watch

# Lint
npm run lint

# Package for distribution
vsce package
```

## 📁 Project Structure

```
rustchain-vscode/
├── src/
│   └── extension.ts      # Main extension logic
├── resources/
│   └── icon.svg          # Extension icon
├── package.json          # Extension manifest
├── tsconfig.json         # TypeScript config
├── .vscodeignore         # Files to exclude from package
└── README.md             # This file
```

## 🌐 Compatibility

- ✅ **VS Code** (v1.85.0+)
- ✅ **Cursor** (VS Code fork)
- ✅ **Windsurf** (VS Code fork)
- ✅ **Code OSS** (open source build)

## 🐛 Known Issues

- Miner list limited to first 5 miners (performance)
- Bounty list is static (will integrate with GitHub API in v1.1)
- Epoch timer shows end time only if available from node

## 📝 Changelog

### v1.0.0 (2026-04-14)
- Initial release
- Wallet balance display
- Miner status indicators
- Bounty browser
- Epoch timer
- Auto-refresh
- Configurable settings

## 🤝 Contributing

Contributions welcome! To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a PR to `Scottcjn/rustchain-bounties`

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

## 🔗 Links

- **RustChain**: https://rustchain.org
- **GitHub**: https://github.com/Scottcjn/Rustchain
- **Elyan Labs**: https://elyanlabs.ai
- **Report Issues**: https://github.com/Scottcjn/rustchain-bounties/issues

---

**Made with ❤️ for the RustChain community**
