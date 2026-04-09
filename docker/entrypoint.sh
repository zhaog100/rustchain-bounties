#!/bin/bash
set -e

echo "🦀 RustChain Miner Starting..."
echo "Wallet: ${RUSTCHAIN_WALLET:0:10}..."
echo "Node: $RUSTCHAIN_NODE_URL"
echo "Threads: $RUSTCHAIN_MINER_THREADS"

# Validate wallet address
if [ -z "$RUSTCHAIN_WALLET" ]; then
    echo "❌ ERROR: RUSTCHAIN_WALLET not set"
    echo "Usage: docker run -e RUSTCHAIN_WALLET=your_address rustchain-miner"
    exit 1
fi

# Start miner
cd /app/node
exec python3 rustchain_v2_integrated_v2.2.1_rip200.py \
    --wallet "$RUSTCHAIN_WALLET" \
    --node "$RUSTCHAIN_NODE_URL" \
    --threads "$RUSTCHAIN_MINER_THREADS" \
    --log-level "$RUSTCHAIN_LOG_LEVEL"
