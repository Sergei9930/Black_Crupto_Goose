"""Заглушка для биржи MAX."""

STREAM_URL = ""  # TODO: указать реальный WebSocket URL


def parse_prices(message: str) -> dict[str, float]:
    """Разбор сообщения MAX. Пока не реализовано."""
    return {}
