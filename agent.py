"""
CEO Agent — core Claude API runner with conversation memory.
"""

import anthropic
from config import CLAUDE_MODEL
from skills.prompts import SKILL_MAP

_memory: dict[str, list[dict]] = {}


def run_skill(skill_id: str, user_input: str, context: str = "", session_id: str = "default") -> str:
    skill = SKILL_MAP.get(skill_id)
    if not skill:
        available = ", ".join(SKILL_MAP.keys())
        raise ValueError(f"Unknown skill '{skill_id}'. Available: {available}")

    client = anthropic.Anthropic()

    full_input = user_input
    if context:
        full_input = f"Context:\n{context}\n\n---\n\n{user_input}"

    history = _memory.get(session_id, [])
    messages = history + [{"role": "user", "content": full_input}]

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=skill["prompt"],
        messages=messages,
    )

    reply = response.content[0].text

    _memory[session_id] = (messages + [{"role": "assistant", "content": reply}])[-20:]

    return reply


def chat(user_input: str, session_id: str = "default") -> str:
    """Free-form CEO assistant chat with memory."""
    client = anthropic.Anthropic()

    system = """You are an elite AI assistant for a CEO and entrepreneur. You have deep expertise in:
- Business strategy and GTM execution
- Fundraising and investor relations
- Team building and leadership
- Product and market fit
- Operations, finance, and scaling
- Deal-making and negotiations

You are direct, sharp, and action-oriented. You give concrete advice, not vague frameworks.
You remember the context of this conversation and build on it.
When you don't know something specific about the user's business, ask — don't assume."""

    history = _memory.get(session_id, [])
    messages = history + [{"role": "user", "content": user_input}]

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=system,
        messages=messages,
    )

    reply = response.content[0].text
    _memory[session_id] = (messages + [{"role": "assistant", "content": reply}])[-20:]
    return reply


def clear_memory(session_id: str = "default"):
    _memory.pop(session_id, None)
