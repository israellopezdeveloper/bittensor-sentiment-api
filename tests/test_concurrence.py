import asyncio
from unittest.mock import AsyncMock, patch

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
async def test_concurrent_requests(mock_dividends, _, mock_get):
    mock_get.return_value = None
    mock_dividends.return_value = 42.0

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url='http://test') as client:
        headers = {'Authorization': settings.auth_token}

        tasks = [
            client.get(
                '/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v',
                headers=headers,
            )
            for _ in range(1000)
        ]
        responses = await asyncio.gather(*tasks)
        for response in responses:
            assert response.status_code == 200
            assert 'dividend' in response.json()
