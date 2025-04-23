from typing import Optional

from bittensor.utils import is_valid_ss58_address
from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import TimeoutException

from app.cache.singleton import redis_cache
from app.core.auth import verify_token
from app.services.singleton import substrate_service
from app.tasks import analyze_and_stake

router = APIRouter()


def validate_hotkey(hotkey: str) -> str:
    """
    Validates a hotkey address.
    """
    if not is_valid_ss58_address(hotkey):
        raise HTTPException(status_code=422, detail='Invalid hotkey address')
    return hotkey


@router.get(
    '/tao_dividends',
    tags=['TAO Dividends'],
    summary='Obtain TAO dividends for a given subnet and hotkey',
    description="""
        Returns the TAO dividend for a given subnet and hotkey. Optionally triggers a
        sentiment-based stake/unstake operation if `trade=true`.
        """,
)
async def get_tao_dividends(
    netuid: Optional[int] = Query(None, description='The subnet ID', example=18),
    hotkey: Optional[str] = Query(
        None,
        description='The wallet hotkey address',
        example='5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v',
        min_length=48,
        max_length=48,
    ),
    trade: bool = False,
    _: str = Depends(verify_token),
):
    async def _get_cache_all() -> list | None:
        key = 'dividends:all'
        cached = await redis_cache.get(key)
        if cached:
            return cached['results']
        return None

    async def _get_cache_netuid(netuid: int) -> list | None:
        key = f'dividends:{netuid}:netuid'
        cached = await redis_cache.get(key)
        if cached is not None:
            return cached['results']
        return None

    async def _get_cache_netuid_hotkey(netuid: int, hotkey: str) -> float | None:
        key = f'dividends:{netuid}:netuid:{hotkey}:hotkey'
        cached = await redis_cache.get(key)
        if cached:
            return cached['results']
        return None

    async def _set_cache_all(results: list) -> None:
        key = 'dividends:all'
        await redis_cache.set(key, {'results': results})

    async def _set_cache_netuid(netuid: int, results: list) -> None:
        key = f'dividends:{netuid}:netuid'
        await redis_cache.set(key, {'results': results})

    async def _set_cache_netuid_hotkey(netuid: int, hotkey: str, results: float) -> None:
        key = f'dividends:{netuid}:netuid:{hotkey}:hotkey'
        await redis_cache.set(key, {'results': results})

    # Responses

    async def _response_all() -> dict:
        cached = await _get_cache_all()
        if cached:
            return {'results': cached, 'cached': True}
        results = await substrate_service.get_all_dividends()
        await _set_cache_all(results)
        return {'results': results, 'cached': False}

    async def _response_netuid(netuid: int) -> dict:
        def process_all_data(cached: list) -> list:
            for entry in cached:
                if entry['netuid'] == netuid:
                    return entry['hotkeys']
            return []

        cached = await _get_cache_netuid(netuid)
        if cached:
            return {
                'netuid': netuid,
                'hotkeys': cached,
                'cached': True,
            }
        cached = await _get_cache_all()
        if cached:
            return {
                'netuid': netuid,
                'hotkeys': process_all_data(cached),
                'cached': True,
            }
        results = await substrate_service.get_dividends_for_netuid(netuid)
        if results is None:
            raise HTTPException(status_code=500, detail='Unable to fetch dividend')
        await _set_cache_netuid(netuid, results)
        return {
            'netuid': netuid,
            'hotkeys': results,
            'cached': False,
        }

    async def _response_hotkey(hotkey: str) -> dict:
        def process_all_data(cached: list) -> list:
            results = []
            netuid: int = 0
            hotkeys: list = []
            for netuid_entry in cached:
                netuid = netuid_entry['netuid']
                hotkeys = netuid_entry['hotkeys']
                for hotkey_entry in hotkeys:
                    if hotkey_entry['hotkey'] == hotkey:
                        results.append({
                            'netuid': netuid,
                            'dividend': hotkey_entry['dividends'],
                        })
            return results

        cached = await _get_cache_all()
        if cached is not None:
            return {
                'hotkey': hotkey,
                'netuids': process_all_data(cached),
                'cached': True,
            }
        results = await substrate_service.get_all_dividends()
        await _set_cache_all(results)
        return {
            'hotkey': hotkey,
            'netuids': process_all_data(results),
            'cached': False,
        }

    async def _response_netuid_hotkey(netuid: int, hotkey: str) -> dict:
        def process_all_data(cached: list) -> float:
            for netuid_entry in cached:
                if hasattr(netuid_entry, 'netuid') and netuid_entry['netuid'] == netuid:
                    for hotkey_entry in netuid_entry['hotkeys']:
                        if hasattr(hotkey_entry, 'hotkey') and hotkey_entry['hotkey'] == hotkey:
                            return hotkey_entry['dividends']
            raise HTTPException(status_code=500, detail='Unable to fetch dividend')

        cached = await _get_cache_netuid_hotkey(netuid, hotkey)
        if cached is not None:
            return {
                'netuid': netuid,
                'hotkey': hotkey,
                'dividend': cached,
                'cached': True,
            }
        cached = await _get_cache_all()
        if cached:
            return {
                'netuid': netuid,
                'hotkey': hotkey,
                'dividend': process_all_data(cached),
                'cached': True,
            }
        results = await substrate_service.get_dividends_for_netuid_hotkey(netuid, hotkey)
        if results is None:
            raise HTTPException(status_code=500, detail='Unable to fetch dividend')
        await _set_cache_netuid_hotkey(netuid, hotkey, results)
        return {
            'netuid': netuid,
            'hotkey': hotkey,
            'dividend': results,
            'cached': False,
        }

    """
    Returns the TAO dividend for a given subnet and hotkey. Optionally triggers a
    sentiment-based stake/unstake operation if `trade=true`.

    Args:
        netuid (int): The subnet ID. Default is 18.
        hotkey (str): The wallet hotkey address.
        trade (bool): Whether to trigger a stake/unstake operation based on sentiment.

    Returns:
        dict: Dividend data, cache status, and trade trigger status.
    """

    if netuid is not None and hotkey is not None:
        stake_tx_triggered = False
        if trade:
            try:
                analyze_and_stake.delay(netuid, hotkey)
                stake_tx_triggered = True
            except TimeoutException as e:
                raise HTTPException(status_code=500, detail='Sentiment analysis timed out') from e

        response = await _response_netuid_hotkey(netuid, hotkey)
        return {**response, 'stake_tx_triggered': stake_tx_triggered}

    if netuid is not None:
        return await _response_netuid(netuid)

    if hotkey is not None:
        return await _response_hotkey(hotkey)

    return await _response_all()
