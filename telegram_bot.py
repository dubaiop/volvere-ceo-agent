"""
Telegram webhook handler — receives updates via FastAPI endpoint.
"""

import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, COMPANY_NAME
from agent import run_skill, chat, clear_memory
from skills.prompts import SKILL_MAP

logger = logging.getLogger(__name__)

HELP_TEXT = f"""*{COMPANY_NAME} CEO Assistant* 🤖

*Skills:*
/briefing — Daily briefing & priorities
/decision — Decision support & trade-offs
/meeting — Meeting prep & agenda
/investor — Investor & stakeholder comms
/deal — Deal structuring & negotiation
/solve — Problem diagnosis & solutions

Just type any message for free-form advice.

/clear — Reset conversation memory
/help — Show this menu"""


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

async def clear_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    clear_memory(str(update.effective_user.id))
    await update.message.reply_text("Memory cleared.")

async def _run_skill_cmd(update: Update, skill_id: str, hint: str):
    session_id = str(update.effective_user.id)
    text = update.message.text.partition(" ")[2].strip()
    if not text:
        await update.message.reply_text(f"Add your input after the command.\n\nExample: `/{skill_id.split('-')[0]} {hint}`", parse_mode="Markdown")
        return
    await update.message.reply_text("Analyzing...")
    try:
        result = run_skill(skill_id, text, session_id=session_id)
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def briefing_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _run_skill_cmd(update, "daily-briefing", "Paste your pipeline or describe your day")

async def decision_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _run_skill_cmd(update, "decision-support", "Should we raise now or grow to $1M ARR first?")

async def meeting_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _run_skill_cmd(update, "meeting-prep", "Meeting with Series A investor, they funded 5 SaaS cos")

async def investor_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _run_skill_cmd(update, "investor-comms", "Monthly update: MRR $15k, +20% MoM")

async def deal_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _run_skill_cmd(update, "deal-maker", "Enterprise client wants 40% discount for annual contract")

async def solve_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _run_skill_cmd(update, "problem-solver", "Churn spiked to 8% this month")

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    session_id = str(update.effective_user.id)
    text = update.message.text.strip()
    if not text:
        return
    await update.message.reply_text("Thinking...")
    try:
        result = chat(text, session_id=session_id)
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).updater(None).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("briefing", briefing_cmd))
    app.add_handler(CommandHandler("decision", decision_cmd))
    app.add_handler(CommandHandler("meeting", meeting_cmd))
    app.add_handler(CommandHandler("investor", investor_cmd))
    app.add_handler(CommandHandler("deal", deal_cmd))
    app.add_handler(CommandHandler("solve", solve_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    return app
