"""Экранирование пользовательского текста для Markdown MAX."""

_MD_ESCAPE_CHARS = r"\*_[]()~`>#+-=|{}.!"


def escape_markdown(text: str) -> str:
    if not text:
        return ""
    result = str(text)
    for char in _MD_ESCAPE_CHARS:
        result = result.replace(char, f"\\{char}")
    return result
