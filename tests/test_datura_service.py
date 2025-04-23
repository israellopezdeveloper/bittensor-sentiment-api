import httpx
import pytest
import respx
from httpx import Response

from app.core.config import settings
from app.services.datura_service import DaturaService


@pytest.mark.asyncio
@respx.mock
async def test_search_tweets():
    respx.get(DaturaService.API_URL).mock(
        return_value=Response(200, json=[{'text': 'Tweet 1'}, {'text': 'Tweet 2'}])
    )
    result = await DaturaService.search_tweets(netuid=18)
    assert result == ['Tweet 1', 'Tweet 2']


@respx.mock
@pytest.mark.asyncio
async def test_search_tweets_timeout():
    respx.get(DaturaService.API_URL).mock(side_effect=httpx.TimeoutException('Timeout'))

    with pytest.raises(httpx.TimeoutException):
        await DaturaService.search_tweets(18)


@respx.mock
@pytest.mark.asyncio
async def test_search_tweets_retry_on_error():
    call_count = 0

    def failing_response(_):
        nonlocal call_count
        call_count += 1
        return httpx.Response(500)

    respx.get(url__regex=r'^https://apis\.datura\.ai/twitter.*').mock(side_effect=failing_response)
    with pytest.raises(httpx.HTTPStatusError):
        await DaturaService.search_tweets(18)

    assert call_count == settings.blockchain_max_retries


@respx.mock
@pytest.mark.asyncio
async def test_search_tweets_retry_then_success():
    call_count = 0

    def flaky_response(_):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            print('[CALL 1] Simulando fallo con 500')
            return httpx.Response(500)
        print('[CALL 2] Simulando éxito con tweets')
        return httpx.Response(200, json=[{'text': 'Retry succeeded!'}])

    respx.get(url__regex=r'^https://apis\.datura\.ai/twitter.*').mock(side_effect=flaky_response)

    result = await DaturaService.search_tweets(18)

    assert result == ['Retry succeeded!']
    assert call_count == 2
