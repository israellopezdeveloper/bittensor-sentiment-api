import pytest
import respx
from httpx import Response

from app.services.chutes_service import ChutesService


@pytest.mark.parametrize(
    'text,expected',
    [
        ('Sentiment: 42.5', 42.5),
        ('Score is -101', -100.0),
        ('Response: 200', 100.0),
        ('Nonsense text', 0.0),
    ],
)
def test_extract_sentiment_score(text, expected):
    assert ChutesService.extract_sentiment_score(text) == expected


@pytest.mark.parametrize(
    'text,expected',
    [
        ('Score: -150.8', -100.0),
        ('Sentiment = 123.45', 100.0),
        ('Overall score: 87.3', 87.3),
        ('Score: 45,6', 45.6),
        ('Nonsense text without number', 0.0),
        ('It is 42', 42.0),
        ('-12', -12.0),
        ('', 0.0),
        ('Sentiment: -20.5 and confidence: 99.9', -20.5),
        ('Nonsense text', 0.0),
        ('Sentiment: foo', 0.0),
        ('Sentiment: 150.0', 100.0),
        ('Sentiment: -150.0', -100.0),
        ('Sentiment: -0.5', -0.5),
        ('value: 0.00000001', 0.00000001),
        ('0', 0.0),
        ('0.0', 0.0),
        ('Sentiment: -100.001', -100.0),
        ('Sentiment: 100.001', 100.0),
        ('+42.0', 42.0),
    ],
)
def test_extract_sentiment_score_edge_cases(text, expected):
    assert ChutesService.extract_sentiment_score(text) == expected


@respx.mock
@pytest.mark.asyncio
async def test_get_sentiment_score_retry_then_success():
    call_count = 0

    def flaky_response(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(200, json={'invalid': 'structure'})
        return Response(200, json={'choices': [{'message': {'content': 'Sentiment: 88'}}]})

    respx.post(ChutesService.BASE_URL).mock(side_effect=flaky_response)

    tweets = ['Bittensor is amazing!']
    result = await ChutesService.get_sentiment_score(tweets)

    assert result == 88.0
    assert call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_sentiment_score_missing_choices():
    respx.post(ChutesService.BASE_URL).mock(return_value=Response(200, json={'not_choices': []}))

    tweets = ['Some tweet']
    result = await ChutesService.get_sentiment_score(tweets)

    assert result == 0.0
