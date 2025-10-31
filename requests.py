"""Simple requests stub for offline testing."""

class _Response:
    def __init__(self, content: str = "42") -> None:
        self._content = content

    def json(self) -> dict:
        return {"message": {"content": self._content}}


def post(*args, **kwargs):  # pragma: no cover - integration stub
    return _Response()

