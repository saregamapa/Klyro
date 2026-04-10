from __future__ import annotations

import re

# User asks about pricing, contacting sales, demos, or talking to a human
_LEAD_PATTERN = re.compile(
    r"\b("
    r"price|pricing|prices|cost|costs|how much|quote|quotes|plan|plans|subscription|"
    r"billing|invoice|discount|trial length|enterprise tier|"
    r"contact|email me|reach out|get in touch|talk to|speak to|call me|phone|"
    r"sales|demo|book a|schedule|meeting|human|agent|representative|someone from"
    r")\b",
    re.IGNORECASE,
)


def should_prompt_lead_capture(message: str) -> bool:
    text = (message or "").strip()
    if len(text) < 3:
        return False
    return bool(_LEAD_PATTERN.search(text))
