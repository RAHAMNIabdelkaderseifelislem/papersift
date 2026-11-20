import pytest
import requests

from papersift.providers import ProviderError, RateLimitError
from papersift.providers._http import post_with_retry
from tests.conftest import FakeResponse, FakeSession


def run(responses, **kwargs):
    sleeps = []
    session = FakeSession(responses)
    result = post_with_retry(
        session, "http://x", headers={}, json={}, timeout=1, sleep=sleeps.append, **kwargs
    )
    return result, sleeps, session


def test_success_first_try_does_not_sleep():
    result, sleeps, session = run([FakeResponse(200, {"ok": 1})])
    assert result.status_code == 200 and sleeps == [] and len(session.calls) == 1


def test_retries_on_429_with_exponential_backoff():
    _, sleeps, session = run([FakeResponse(429), FakeResponse(429), FakeResponse(200, {})])
    assert sleeps == [2.0, 4.0] and len(session.calls) == 3


def test_retry_after_header_is_respected():
    _, sleeps, _ = run([FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(200, {})])
    assert sleeps == [7.0]


def test_retries_on_server_error_and_network_error():
    _, sleeps, _ = run([FakeResponse(503), requests.ConnectionError("x"), FakeResponse(200, {})])
    assert len(sleeps) == 2


def test_client_errors_fail_immediately():
    with pytest.raises(ProviderError, match="401"):
        run([FakeResponse(401, text="bad key")])


def test_gives_up_with_rate_limit_error():
    with pytest.raises(RateLimitError):
        run([FakeResponse(429)], max_retries=2)


def test_gives_up_with_provider_error_for_server_errors():
    with pytest.raises(ProviderError) as info:
        run([FakeResponse(500)], max_retries=1)
    assert not isinstance(info.value, RateLimitError)
