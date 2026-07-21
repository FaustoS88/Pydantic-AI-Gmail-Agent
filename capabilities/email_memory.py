"""
email_memory.py — Thread context instructions as a Pydantic AI v2 Capability.

"""

from pydantic_ai.capabilities import Capability

email_memory = Capability(
    id="email-memory",
    description="Use conversation history and thread context for smarter replies.",
    instructions=(
        "Before replying to any email, call get_thread_context to read "
        "the full conversation thread.\n\n"
        "When you have thread context:\n"
        "- Reference prior exchanges naturally ('Following up on our "
        "earlier discussion about...', 'As I mentioned in my last "
        "email...').\n"
        "- Do NOT repeat information the user already provided in "
        "earlier messages.\n"
        "- Do NOT ask questions that were already answered in the "
        "thread.\n"
        "- If the thread shows an ongoing project or recurring topic, "
        "acknowledge the continuity.\n"
        "- Match the tone and formality established in earlier "
        "messages in the thread.\n"
        "- If the latest message in the thread is from the user "
        "themselves (the account owner), skip that email — they "
        "already replied."
    ),
)