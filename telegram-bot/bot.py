#!/usr/bin/env python3
"""RustChain Telegram Bot - Check wallet, miner, bounties. Bounty #2869 (10 RTC)"""
import os, json, logging, urllib.request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

API = os.getenv("RUSTCHAIN_API", "https://api.rustchain.io/v1")
logging.basicConfig(level=logging.INFO)

async def api(endpoint):
    req = urllib.request.Request(f"{API}{endpoint}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("⛏️ Miner", callback_data="miner")],
           [InlineKeyboardButton("📋 Bounties", callback_data="bounties"),
            InlineKeyboardButton("❤️ Health", callback_data="health")]]
    await update.message.reply_text("🦀 RustChain Bot\n\n/balance <addr> /miner <addr> /bounties /health",
        reply_markup=InlineKeyboardMarkup(kb))

async def balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: return await update.message.reply_text("Usage: /balance <address>")
    try:
        d = await api(f"/balance/{ctx.args[0]}")
        await update.message.reply_text(f"💰 {d.get('amount_rtc', 0)} RTC")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def miner_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: return await update.message.reply_text("Usage: /miner <address>")
    try:
        d = await api(f"/miner/{ctx.args[0]}/status")
        s = "🟢 Attesting" if d.get("attesting") else "🔴 Offline"
        await update.message.reply_text(f"⛏️ {s}")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def bounties(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        d = await api("/bounties?limit=5")
        text = "📋 Open Bounties:\n"
        for b in d.get("bounties", []):
            text += f"• {b.get('title','N/A')} — {b.get('reward','?')} RTC\n"
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def health(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        d = await api("/health")
        s = "🟢 Online" if d.get("ok") else "🔴 Offline"
        await update.message.reply_text(f"❤️ {s} (v{d.get('version','?')})")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(f"Use /{q.data} <address> to check")

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token: print("Set TELEGRAM_BOT_TOKEN"); exit(1)
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("miner", miner_status))
    app.add_handler(CommandHandler("bounties", bounties))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CallbackQueryHandler(button))
    print("🦀 RustChain Telegram Bot running...")
    app.run_polling()
