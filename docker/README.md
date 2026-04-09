# RustChain Docker Setup

One command to run RustChain miner:

\`\`\`bash
# Clone and run
git clone https://github.com/Scottcjn/rustchain-bounties.git
cd rustchain-bounties/docker

# Set your wallet and start
RUSTCHAIN_WALLET=your_address docker compose up -d

# Check logs
docker compose logs -f

# Stop
docker compose down
\`\`\`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| RUSTCHAIN_WALLET | (required) | Your wallet address |
| RUSTCHAIN_NODE_URL | https://api.rustchain.io | Node API URL |
| RUSTCHAIN_MINER_THREADS | 1 | Mining threads |
| RUSTCHAIN_LOG_LEVEL | info | Log level |

## Quick Test

\`\`\`bash
docker build -t rustchain-miner -f docker/Dockerfile .
docker run --rm -e RUSTCHAIN_WALLET=test rustchain-miner
\`\`\`
