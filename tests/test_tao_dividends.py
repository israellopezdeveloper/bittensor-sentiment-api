from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
@patch('app.cache.singleton.redis_cache.get', new_callable=AsyncMock)
@patch('app.cache.singleton.redis_cache.set', new_callable=AsyncMock)
@patch(
    'app.services.singleton.substrate_service.get_dividends_for_netuid_hotkey',
    new_callable=AsyncMock,
)
async def test_get_tao_dividends(mock_dividends, _, mock_get):
    mock_get.return_value = None
    mock_dividends.return_value = 42.0

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get(
            '/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v',
            headers={'Authorization': settings.auth_token},
        )

    assert response.status_code == 200
    data = response.json()
    assert data['dividend'] == 42.0


@pytest.mark.asyncio
@patch('app.cache.singleton.redis_cache.get', new_callable=AsyncMock)
@patch('app.cache.singleton.redis_cache.set', new_callable=AsyncMock)
@patch('app.services.singleton.substrate_service.submit_stake_adjustment', new_callable=AsyncMock)
@patch(
    'app.services.singleton.substrate_service.get_dividends_for_netuid_hotkey',
    new_callable=AsyncMock,
)
@patch('app.api.v1.tao_dividends.analyze_and_stake.delay')
async def test_get_tao_dividends_trade_true(
    mock_delay,
    mock_get_dividends_for_netuid_hotkey,
    mock_submit,
    mock_cache_set,
    mock_cache_get,
):
    mock_cache_get.return_value = None
    mock_get_dividends_for_netuid_hotkey.return_value = 80.0

    # Simula que no devuelve nada (como es en la función real si todo va bien)
    mock_submit.return_value = None

    mock_task = MagicMock()
    mock_task.get.return_value = 42.0
    mock_delay.return_value = mock_task

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get(
            '/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v&trade=true',
            headers={'Authorization': settings.auth_token},
        )

    assert response.status_code == 200
    data = response.json()
    assert data['dividend'] == 80.0
    assert data['stake_tx_triggered'] is True


@pytest.mark.asyncio
@patch('app.cache.singleton.redis_cache.get', new_callable=AsyncMock)
@patch(
    'app.services.singleton.substrate_service.get_dividends_for_netuid_hotkey',
    new_callable=AsyncMock,
)
async def test_get_tao_dividends_error_when_dividends_none(mock_get_dividends, mock_cache_get):
    mock_cache_get.return_value = None
    mock_get_dividends.return_value = None  # Simula fallo en consulta a la chain

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get(
            '/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v',
            headers={'Authorization': settings.auth_token},
        )

    assert response.status_code == 500
    assert response.json() == {'detail': 'Unable to fetch dividend'}


@pytest.mark.asyncio
async def test_get_tao_dividends_error_without_token():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get(
            '/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v'
        )

    assert response.status_code == 422
    assert response.json() == {
        'detail': [
            {
                'input': None,
                'loc': ['header', 'authorization'],
                'msg': 'Field required',
                'type': 'missing',
            }
        ]
    }


@pytest.mark.asyncio
async def test_get_tao_dividends_error_with_not_valid_token():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get(
            '/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v',
            headers={'Authorization': 'Invalid token'},
        )

    assert response.status_code == 401
    assert response.json() == {'detail': 'Invalid token'}


@pytest.mark.asyncio
@patch('app.cache.singleton.redis_cache.get', new_callable=AsyncMock)
@patch(
    'app.services.singleton.substrate_service.get_dividends_for_netuid_hotkey',
    new_callable=AsyncMock,
)
async def test_get_tao_dividends_cached(mock_get_dividends, mock_cache_get):
    mock_cache_get.return_value = {'results': 77.7}

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get(
            '/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v',
            headers={'Authorization': settings.auth_token},
        )

    assert response.status_code == 200
    data = response.json()
    assert data['cached'] is True
    assert data['dividend'] == 77.7
