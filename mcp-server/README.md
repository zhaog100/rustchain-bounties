# RustChain MCP Server

Model Context Protocol server for RustChain. Connects any AI agent to RustChain operations.

## Installation

```bash
npm install
npm run build
```

## Usage with Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "rustchain": {
      "command": "node",
      "args": ["/path/to/rustchain-mcp/dist/index.js"],
      "env": {
        "RUSTCHAIN_API_KEY": "your-key"
      }
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `rustchain_health` | Check node health |
| `rustchain_balance` | Get wallet balance |
| `rustchain_bounties` | List open bounties |
| `rustchain_miner_status` | Check miner status |
| `rustchain_transactions` | Get recent transactions |

## Environment Variables

- `RUSTCHAIN_API_URL` — API base URL (default: https://api.rustchain.io/v1)
- `RUSTCHAIN_API_KEY` — Optional API key
