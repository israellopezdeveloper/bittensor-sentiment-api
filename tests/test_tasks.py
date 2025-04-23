from unittest.mock import AsyncMock, patch


@patch('app.services.chutes_service.ChutesService.get_sentiment_score', new_callable=AsyncMock)
@patch('app.services.datura_service.DaturaService.search_tweets', new_callable=AsyncMock)
def test_analyze_and_stake(mock_search, mock_sentiment):
    mock_search.return_value = ['Tweet']
    mock_sentiment.return_value = 80.0

    from app.tasks import analyze_and_stake

    result = analyze_and_stake.run(18, 'FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v')
    assert result == 80.0


@patch('app.services.datura_service.DaturaService.search_tweets', new_callable=AsyncMock)
@patch('app.services.chutes_service.ChutesService.get_sentiment_score', new_callable=AsyncMock)
def test_analyze_and_stake_no_tweets(mock_sentiment, mock_search):
    mock_search.return_value = []
    mock_sentiment.return_value = 0.0

    from app.tasks import analyze_and_stake

    result = analyze_and_stake.run(18, 'FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v')
    assert result == 0.0


@patch('app.services.datura_service.DaturaService.search_tweets', new_callable=AsyncMock)
@patch('app.services.chutes_service.ChutesService.get_sentiment_score', new_callable=AsyncMock)
def test_analyze_and_stake_raises_exception(mock_sentiment, mock_search):
    mock_search.side_effect = Exception('API error')
    mock_sentiment.return_value = 0.0

    from app.tasks import analyze_and_stake

    result = analyze_and_stake.run(18, 'FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v')
    assert result == 0.0
