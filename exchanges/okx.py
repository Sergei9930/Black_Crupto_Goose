"""Заглушка для биржи OKX."""

STREAM_URL = ""  # TODO: указать реальный WebSocket URL


def parse_prices(message: str) -> dict[str, float]:
    """Разбор сообщения OKX. Пока не реализовано."""
    return {}
