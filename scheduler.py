"""
Scheduled workflows — daily briefing at 7am, sent to Telegram.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import TELEGRAM_BOT_TOKEN, COMPANY_NAME
from agent import run_skill

logger = logging.getLogger(__name__)

BRIEFING_HOUR = 7   # 7am
BRIEFING_TZ   = "Asia/Dubai"


def _build_briefing_input() -> str:
    lines = [f"Date: {datetime.now().strftime('%A, %B %d %Y')}"]

    try:
        from hubspot import get_pipeline_summary, get_recent_contacts, get_recent_deals
        pipeline = get_pipeline_summary()
        contacts = get_recent_contacts(limit=5)
        deals    = get_recent_deals(limit=5)

        lines.append(f"\nPipeline: {pipeline['total_deals']} open deals, total value ${pipeline['total_value']:,.0f}")

        if pipeline["stages"]:
            lines.append("Stages:")
            for stage, data in pipeline["stages"].items():
                lines.append(f"  - {stage}: {data['count']} deals (${data['value']:,.0f})")

        if deals:
            lines.append("\nTop deals:")
            for d in deals:
                p = d.get("properties", {})
                lines.append(f"  - {p.get('dealname','—')} | ${p.get('amount','0')} | {p.get('dealstage','—')}")

        if contacts:
            lines.append("\nRecent contacts:")
            for c in contacts:
                p = c.get("properties", {})
                name = f"{p.get('firstname','') or ''} {p.get('lastname','') or ''}".strip() or "—"
                lines.append(f"  - {name} | {p.get('email','—')} | {p.get('lifecyclestage','—')}")
    except Exception as e:
        lines.append(f"\nHubSpot: unavailable ({e})")

    return "\n".join(lines)


def _send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping send.")
        return

    import requests
    from config import TELEGRAM_CHAT_ID
    if not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not set — skipping send.")
        return

    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "Markdown"},
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Telegram send error: {e}")


def run_daily_briefing():
    logger.info("Running scheduled daily briefing...")
    try:
        briefing_input = _build_briefing_input()
        context = f"Company: {COMPANY_NAME}. This is the automated morning briefing."
        result = run_skill("daily-briefing", briefing_input, context, session_id="scheduler")

        header = f"🌅 *Good morning — Daily Briefing*\n_{datetime.now().strftime('%A, %B %d')}_\n\n"
        _send_telegram(header + result)
        logger.info("Daily briefing sent.")
    except Exception as e:
        logger.error(f"Daily briefing failed: {e}")
        _send_telegram(f"⚠️ Daily briefing failed: {e}")


def start_scheduler() -> BackgroundScheduler:
    tz = pytz.timezone(BRIEFING_TZ)
    scheduler = BackgroundScheduler(timezone=tz)

    scheduler.add_job(
        run_daily_briefing,
        trigger=CronTrigger(hour=BRIEFING_HOUR, minute=0, timezone=tz),
        id="daily_briefing",
        name="Daily CEO Briefing",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started — daily briefing at {BRIEFING_HOUR}:00 {BRIEFING_TZ}")
    return scheduler
