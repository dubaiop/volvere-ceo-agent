import os
from dotenv import load_dotenv

load_dotenv()

CLAUDE_MODEL = "claude-sonnet-4-6"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY", "")
HUBSPOT_BASE_URL = "https://api.hubapi.com"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
PORT = int(os.environ.get("PORT", 8000))
CEO_NAME = os.environ.get("CEO_NAME", "CEO")
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Volvere.io")
