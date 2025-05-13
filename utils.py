import html

def escape_html(text: str) -> str:
    """Безопасный HTML-escape для текста"""
    return html.escape(text)

def get_author(user) -> str:
    """Формирует имя автора задачи из объекта user"""
    if not user:
        return "<unknown>"
    return f"@{user.username}" if user.username else user.first_name or str(user.id)
