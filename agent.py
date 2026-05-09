"""CEO Agent — Claude first, Groq fallback if credits run out."""

from config import CLAUDE_MODEL, ANTHROPIC_API_KEY, GROQ_API_KEY, GROQ_MODEL, COMPANY_NAME, CEO_NAME
from skills.prompts import SKILL_MAP
from database import log_interaction

_memory: dict[str, list[dict]] = {}

CEO_SYSTEM = f"""You are an elite AI assistant for {CEO_NAME}, CEO of {COMPANY_NAME}. You have deep expertise in:
- Business strategy and GTM execution
- Fundraising and investor relations
- Team building and leadership
- Product and market fit
- Operations, finance, and scaling
- Deal-making and negotiations

You are direct, sharp, and action-oriented. You give concrete advice, not vague frameworks.
You remember the context of this conversation and build on it.
When you don't know something specific about the user's business, ask — don't assume."""


def _call(system: str, messages: list, max_tokens: int = 4096) -> str:
    """Try Claude first. If credits exhausted, fall back to Groq (free)."""
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            r = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.create(
                model=CLAUDE_MODEL, max_tokens=max_tokens, system=system, messages=messages
            )
            return r.content[0].text
        except Exception as e:
            err = str(e).lower()
            if "credit" in err or "balance" in err or "billing" in err:
                pass
            else:
                raise

    if GROQ_API_KEY:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
        msgs = [{"role": "system", "content": system}] + messages
        r = client.chat.completions.create(
            model=GROQ_MODEL, messages=msgs, max_tokens=min(max_tokens, 2048), temperature=0.7
        )
        return r.choices[0].message.content

    raise RuntimeError("No working API. Add Anthropic credits or set GROQ_API_KEY.")


def run_skill(skill_id: str, user_input: str, context: str = "", session_id: str = "default") -> str:
    skill = SKILL_MAP.get(skill_id)
    if not skill:
        raise ValueError(f"Unknown skill '{skill_id}'. Available: {', '.join(SKILL_MAP.keys())}")

    full_input = f"Context:\n{context}\n\n---\n\n{user_input}" if context else user_input
    history = _memory.get(session_id, [])
    messages = history + [{"role": "user", "content": full_input}]
    reply = _call(skill["prompt"], messages)
    _memory[session_id] = (messages + [{"role": "assistant", "content": reply}])[-20:]
    log_interaction(session_id, skill_id, user_input, reply)
    return reply


def chat(user_input: str, session_id: str = "default") -> str:
    history = _memory.get(session_id, [])
    messages = history + [{"role": "user", "content": user_input}]
    reply = _call(CEO_SYSTEM, messages)
    _memory[session_id] = (messages + [{"role": "assistant", "content": reply}])[-20:]
    log_interaction(session_id, "chat", user_input, reply)
    return reply


def clear_memory(session_id: str = "default"):
    _memory.pop(session_id, None)
