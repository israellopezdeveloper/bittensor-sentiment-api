from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.bittensor_substrate_service import AsyncSubstrateService


@pytest.mark.asyncio
@patch('app.services.bittensor_substrate_service.AsyncSubstrateInterface')
async def test_get_dividends(mock_substrate_class):
    instance = AsyncMock()
    instance.get_chain_head.return_value = '0x123'
    mock_result = MagicMock()
    mock_result.value = 1.5
    instance.query.return_value = mock_result
    mock_substrate_class.return_value = instance

    service = AsyncSubstrateService()
    dividend = await service.get_dividends_for_netuid_hotkey(
        18, '5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v'
    )
    assert dividend == 1.5


@pytest.mark.asyncio
@patch('app.services.bittensor_substrate_service.AsyncSubstrateInterface')
async def test_get_dividends_with_none_result(mock_substrate_class):
    instance = AsyncMock()
    instance.get_chain_head.return_value = '0x123'
    instance.query.return_value = None
    mock_substrate_class.return_value = instance

    service = AsyncSubstrateService()
    result = await service.get_dividends_for_netuid_hotkey(
        18, '5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v'
    )
    assert result is None


@pytest.mark.asyncio
@patch('app.services.bittensor_substrate_service.AsyncSubstrateInterface')
async def test_get_dividends_with_non_numeric(mock_substrate_class):
    instance = AsyncMock()
    instance.get_chain_head.return_value = '0x123'
    instance.query.return_value = AsyncMock(value={'unexpected': 'object'})
    mock_substrate_class.return_value = instance

    service = AsyncSubstrateService()
    result = await service.get_dividends_for_netuid_hotkey(
        18, '5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v'
    )
    assert result is None


@pytest.mark.asyncio
@patch('app.services.bittensor_substrate_service.AsyncSubstrateInterface')
async def test_get_dividends_for_netuid(mock_substrate_class):
    mock_key = MagicMock()
    mock_key.value = '5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v'
    mock_value = MagicMock()
    mock_value.value = 42.0

    qmr_mock = AsyncMock()
    qmr_mock.__aiter__.return_value = [(mock_key, mock_value)]

    instance = AsyncMock()
    instance.query_map.return_value = qmr_mock
    mock_substrate_class.return_value = instance

    service = AsyncSubstrateService()
    result = await service.get_dividends_for_netuid(18)

    assert result[0]['dividend'] == 42.0


@pytest.mark.asyncio
@patch('app.services.bittensor_substrate_service.AsyncSubstrateInterface')
async def test_get_dividends_for_netuid_failure_returns_empty(mock_substrate_class):
    instance = AsyncMock()
    instance.query_map.side_effect = Exception('Mock failure')
    mock_substrate_class.return_value = instance

    service = AsyncSubstrateService()
    result = await service.get_dividends_for_netuid(18)

    assert result == []


@pytest.mark.asyncio
@patch('app.services.bittensor_substrate_service.AsyncSubstrateInterface')
async def test_get_all_dividends(mock_substrate_class):
    # Clave simulada: netuid = 18, hotkey en bytes
    mock_key = (18, ((0x00,) * 32,))
    mock_value = MagicMock()
    mock_value.value = 77.7

    qmr_mock = AsyncMock()
    qmr_mock.__aiter__.return_value = [(mock_key, mock_value)]

    instance = AsyncMock()
    instance.query_map.return_value = qmr_mock
    mock_substrate_class.return_value = instance

    service = AsyncSubstrateService()
    result = await service.get_all_dividends()

    assert len(result) == 1
    assert result[0]['netuid'] == 18
    assert 'hotkey' in result[0]['hotkeys'][0]
    assert result[0]['hotkeys'][0]['dividends'] == 77.7


@pytest.mark.asyncio
@patch('app.services.bittensor_substrate_service.AsyncSubstrateInterface')
async def test_get_all_dividends_failure_returns_empty(mock_substrate_class):
    instance = AsyncMock()
    instance.query_map.side_effect = Exception('Mock error')
    mock_substrate_class.return_value = instance

    service = AsyncSubstrateService()
    result = await service.get_all_dividends()

    assert result == []
