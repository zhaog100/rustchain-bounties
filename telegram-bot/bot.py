#!/usr/bin/env python3
"""
RustChain Telegram Bot — @RustChainBot

Commands:
  /balance <wallet> — Check RTC balance
  /miners           — List active miners
  /epoch            — Current epoch info
  /price            — Show RTC reference rate ($0.10)
  /help             — Show commands

Environment:
  TELEGRAM_BOT_TOKEN — Bot token from @BotFather
  RUSTCHAIN_NODE     — RustChain node URL (default: https://50.28.86.131:8099)
"""

import logging
import os
import re
import time
from datetime import datetime
from typing import Optional

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)
logger = logging.getLogger(__name__)

NODE_URL = os.getenv("RUSTCHAIN_NODE", "https://50.28.86.131:8099")
RATE_LIMIT_SECONDS = 5

# Rate limiting: {user_id: last_request_time}
user_last_request: dict[int, float] = {}

# ---------------------------------------------------------------------------
# RustChain API Helpers
# ---------------------------------------------------------------------------


def call_node_api(endpoint: str, params: Optional[dict] = None) -> dict:
    """Call RustChain node API."""
    url = f"{NODE_URL}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to node at {url}")
        return {"error": "Node offline"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"Node returned {e.response.status_code}")
        return {"error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.Timeout:
        logger.error("Node request timed out")
        return {"error": "Timeout"}


def get_balance(wallet: str) -> dict:
    """Get wallet balance."""
    return call_node_api("wallet/balance", {"miner": wallet})


def get_miners() -> dict:
    """Get list of active miners."""
    return call_node_api("miners/list")


def get_epoch_info() -> dict:
    """Get current epoch info."""
    return call_node_api("epoch/current")


def get_price() -> dict:
    """Get RTC reference rate."""
    # Hardcoded reference rate as per bounty spec
    return {"ok": True, "price_usd": 0.10, "timestamp": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------


def check_rate_limit(user_id: int) -> bool:
    """Check if user is rate limited. Returns True if allowed."""
    now = time.time()
    last = user_last_request.get(user_id, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return False
    user_last_request[user_id] = now
    return True


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "🌾 **Welcome to RustChain Bot!**\n\n"
        "I can help you check wallet balances, miner status, and more.\n\n"
        "Use /help to see available commands."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
🌾 **RustChain Bot Commands**

/balance <wallet> — Check RTC balance
/miners — List active miners
/epoch — Current epoch info
/price — Show RTC reference rate ($0.10)
/help — Show this help message

**Examples:**
`/balance my-wallet`
`/miners`
`/epoch`

Rate limit: 1 request per 5 seconds per user.
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command."""
    if not check_rate_limit(update.effective_user.id):
        await update.message.reply_text(
            "⏳ Please wait 5 seconds between requests.",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/balance <wallet>`\n\nExample: `/balance my-wallet`",
            parse_mode="Markdown"
        )
        return

    wallet = context.args[0]
    
    # Validate wallet name (alphanumeric, dash, underscore)
    if not re.match(r'^[a-zA-Z0-9_-]+$', wallet):
        await update.message.reply_text(
            f"❌ Invalid wallet name: `{wallet}`\n\n"
            "Wallet names can only contain letters, numbers, dashes, and underscores.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(f"⏳ Checking balance for `{wallet}`...", parse_mode="Markdown")
    
    result = get_balance(wallet)
    
    if result.get("ok"):
        balance = result.get("balance", 0)
        await update.message.reply_text(
            f"💰 **Balance for `{wallet}`**\n\n"
            f"**{balance:.4f} RTC**\n\n"
            f"≈ ${balance * 0.10:.2f} USD (at $0.10/RTC)",
            parse_mode="Markdown"
        )
    else:
        error = result.get("error", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error}", parse_mode="Markdown")


async def cmd_miners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /miners command."""
    if not check_rate_limit(update.effective_user.id):
        await update.message.reply_text(
            "⏳ Please wait 5 seconds between requests.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("⏳ Fetching miner list...", parse_mode="Markdown")
    
    result = get_miners()
    
    if result.get("ok"):
        miners = result.get("miners", [])
        if not miners:
            await update.message.reply_text("📭 No active miners found.")
            return
        
        text = "⛏️ **Active Miners**\n\n"
        for i, miner in enumerate(miners[:10], 1):  # Limit to 10
            name = miner.get("name", "Unknown")
            status = miner.get("status", "unknown")
            text += f"{i}. `{name}` — {status}\n"
        
        if len(miners) > 10:
            text += f"\n... and {len(miners) - 10} more"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        error = result.get("error", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error}", parse_mode="Markdown")


async def cmd_epoch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /epoch command."""
    if not check_rate_limit(update.effective_user.id):
        await update.message.reply_text(
            "⏳ Please wait 5 seconds between requests.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("⏳ Fetching epoch info...", parse_mode="Markdown")
    
    result = get_epoch_info()
    
    if result.get("ok"):
        epoch = result.get("epoch", 0)
        start_time = result.get("start_time", "Unknown")
        end_time = result.get("end_time", "Unknown")
        
        await update.message.reply_text(
            f"📊 **Epoch Info**\n\n"
            f"**Epoch**: {epoch}\n"
            f"**Started**: {start_time}\n"
            f"**Ends**: {end_time}",
            parse_mode="Markdown"
        )
    else:
        error = result.get("error", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error}", parse_mode="Markdown")


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /price command."""
    if not check_rate_limit(update.effective_user.id):
        await update.message.reply_text(
            "⏳ Please wait 5 seconds between requests.",
            parse_mode="Markdown"
        )
        return

    result = get_price()
    
    if result.get("ok"):
        price = result.get("price_usd", 0.10)
        timestamp = result.get("timestamp", "Unknown")
        
        await update.message.reply_text(
            f"💹 **RTC Reference Rate**\n\n"
            f"**1 RTC = ${price:.2f} USD**\n\n"
            f"Updated: {timestamp}",
            parse_mode="Markdown"
        )
    else:
        error = result.get("error", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error}", parse_mode="Markdown")


async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text(
        "❓ Unknown command. Use /help to see available commands."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the bot."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        print("::error::TELEGRAM_BOT_TOKEN environment variable not set!")
        return

    # Build application
    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("balance", cmd_balance))
    application.add_handler(CommandHandler("miners", cmd_miners))
    application.add_handler(CommandHandler("epoch", cmd_epoch))
    application.add_handler(CommandHandler("price", cmd_price))

    # Handle unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    # Start the bot
    logger.info(f"🌾 RustChain Bot starting... (Node: {NODE_URL})")
    print(f"🌾 RustChain Bot starting... (Node: {NODE_URL})")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
