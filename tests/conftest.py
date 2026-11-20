"""Shared test helpers."""

from __future__ import annotations


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json = json_data
        self.text = text or (str(json_data) if json_data is not None else "")
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class FakeSession:
    """Stands in for requests.Session: returns queued responses, records calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def _next(self, url, kwargs):
        self.calls.append({"url": url, **kwargs})
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(item, Exception):
            raise item
        return item

    def post(self, url, **kwargs):
        return self._next(url, kwargs)

    def get(self, url, **kwargs):
        return self._next(url, kwargs)
