import html
from typing import Any, Mapping, Optional

def h(text: str) -> str:
    """HTML-escape arbitrary text for Telegram."""
    return html.escape(text or "")

def b(text: str) -> str:
    return f"<b>{h(text)}</b>"

def i(text: str) -> str:
    return f"<i>{h(text)}</i>"

def code(text: str) -> str:
    return f"<code>{h(text)}</code>"

def render(template: str, vars: Optional[Mapping[str, Any]] = None) -> str:
    """Lightweight {var} templating with HTML escaping for values."""
    vars = vars or {}
    safe = {k: h(str(v)) for k, v in vars.items()}
    return template.format(**safe)
